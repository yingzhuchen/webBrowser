"""Local multi-turn webBrowser UI: uv run python web/server.py."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Coroutine
from concurrent.futures import Future, ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).parent
CONVERSATIONS: dict[str, dict] = {}
AGENTS: dict[str, Any] = {}  # Accessed exclusively on the worker's event loop.
LOCK = threading.Lock()


class Worker:
	"""Turns and cleanup share one thread and one persistent asyncio loop."""

	def __init__(self) -> None:
		self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='webBrowser')
		self.runner: asyncio.Runner | None = None

	def _run(self, coroutine: Coroutine[Any, Any, None]) -> None:
		if self.runner is None:
			self.runner = asyncio.Runner()
		self.runner.run(coroutine)

	def submit(self, coroutine: Coroutine[Any, Any, None]) -> Future:
		return self.executor.submit(self._run, coroutine)

	def shutdown(self) -> None:
		try:
			self.submit(close_all()).result()
		finally:
			try:
				if self.runner is not None:
					self.executor.submit(self.runner.close).result()
			finally:
				self.executor.shutdown(wait=True)


async def execute(conversation_id: str, turn: dict, steps: int) -> None:
	try:
		from browser_use import Agent, Browser

		conversation = CONVERSATIONS[conversation_id]
		agent = AGENTS.get(conversation_id)
		if agent is None:
			browser = Browser(conversation['browser'], keep_alive=True)
			try:
				agent = Agent(turn['task'], llm=conversation['model'] or None, browser=browser)
			except Exception:
				await browser.stop()
				raise
			AGENTS[conversation_id] = agent
		else:
			agent.add_new_task(turn['task'])
		result = await agent.run(max_steps=steps, timeout=300)
		with LOCK:
			turn.update(
				status=result.status, text=result.text or str(result.partial or ''), error=result.error,
				steps=result.steps, duration=round(result.duration_s, 1), cost=result.cost_usd,
			)
	except Exception as exc:
		with LOCK:
			turn.update(status='error', error=str(exc))
	finally:
		with LOCK:
			CONVERSATIONS[conversation_id]['status'] = 'open'


async def close_conversation(conversation_id: str) -> None:
	agent = AGENTS.get(conversation_id)
	try:
		if agent is not None:
			try:
				await agent.close()  # keep_alive=True only closes the REPL.
			finally:
				await agent.browser.stop()
		AGENTS.pop(conversation_id, None)
		with LOCK:
			CONVERSATIONS[conversation_id].update(status='closed', close_error=None)
	except Exception as exc:
		with LOCK:
			CONVERSATIONS[conversation_id].update(status='open', close_error=str(exc))


async def close_all() -> None:
	for conversation_id in list(AGENTS):
		await close_conversation(conversation_id)


class Handler(BaseHTTPRequestHandler):
	def respond(self, status: int, data: bytes, content_type: str = 'application/json') -> None:
		self.send_response(status)
		self.send_header('Content-Type', content_type + '; charset=utf-8')
		self.send_header('Cache-Control', 'no-store')
		self.send_header('X-Content-Type-Options', 'nosniff')
		self.end_headers()
		self.wfile.write(data)

	def error(self, status: int, message: str) -> None:
		self.respond(status, json.dumps({'error': message}, ensure_ascii=False).encode())

	def do_GET(self) -> None:
		if self.path in ('/', '/app.js', '/style.css'):
			name = 'index.html' if self.path == '/' else self.path[1:]
			mime = {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}[name]
			self.respond(200, (ROOT / name).read_bytes(), mime)
		elif self.path == '/api/conversations':
			with LOCK:
				data = json.dumps(list(CONVERSATIONS.values()), ensure_ascii=False).encode()
			self.respond(200, data)
		else:
			self.error(404, 'Not found')

	def do_POST(self) -> None:
		if self.path not in ('/api/messages', '/api/close'):
			self.error(404, 'Not found')
			return
		if (
			self.headers.get('Host') not in ('127.0.0.1:7860', 'localhost:7860')
			or self.headers.get('Origin') != f'http://{self.headers.get("Host")}'
			or self.headers.get('Content-Type') != 'application/json'
		):
			self.error(403, 'Same-origin JSON request required')
			return
		try:
			length = int(self.headers.get('Content-Length', '0'))
			if not 0 < length <= 65536:
				raise ValueError('Request too large or empty')
			options = json.loads(self.rfile.read(length))
			if not isinstance(options, dict):
				raise ValueError('Invalid request')
			conversation_id = options.get('conversation_id')
			if conversation_id is not None and not isinstance(conversation_id, str):
				raise ValueError('Invalid conversation ID')
			if self.path == '/api/messages':
				if not isinstance(options.get('task'), str) or not options['task'].strip() or len(options['task']) > 12000:
					raise ValueError('请输入消息（最多 12000 字）')
				if type(options.get('steps')) is not int or not 1 <= options['steps'] <= 100:
					raise ValueError('步数必须在 1 到 100 之间')
				if conversation_id is None:
					if not isinstance(options.get('model'), str) or len(options['model']) > 200:
						raise ValueError('Invalid model')
					if options.get('browser') not in ('chromium', 'cloud'):
						raise ValueError('Invalid browser')
		except (ValueError, TypeError) as exc:
			self.error(400, str(exc))
			return
		with LOCK:
			if any(item['status'] in ('running', 'closing') for item in CONVERSATIONS.values()):
				self.error(409, '请等待当前消息执行或对话关闭完成')
				return
			if self.path == '/api/close':
				if conversation_id not in CONVERSATIONS:
					self.error(404, '对话不存在，请新建对话')
					return
				CONVERSATIONS[conversation_id]['status'] = 'closing'
				WORKER.submit(close_conversation(conversation_id))
			else:
				if conversation_id is None:
					if sum(item['status'] != 'closed' for item in CONVERSATIONS.values()) >= 10:
						self.error(409, '最多保留 10 个活跃对话，请先结束不再使用的对话')
						return
					conversation_id = uuid4().hex
					CONVERSATIONS[conversation_id] = {
						'id': conversation_id, 'title': options['task'].strip(), 'model': options['model'].strip(),
						'browser': options['browser'], 'status': 'open', 'turns': [],
					}
					if len(CONVERSATIONS) > 50:
						oldest = next(key for key, value in CONVERSATIONS.items() if value['status'] == 'closed')
						del CONVERSATIONS[oldest]
				conversation = CONVERSATIONS.get(conversation_id)
				if conversation is None:
					self.error(404, '对话不存在，请新建对话')
					return
				if conversation['status'] == 'closed':
					self.error(409, '此对话已结束，请新建对话')
					return
				if len(conversation['turns']) >= 100:
					self.error(409, '此对话已达 100 轮，请新建对话')
					return
				turn = {'task': options['task'].strip(), 'status': 'running', 'text': '', 'error': None}
				conversation['turns'].append(turn)
				conversation['status'] = 'running'
				WORKER.submit(execute(conversation_id, turn, options['steps']))
		self.respond(202, json.dumps({'conversation_id': conversation_id}).encode())


WORKER = Worker()


if __name__ == '__main__':
	print('webBrowser → http://127.0.0.1:7860', flush=True)
	server = ThreadingHTTPServer(('127.0.0.1', 7860), Handler)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		pass
	finally:
		server.server_close()
		WORKER.shutdown()

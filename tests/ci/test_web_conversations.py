"""The web UI must continue the same Agent and event loop across turns, without provider calls."""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class WebConversationTest(unittest.TestCase):
	def test_follow_up_keeps_agent_browser_and_loop_until_explicit_close(self):
		spec = importlib.util.spec_from_file_location('web_server_test', Path(__file__).parents[2] / 'web/server.py')
		assert spec and spec.loader
		web = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(web)
		instances = []

		class Browser:
			def __init__(self, kind, *, keep_alive):
				self.stopped = False
				assert keep_alive

			async def stop(self):
				self.stopped = True

		class Agent:
			def __init__(self, task, *, llm, browser):
				self.tasks = [task]
				self.browser = browser
				self.loop = asyncio.get_running_loop()
				self.closed = False
				instances.append(self)

			def add_new_task(self, task):
				self.tasks.append(task)

			async def run(self, **kwargs):
				assert asyncio.get_running_loop() is self.loop
				assert not self.closed and not self.browser.stopped
				return SimpleNamespace(status='completed', text=' / '.join(self.tasks), partial=None, error=None,
					steps=1, duration_s=0.1, cost_usd=0)

			async def close(self):
				assert asyncio.get_running_loop() is self.loop
				self.closed = True

		worker = web.Worker()
		web.CONVERSATIONS['one'] = {
			'id': 'one', 'title': 'Remember Paris', 'model': '', 'browser': 'chromium', 'status': 'running', 'turns': [],
		}
		try:
			with patch.dict(sys.modules, {'browser_use': SimpleNamespace(Agent=Agent, Browser=Browser)}):
				for text in ('Remember Paris', 'Which city did I mention?'):
					turn = {'task': text, 'status': 'running', 'text': '', 'error': None}
					web.CONVERSATIONS['one']['turns'].append(turn)
					worker.submit(web.execute('one', turn, 10)).result(timeout=5)
					self.assertEqual(turn['status'], 'completed')
				self.assertEqual(len(instances), 1)
				self.assertEqual(instances[0].tasks, ['Remember Paris', 'Which city did I mention?'])
				self.assertEqual(turn['text'], 'Remember Paris / Which city did I mention?')
				self.assertFalse(instances[0].browser.stopped)
				worker.submit(web.close_conversation('one')).result(timeout=5)
				self.assertTrue(instances[0].closed)
				self.assertTrue(instances[0].browser.stopped)
				self.assertEqual(web.CONVERSATIONS['one']['status'], 'closed')
		finally:
			worker.shutdown()

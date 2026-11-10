const $ = (id) => document.getElementById(id);
let runs = [], selected = null, sending = false;
const labels = {running: '执行中', completed: '已完成', error: '执行失败', timeout: '已超时', max_steps: '达到步数上限'};
function render() {
	$('run').disabled = sending || runs.some(run => run.status === 'running');
	$('run').textContent = $('run').disabled ? '任务执行中…' : '开始任务 ↗';
	$('history').replaceChildren();
	if (!runs.length) { const p = document.createElement('p'); p.className = 'muted'; p.textContent = '还没有任务记录'; $('history').append(p); }
	for (const run of [...runs].reverse()) {
		const button = document.createElement('button'); button.textContent = `${run.status === 'running' ? '◌' : '↳'} ${run.task}`;
		button.title = run.task; button.className = selected === run.id ? 'active' : '';
		button.onclick = () => { selected = run.id; render(); }; $('history').append(button);
	}
	const run = runs.find(run => run.id === selected);
	$('result-panel').hidden = !run;
	if (!run) return;
	$('status').textContent = labels[run.status] || run.status;
	$('result-task').textContent = run.task;
	$('result').textContent = run.error || run.text || (run.status === 'running' ? 'Agent 正在浏览器中执行任务，完成后将在这里显示结果。' : '本次任务没有返回文本结果。');
	$('metrics').textContent = run.duration == null ? '单次任务执行预算：300 秒' : `${run.steps} 步 · ${run.duration} 秒${run.cost == null ? '' : ` · $${run.cost.toFixed(4)}`}`;
	$('copy').hidden = !run.text;
}
async function refresh() {
	const response = await fetch('/api/runs');
	if (!response.ok) throw new Error('无法获取任务状态');
	runs = await response.json(); render();
}
$('task-form').onsubmit = async (event) => {
	event.preventDefault(); if (sending) return;
	const task = $('task').value.trim(); if (!task) { $('task').focus(); return; }
	sending = true; $('notice').textContent = ''; render();
	try {
		const response = await fetch('/api/runs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({task, model: $('model').value.trim(), browser: $('browser').value, steps: Number($('steps').value)})});
		const data = await response.json(); if (!response.ok) throw new Error(data.error || '任务启动失败');
		selected = data.id; await refresh();
	} catch (error) { $('notice').textContent = error.message; }
	finally { sending = false; render(); }
};
function newTask() { selected = null; $('task').value = ''; $('notice').textContent = ''; render(); $('task').focus(); }
$('new-task').onclick = newTask;
document.addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); newTask(); } });
document.querySelectorAll('[data-task]').forEach(button => { button.onclick = () => { $('task').value = button.dataset.task; $('task').focus(); }; });
$('copy').onclick = async () => { try { await navigator.clipboard.writeText(runs.find(run => run.id === selected)?.text || ''); $('copy').textContent = '已复制'; setTimeout(() => { $('copy').textContent = '复制结果'; }, 1500); } catch { $('notice').textContent = '复制失败，请手动选择结果文本。'; } };
async function poll() { try { await refresh(); if ($('notice').textContent === '服务连接中断，正在重试…') $('notice').textContent = ''; } catch { $('notice').textContent = '服务连接中断，正在重试…'; } finally { setTimeout(poll, 1500); } }
poll();

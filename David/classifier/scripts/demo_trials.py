"""Run bounded fresh Claude Code trials on self-contained task fixtures."""

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def trial(case: str, index: int, folder: Path, seconds: int, budget: float) -> dict:
    """Run one fresh Sonnet session and retain its native transcript and source changes."""
    template = ROOT / 'demos' / case
    working = folder / case / str(index) / 'project'
    working.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, working, ignore=shutil.ignore_patterns('PROMPT.md', '__pycache__'))
    subprocess.run(['git', '-c', f'safe.directory={working}', 'init', '--quiet'], cwd=working, check=True)
    settings = working / '.claude' / 'settings.json'
    settings.parent.mkdir()
    excludes = [str(parent / 'CLAUDE.md').replace('\\', '/') for parent in working.parents]
    excludes += [str(Path.home() / '.claude/CLAUDE.md').replace('\\', '/')]
    settings.write_text(json.dumps({'claudeMdExcludes': excludes, 'autoMemoryEnabled': False}), encoding='utf-8')
    prompt = (template / 'PROMPT.md').read_text(encoding='utf-8').strip()
    session_id = str(uuid.uuid4())
    executable = shutil.which('claude')
    command = [executable, '-p', prompt, '--model', 'sonnet', '--session-id', session_id,
               '--output-format', 'stream-json', '--verbose', '--setting-sources', 'project',
               '--disable-slash-commands', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
               '--permission-mode', 'acceptEdits', '--allowedTools',
               'Read,Glob,Grep,Edit,Write,Bash(python *),PowerShell(python *),Bash(pytest *),PowerShell(pytest *),Bash(git diff*),PowerShell(git diff*)',
               '--max-budget-usd', str(budget)]
    output = working.parent
    receipt = {'case': case, 'attempt': index, 'session_id': session_id, 'cwd': str(working),
               'prompt': prompt, 'wall_cap_s': seconds, 'budget_cap_usd': budget, 'terminal': False}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    started = time.monotonic()
    with (output / 'transcript.jsonl').open('w', encoding='utf-8') as stdout, (output / 'stderr.log').open('w', encoding='utf-8') as stderr:
        process = subprocess.Popen(command, cwd=working, stdout=stdout, stderr=stderr,
                                   env={**os.environ, 'PYTHONUTF8': '1'})
        receipt['pid'] = process.pid
        (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        try:
            receipt['exit_code'] = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            receipt['timed_out'] = True
            receipt['exit_code'] = process.returncode
    receipt.update(wall_s=time.monotonic() - started, terminal=True)
    records = []
    for line in (output / 'transcript.jsonl').read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            pass
    receipt['init'] = next(({'model': record.get('model'), 'permissionMode': record.get('permissionMode'),
                            'claude_code_version': record.get('claude_code_version')}
                           for record in records if record.get('type') == 'system' and record.get('subtype') == 'init'), None)
    receipt['result'] = next((record for record in reversed(records) if record.get('type') == 'result'), None)
    receipt['tool_calls'] = [{'name': block['name'], 'input': block.get('input', {})}
                             for record in records if record.get('type') == 'assistant'
                             for block in record.get('message', {}).get('content', []) if block.get('type') == 'tool_use']
    completed = subprocess.run([shutil.which('python') or 'python', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                               cwd=working, capture_output=True, text=True, encoding='utf-8', timeout=30)
    (output / 'tests.log').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    receipt['tests_exit_code'] = completed.returncode
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps({'case': case, 'attempt': index, 'exit_code': receipt['exit_code'],
                      'wall_s': receipt['wall_s'], 'tools': len(receipt['tool_calls']), 'init': receipt['init'],
                      'result': (receipt['result'] or {}).get('result')}), flush=True)
    return receipt


def main() -> int:
    """Run a small candidate screen without altering any shared Claude settings."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempts', type=int, default=3)
    parser.add_argument('--cases', nargs='+', default=['refunds', 'customers'], choices=sorted(p.name for p in (ROOT / 'demos').iterdir() if (p / 'PROMPT.md').exists()))
    parser.add_argument('--parallel', type=int, default=2)
    parser.add_argument('--seconds', type=int, default=180)
    parser.add_argument('--budget', type=float, default=1)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    folder = args.output or ROOT / 'results' / 'projects' / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    jobs = [(case, index) for index in range(1, args.attempts + 1) for case in args.cases]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = [pool.submit(trial, case, index, folder, args.seconds, args.budget) for case, index in jobs]
        receipts = [future.result() for future in futures]
    (folder / 'summary.json').write_text(json.dumps(receipts, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

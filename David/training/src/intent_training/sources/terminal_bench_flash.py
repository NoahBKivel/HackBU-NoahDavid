"""Preserve dsh terminal trajectories and keep verifier outcomes out of events."""
import json
import re
from pathlib import Path
from .events import instruction, message, tool

SECRET_PATTERNS = (r'ghp_[A-Za-z0-9]{36}', r'AKIA[0-9A-Z]{16}',
                   r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----',
                   r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'hf_[A-Za-z0-9]{34}', r'sk-ant-[A-Za-z0-9_-]{20,}',
                   r'sk-(?:svcacct|proj)-[A-Za-z0-9_-]{20,}', r'github_pat_[A-Za-z0-9_]{22,}')


def scrub(value):
    """Remove credential-shaped source text before emitting any record."""
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            value = re.sub(pattern, '[REDACTED CREDENTIAL]', value, flags=re.S)
        return value
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    return value


DATASET = 'openguardrails/terminal-bench-2.1-deepseek-v4-flash-trajectories'


def text(blocks):
    """Extract visible text without exposing model reasoning."""
    if isinstance(blocks, str):
        return blocks
    return '\n'.join(b.get('text', '') for b in blocks or [] if b.get('type') == 'text')


def convert(raw_dir: Path):
    """Yield complete dsh event streams with outcome evidence as teacher hints."""
    for path in sorted(Path(raw_dir).rglob('dsh-session.jsonl')):
        if 'dsh' not in path.parts:
            continue
        result_path = path.with_name('dsh-result.json')
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding='utf-8'))
        final = result.get('final_response')
        if not isinstance(final, str) or not final.strip():
            continue
        records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        responses = {}
        for row in records:
            if row['type'] == 'tool/result':
                for block in row['data']['message'].get('content', []):
                    if block['type'] == 'tool-result':
                        responses[block['toolCallId']] = (text(block.get('content')), bool(block.get('isError', False)))
        events, reasoning = [], {}
        pending_text, pending_reasoning = [], []
        def append(event):
            events.append(event)
            if pending_reasoning:
                reasoning[str(event['seq'])] = '\n'.join(pending_reasoning)
                pending_reasoning.clear()
        for row in records:
            data = row.get('data', {})
            if row['type'] == 'user/message':
                value = text(data.get('content'))
                if value:
                    append(instruction(value, len(events) + 1))
            elif row['type'] == 'assistant/message':
                content = data['message'].get('content', [])
                for b in content:
                    if b['type'] in {'thinking', 'reasoning'}:
                        pending_reasoning.append(b.get('thinking', b.get('text', '')))
                visible = text(content)
                if any(b['type'] == 'tool-call' for b in content):
                    if visible:
                        pending_text.append(visible)
                elif visible and visible != final:
                    append(message(visible, len(events) + 1))
            elif row['type'] == 'tool/call':
                args = data.get('arguments', {})
                if isinstance(args, str):
                    args = json.loads(args)
                name = data['name']
                changes = None
                if name == 'bash':
                    name = 'Bash'
                elif name == 'str_replace_editor':
                    command = args.get('command')
                    name = 'Read' if command == 'view' else 'Write' if command == 'create' else 'Edit'
                    if name in {'Edit', 'Write'} and args.get('path'):
                        changes = [{'path': args['path'], 'op': 'write' if name == 'Write' else 'edit', 'patch': None}]
                output, error = responses.get(data['callId'], ('', False))
                append(tool(name, args, output, len(events) + 1, is_error=error,
                            agent_text='\n'.join(pending_text), file_changes=changes))
                pending_text.clear()
        append(message(final, len(events) + 1))
        trial = path.parent.parent
        verifier = trial / 'verifier'
        side = {'reasoning': reasoning, 'source_labels': [], 'outcome': {
            'basis': 'O', 'origin': DATASET, 'verifier_stdout': (verifier / 'test-stdout.txt').read_text(encoding='utf-8') if (verifier / 'test-stdout.txt').exists() else None,
            'reward': (verifier / 'reward.txt').read_text(encoding='utf-8').strip() if (verifier / 'reward.txt').exists() else None}}
        session = next((r.get('id') for r in records if r['type'] == 'session'), trial.name)
        meta = {'source': 'terminal_bench_flash', 'trajectory_id': session, 'task_id': trial.name,
                'source_record_id': session, 'objective': ['M5', 'G5'], 'licence': 'MIT; task definitions retain Terminal-Bench licence', 'harness': 'dsh'}
        yield scrub(events), scrub(side), meta



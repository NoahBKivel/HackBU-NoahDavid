"""Convert rendered Claude sessions with localized Stop-hook and recovery cuts."""
import copy
from itertools import chain
import json
from pathlib import Path
import re

from .events import instruction, message, tool
from .reading import rows

HOOK = 'Stop hook feedback:'
BLOCKS = re.compile(r'(?m)^---[ \t]*\r?\n(?:[ \t]*\r?\n)*(?=\*\*(?:User|Claude|Tool result|Thinking):\*\*|> \x60)')
LABEL = re.compile(r'^\*\*(User|Claude|Tool result|Thinking):\*\*[^\n]*\n*')
CALL = re.compile(r'^> `([^`]+)`\s*(?:--|\u2014)\s*([\s\S]*)$')
BYPASS = re.compile(r'bypass|--force(?:-unsafe)?|--no-verify|dangerously[-_]skip|disable.{0,15}(?:hook|guard)', re.I)
AUTOMATION = re.compile(r'<scheduled-task|scheduled[ -]task|headless|robot_inbox_prompt|the user is not present', re.I)
ROLE = re.compile(r'^\s*(?:you are\b|act as\b|your role\b|ты\s+(?:являешься|ревьюер|судья)|ты\s*[\u2014-]\s*)', re.I)
PRIVATE_CONTEXT = re.compile(r'\b(?:passport|social security|date of birth|diagnosis|диагноз|паспорт|супруг[аи]|дочер[ьи]|сын[ау]|родственник)\b', re.I)
PII = [
    (re.compile(r'\b\d{7,}\b'), '[ID]'),
    (re.compile(r'(?<=[а-яёa-z]\s)[А-ЯЁ][а-яё]{2,}\b'), '[PERSON]'),
    (re.compile(r'(?<![\w.+-])[\w.+-]{1,128}@[\w.-]{1,253}\.[A-Za-z]{2,63}\b'), '[EMAIL]'),
    (re.compile(r'(?<!\w)\+\d[\d ()-]{8,}\d'), '[PHONE]'),
    (re.compile(r'(?i)([A-Z]:[\\/]+Users[\\/]+|/home/|/Users/)[^\\/\s"\x27]+'), r'\1[USER]'),
    (re.compile(r'\b[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{3,}(?:\s+[А-ЯЁ][а-яё]{3,})?\b'), '[PERSON]'),
    (re.compile(r'\b(?:sk-ant-|sk-proj-|sk-svcacct-|ghp_|github_pat_|hf_)[A-Za-z0-9_-]{16,}'), '[SECRET]'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), '[SECRET]'),
]


def scrub(text):
    """Apply an additional conservative identity and credential pass."""
    for pattern, replacement in PII:
        text = pattern.sub(replacement, text)
    return text


def parse(text):
    """Read source separators and labels without promoting tool output to instructions."""
    parts = []
    for chunk in BLOCKS.split(text):
        chunk = chunk.strip()
        match = LABEL.match(chunk)
        if match:
            parts.append((match[1], chunk[match.end():].strip()))
        elif CALL.match(chunk):
            parts.append(('call', chunk))
        elif chunk and not parts:
            # Export summaries precede the actual conversation and are not user context.
            start = re.search(r'(?m)^\*\*User:\*\*', chunk)
            if start:
                parts.append(('User', LABEL.sub('', chunk[start.start():], count=1).strip()))
        elif chunk:
            raise ValueError('An unrecognized source block cannot be replayed safely.')
    return parts


def normalize(parts):
    events, reasoning = [], {}
    pending = []
    for index, (kind, body) in enumerate(parts):
        if kind == 'User':
            if pending:
                events.append(message('\n\n'.join(pending), len(events)+1))
                pending = []
            events.append(instruction(body, len(events)+1))
        elif kind == 'Claude':
            pending.append(body)
            if index + 1 == len(parts) or parts[index+1][0] == 'User':
                events.append(message('\n\n'.join(pending), len(events)+1))
                pending = []
        elif kind == 'Thinking':
            reasoning[str(len(events)+1)] = body
        elif kind == 'call':
            match = CALL.match(body)
            name, raw = match.groups()
            try:
                args = json.loads(raw)
            except ValueError:
                args = {'raw': raw}
            result = parts[index+1][1] if index+1 < len(parts) and parts[index+1][0] == 'Tool result' else ''
            events.append(tool(name, args, result, len(events)+1, agent_text='\n\n'.join(pending)))
            pending = []
    if pending:
        events.append(message('\n\n'.join(pending), len(events)+1))
    return events, reasoning


def convert(raw_dir: Path):
    """Yield claims, recoveries and complete filtered streams with teacher-only hints."""
    seen = set()
    canonical = sorted(Path(raw_dir).glob('rows-*.jsonl')) if Path(raw_dir).is_dir() else []
    inputs = canonical or [raw_dir]
    for row in chain.from_iterable(rows(path) for path in inputs):
        if row.get('provider') != 'claude' or row.get('_truncated_cells'):
            continue
        sid = row.get('session_id')
        if not sid or sid in seen:
            continue
        seen.add(sid)
        text = row.get('text', '')
        if HOOK not in text and (BYPASS.search(text) or AUTOMATION.search(text)):
            continue
        if PRIVATE_CONTEXT.search(text):
            continue
        try:
            parts = parse(scrub(text))
        except ValueError:
            continue
        if not parts or parts[0][0] != 'User':
            continue
        base = dict(source='agent_sessions', trajectory_id=sid, licence='CC-BY-4.0', harness='claude-code', dataset='TonyDzi/agent-sessions')
        hook_indices = [i for i, (kind, body) in enumerate(parts) if kind == 'User' and body.startswith(HOOK)]
        if hook_indices:
            index = hook_indices[0]
            prior, reasoning = normalize(parts[:index])
            if not prior or prior[-1]['type'] != 'turn_completed':
                continue
            cut = prior[-1]['seq']
            hint = dict(question='M5', value=parts[index][1], event_seq=cut, basis='outcome', origin='Stop-hook text; teacher hint only')
            side = dict(reasoning=reasoning, source_labels=[hint], privacy_pass='regex identities and credentials; private family/medical contexts excluded')
            yield prior, copy.deepcopy(side), dict(base, objective=['M5','G5'], cut_seq=cut, source_record_id=sid+':claim', slice='claim')
            stop = next((j for j in range(index+1,len(parts)) if parts[j][0] == 'User'), len(parts))
            recovery, recovery_reasoning = normalize(parts[:stop])
            if recovery and recovery[-1]['type'] == 'turn_completed' and recovery[-1]['seq'] > cut+1:
                side = dict(reasoning=recovery_reasoning, source_labels=[hint], correction=parts[index][1], findings=[dict(id='F1',question='M1',event_seqs=[cut],correction_seq=cut+1)], finding_question_rule='First teacher-positive question at the hooked event in item order; M1 when none is positive.', hooked_event_seq=cut, correction_seq=cut+1)
                yield recovery, side, dict(base,objective=['L7'],cut_seq=recovery[-1]['seq'],source_record_id=sid+':recovery',slice='recovery')
        elif HOOK not in text and not BYPASS.search(text) and not AUTOMATION.search(text) and not ROLE.search(parts[0][1]):
            events, reasoning = normalize(parts)
            if any(item['type'] == 'tool_completed' for item in events) and any(item['type'] == 'turn_completed' for item in events):
                yield events, dict(reasoning=reasoning,source_labels=[],filter_hint='Tool-using session passed hook, bypass, automation, role and privacy filters; teacher labels every question.'), dict(base,objective=[],source_record_id=sid+':benign',slice='benign')



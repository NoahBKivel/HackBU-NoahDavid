"""Verify source cuts, visible recoveries, privacy and clarification preservation."""
import json
from intent_training.sources.agent_sessions import convert, parse, normalize, scrub
from monitor_format import validate_events


def source(tmp_path, text):
    (tmp_path / 'sessions.jsonl').write_text(json.dumps(dict(provider='claude', session_id='session', text=text)), encoding='utf-8')
    return list(convert(tmp_path))


def test_hook_prefix_excludes_future_and_recovery_is_visible(tmp_path):
    raw = '**User:**\n\nПроверь файл.\n\n---\n\n> `Read` -- {"file_path":"x"}\n\n---\n\n**Tool result:**\n\nexists\n\n---\n\n**Claude:**\n\nФайла нет.\n\n---\n\n**User:**\n\nStop hook feedback: Файл есть.\n\n---\n\n**Claude:**\n\nИсправляю ответ.\n\n---\n\n**User:**\n\nFuture correction must stay outside.'
    claim, recovery = source(tmp_path, raw)
    for events, side, meta in (claim, recovery):
        validate_events(events)
        assert all(not e['agent_thinking'] for e in events)
        assert 'Future correction' not in json.dumps(events)
    assert 'Stop hook' not in json.dumps(claim[0])
    assert claim[0][-1]['agent_text'] == 'Файла нет.'
    assert claim[1]['source_labels'][0]['basis'] == 'outcome'
    assert recovery[0][-2]['new_items'][0]['text'].startswith('Stop hook feedback:')
    assert recovery[1]['findings'][0]['event_seqs'] == [claim[2]['cut_seq']]


def test_benign_requires_tools_and_excludes_automation(tmp_path):
    raw = '**User:**\n\nCheck status.\n\n---\n\n> `Bash` -- {"command":"git status"}\n\n---\n\n**Tool result:**\n\nclean\n\n---\n\n**Claude:**\n\nClean.'
    assert source(tmp_path, raw)[0][2]['objective'] == []
    assert not source(tmp_path, raw.replace('Check status.', '<scheduled-task>Check status.'))
    assert not source(tmp_path, raw.replace('git status', 'git push --no-verify'))
    assert not source(tmp_path, raw.replace('Check status.', 'claude --permission-mode bypassPermissions'))
    assert not source(tmp_path, '**User:**\n\nHello.\n\n---\n\n**Claude:**\n\nHi.')


def test_question_answers_are_verbatim_and_reasoning_is_side_only():
    parts = parse('**User:**\n\nChoose.\n\n---\n\n**Thinking:**\n\nPrivate reasoning.\n\n---\n\n> `AskUserQuestion` -- {"question":"Which?"}\n\n---\n\n**Tool result:**\n\nПользователь выбрал: «A».\n\n---\n\n**Claude:**\n\nSelected A.')
    events, reasoning = normalize(parts)
    validate_events(events)
    assert events[1]['action']['result_text'] == 'Пользователь выбрал: «A».'
    assert list(reasoning.values()) == ['Private reasoning.']
    assert all(not e['agent_thinking'] for e in events)
    assert '[EMAIL]' in scrub('Contact user@example.org')
    assert '[PERSON]' in scrub('Иван Петров')


def test_internal_markdown_separator_remains_in_instruction():
    content = '**User:**\n\nInspect this policy.\n\n---\n\nPreserve the section below.\n\n---\n\n**Claude:**\n\nI will inspect it.'
    events, _ = normalize(parse(content))
    assert events[0]['new_items'][0]['text'] == 'Inspect this policy.\n\n---\n\nPreserve the section below.'
    assert len(events) == 2


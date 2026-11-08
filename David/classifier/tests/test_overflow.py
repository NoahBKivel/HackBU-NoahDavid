import pytest

from David import monitor_format as shared
from intent_runtime.overflow import screen
from intent_runtime.store import SessionStore


class Tokenizer:
    def __call__(self, text, **kwargs):
        return {'input_ids': list(range(len(text.split())))}


class Runner:
    def __init__(self, scores=None):
        self.scores = scores or {}
        self.calls = []

    def ask_many(self, requests):
        self.calls.append(requests)
        return [{key: {'false': 1 - self.scores.get(key, .1), 'true': self.scores.get(key, .1)}
                 for key in questions} for _, questions in requests]


def session(documents):
    store = SessionStore({})
    state = store.get('fixture')
    event = {'event_id': 'one', 'seq': 1, 'type': 'tool_completed', 'todos': [], 'new_items': [],
             'action': {'tool': 'Bash', 'args': {'command': 'pytest'}, 'result_text': '2 passed'}}
    store.add(state, event)
    state.header['documents'] = documents
    return state, event


def test_screens_all_sections_in_one_queued_submission_with_global_references():
    documents = {f'doc-{index}.md': '# Shared heading\n' + ('word ' * 70) for index in range(12)}
    state, event = session(documents)
    runner = Runner()
    result = screen(state, [], event, runner, Tokenizer(), 8192, [])
    assert len(runner.calls) == 1
    assert len(runner.calls[0]) == 2
    assert [len(rows) for _, rows in runner.calls[0]] == [20, 4]
    assert list(result['screen_sections']) == [f'S{index}' for index in range(1, 13)]
    assert [section['path'] for section in result['screen_sections'].values()] == list(documents)
    assert all(shared.count_tokens(text, Tokenizer()) <= 8192 for text, _ in runner.calls[0])
    assert result['overflow'] and result['screen_fired'] == {}


def test_selection_cutoff_and_lowest_score_drop_preserve_screen_findings():
    state, event = session({'first.md': '# Shared heading\n' + ('first ' * 70),
                            'second.md': '# Shared heading\n' + ('second ' * 70)})
    runner = Runner({'SCR#S1': .9, 'M8#S2': .5})
    result = screen(state, [], event, runner, Tokenizer(), 150, [])
    assert '=== first.md › Shared heading ===' in result['text']
    assert '=== second.md › Shared heading ===' not in result['text']
    assert result['screen_fired'] == {'M8#S2': .5}
    assert result['screen_sections']['S2']['text'].startswith('# Shared heading')
    assert result['row_budget'] == 150 + 640 - shared.count_tokens(result['text'], Tokenizer()) - 1


def test_picked_documents_keep_original_order_and_duplicate_headings():
    state, event = session({'first.md': '# Duplicate\nFirst constraint.',
                            'second.md': '# Duplicate\nSecond constraint.'})
    runner = Runner({'SCR#S1': .5, 'M8#S2': .8})
    result = screen(state, [], event, runner, Tokenizer(), 8192, [])
    assert result['text'].index('first.md › Duplicate') < result['text'].index('second.md › Duplicate')
    assert result['screen_fired'] == {'M8#S2': .8}


def test_no_picked_sections_returns_the_shared_document_free_state():
    state, event = session({'unused.md': '# Context\nUnrelated information.'})
    runner = Runner({'SCR#S1': .49, 'M8#S1': .49})
    result = screen(state, [], event, runner, Tokenizer(), 8192, [])
    expected, detailed, fits = shared.render_state([], [], state.events, 1, [], 8191, tokenizer=Tokenizer())
    assert fits and result['text'] == expected and result['detailed'] == detailed
    assert result['screen_fired'] == {}


def test_instructions_exceeding_normal_switch_raise_before_model_calls():
    state, event = session({'doc.md': 'A constraint.'})
    runner = Runner()
    with pytest.raises(OverflowError, match='instructions'):
        screen(state, [{'id': 'I1', 'text': 'instruction ' * 500}], event, runner, Tokenizer(), 100, [])
    assert runner.calls == []


def test_no_screen_room_raises_without_truncating_instructions():
    state, event = session({'doc.md': 'A constraint.'})
    runner = Runner()
    with pytest.raises(OverflowError, match='instructions'):
        screen(state, [{'id': 'I1', 'text': 'instruction ' * 8200}], event, runner, Tokenizer(), 32768, [])
    assert runner.calls == []

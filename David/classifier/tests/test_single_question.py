import time

import pytest

from intent_runtime.calibration import Calibrator
from intent_runtime.single_question import SingleQuestionRuntime
from intent_runtime.store import SessionStore


def test_existing_builder_uses_ordered_verbatim_instructions_and_calibration():
    class Runner:
        def ask(self, state, questions):
            assert state == ['Keep coverage.', 'Use the API.']
            return {'M1': Calibrator({'M1': {'T': 2, 'b': 0}}, 4).apply('M1', [.2, .8], ['false', 'true'])}
    store = SessionStore({})
    runtime = SingleQuestionRuntime(store, Runner(), lambda instructions, event: instructions, 'Fixture question.', 'stock-kev')
    for seq, text in enumerate(['Keep coverage.', 'Use the API.'], 1):
        runtime.classify({'session_id': 'single', 'event_id': str(seq), 'seq': seq, 'type': 'session_started',
                          'new_items': [{'kind': 'user_instruction', 'text': text}]})
    result = runtime.classify({'session_id': 'single', 'event_id': '3', 'seq': 3, 'type': 'tool_completed', 'action': {'tool': 'Edit'}})
    assert result['risk'] == pytest.approx(2/3)
    assert result['flagged'] and result['actions'] == []
    assert store.mapping['single']['last_seq'] == 3


def test_existing_builder_handles_skipped_late_results_once():
    runtime = SingleQuestionRuntime(SessionStore({}), None, None, 'Fixture question.', 'stock-kev')
    base = {'session_id': 'single', 'type': 'tool_completed', 'action': {'tool': 'Read'}}
    runtime.classify({**base, 'event_id': '1', 'seq': 1, 'backend_sent_at': time.time() - 9})
    next_result = runtime.classify({**base, 'event_id': '2', 'seq': 2})
    assert next_result['risk'] is None and next_result['details']['skipped']
    assert [r['event_id'] for r in next_result['late_results']] == ['1']
    assert 'late_results' not in runtime.classify({**base, 'event_id': '3', 'seq': 3})

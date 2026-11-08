import copy
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from intent_runtime.firing import EVERY_EVENT
from intent_runtime.service import Runtime
from intent_runtime.store import SessionStore
from verify_deploy import Result


def event(seq, tool='Bash', **extra):
    return {'session_id': 'fixture', 'event_id': f'e{seq}', 'seq': seq,
            'type': 'tool_completed', 'action': {'tool': tool, 'args': {'command': 'pytest'}, 'denied': None}, **extra}


class FixtureFormats:
    short_names = {key: f'Fixture {key}' for key in (*EVERY_EVENT, 'G2', 'G5')}

    def instructions(self, events):
        self.instruction_calls = getattr(self, 'instruction_calls', 0) + 1
        return [item['text'] for e in events for item in e.get('new_items', []) if item['kind'] == 'user_instruction']

    def update_units(self, session, instructions, event, runner):
        pass

    def render(self, session, instructions, event, runner):
        self.events = session.ordered_events()
        return {'text': 'Fixture state.', 'detailed': [event['seq']]}

    def questions(self, keys, header, context, **extra):
        return {key: {'type': 'noul', 'instructions': 'Fixture wording.'} for key in keys}

    def names(self, fired):
        return ', '.join(self.short_names[key.split('#')[0]] for key in fired)

    def correction(self, findings, session, instructions, context, requirements):
        return 'Fixture correction.'


class FixtureRunner:
    def __init__(self):
        self.overrides = {}
        self.asked = []

    def ask(self, state, questions):
        self.asked.extend(questions)
        result = {}
        for key in questions:
            base = key.split('#')[0]
            default = {'false': .9, 'true': .1}
            if base == 'G1':
                default = {'false': .1, 'true': .9}
            elif base == 'D5':
                default = {'0': .1, '1': .8, '2': .1}
            elif base == 'L7':
                default = {'genuinely fixed': .05, 'dismissed correctly': .9, 'ignored': .05}
            elif base == 'G2':
                default = {'done': .05, 'broken': .05, 'not done': .9}
            result[key] = copy.deepcopy(self.overrides.get(key, self.overrides.get(base, default)))
        return result


@pytest.fixture
def runtime():
    return Runtime(SessionStore({}), FixtureRunner(), FixtureFormats(), 'stock-kev')


def checked(runtime, e):
    result = runtime.classify(e)
    Result.model_validate(result)
    for late in result.get('late_results', []):
        Result.model_validate(late)
    return result


@pytest.mark.parametrize('e', [event(1, 'Read'), event(1, 'AskUserQuestion'),
    event(1, type='session_started'), event(1, type='turn_completed', action=None, turn={'reason':'aborted'}, agent_text='')])
def test_skipped_events_accept_context(runtime, e):
    e['new_items'] = [{'kind': 'user_instruction', 'text': 'Keep coverage.'}, {'kind': 'project_doc', 'path': 'README.md', 'text': 'A complete document.'}]
    result = checked(runtime, e)
    assert result['risk'] is result['drift'] is result['drift_rate'] is None
    assert result['actions'] == [] and result['details']['skipped'] and not result['flagged']
    assert runtime.runner.asked == []
    session = runtime.store.get('fixture')
    assert session.header['documents']['README.md'] == 'A complete document.'
    assert session.header['new_instruction_pending']
    assert runtime.formats.instruction_calls == 1


def test_duplicate_is_not_stored_and_late_arrival_is_stored(runtime):
    session = runtime.store.get('fixture')
    session.gate.wait_seconds = .01
    checked(runtime, event(3))
    stale = event(1, new_items=[{'kind': 'user_instruction', 'text': 'Keep the API.'}])
    result = checked(runtime, stale)
    assert result['details']['skipped']
    assert session.header['last_seq'] == 3
    assert [e['seq'] for e in session.ordered_events()] == [1, 3]
    assert checked(runtime, stale)['details']['skipped']
    assert len(session.events) == 2
    assert runtime.formats.instruction_calls == 2


def test_dismissed_run_does_not_reopen_until_instruction_on_skipped_read(runtime):
    runtime.runner.overrides['L1'] = {'false': .1, 'true': .9}
    assert len(checked(runtime, event(1))['actions']) == 3
    checked(runtime, event(2, 'Read'))
    assert checked(runtime, event(3))['actions'] == []
    assert runtime.store.get('fixture').header['findings'][0]['status'] == 'dismissed'
    runtime.runner.asked.clear()
    assert checked(runtime, event(4))['actions'] == []
    assert 'D5' not in runtime.runner.asked
    checked(runtime, event(5, 'Read', new_items=[{'kind': 'user_instruction', 'text': 'Continue with the original goal.'}]))
    assert len(checked(runtime, event(6))['actions']) == 3
    assert len(runtime.store.get('fixture').header['findings']) == 2


def test_dismissed_action_does_not_suppress_a_later_action(runtime):
    runtime.runner.overrides['M4'] = {'false': .1, 'true': .9}
    checked(runtime, event(1))
    checked(runtime, event(2, 'Read'))
    result = checked(runtime, event(3))
    assert [a['type'] for a in result['actions']] == ['notify_user', 'inject_agent', 'notify_user']
    assert runtime.store.get('fixture').header['findings'][0]['status'] == 'closed'


def test_minor_run_finding_upgrades_with_new_evidence(runtime):
    runtime.runner.overrides.update(L1={'false': .2, 'true': .8}, D5={'0': .8, '1': .1, '2': .1})
    first = checked(runtime, event(1))
    assert [a['level'] for a in first['actions']] == ['potential']
    runtime.runner.overrides['D5'] = {'0': .1, '1': .8, '2': .1}
    second = checked(runtime, event(2))
    assert [a['type'] for a in second['actions']] == ['notify_user', 'inject_agent', 'notify_user']
    findings = runtime.store.get('fixture').header['findings']
    assert len(findings) == 1 and findings[0]['severity'] == 'significant'
    assert findings[0]['cited'] == [2]


def test_turn_end_not_done_sends_no_correction(runtime):
    session = runtime.store.get('fixture')
    session.header['units'] = [{'accepted': True, 'k': 1, 'text': 'Keep coverage.'}]
    result = checked(runtime, event(1, type='turn_completed', action=None, agent_text='', turn={'reason': 'answer'}))
    assert runtime.runner.asked == ['G2#R1', 'G5']
    assert result['actions'] == [] and result['details']['not_done'] == ['Keep coverage.']
    assert result['drift'] is None


def test_g1_sign_and_pane_window(runtime):
    runtime.runner.overrides['G1'] = {'false': .8, 'true': .2}
    first = checked(runtime, event(1))
    assert first['details']['fired'] == {'G1': .8}
    assert first['drift'] == .8 and not first['flagged'] and first['risk'] == .1
    assert first['drift_rate'] is None
    for seq in range(2, 7):
        checked(runtime, event(seq))
    runtime.runner.overrides['G1'] = {'false': .2, 'true': .8}
    last = checked(runtime, event(7))
    assert last['drift_rate'] == pytest.approx((.2 - .8) / 5)


def test_backend_timestamp_late_delivery_once_and_persistence(runtime):
    runtime.runner.overrides['M4'] = {'false': .1, 'true': .9}
    old = event(1, backend_sent_at=time.time() - 9)
    checked(runtime, old)
    session = runtime.store.get('fixture')
    assert session.header['pending_correction_marks'] == []
    result = checked(runtime, event(2, 'Read'))
    assert [r['event_id'] for r in result['late_results']] == ['e1']
    assert session.header['pending_correction_marks'] == ['F1']
    assert 'late_results' not in checked(runtime, event(3, 'Read'))
    assert session.header['findings'][0]['reached_at'] == 3
    rebuilt = SessionStore(runtime.store.mapping).get('fixture')
    assert rebuilt.header['last_seq'] == 3
    assert rebuilt.events == session.events


def test_correction_reaches_only_eligible_arrival_and_followup_is_strict(runtime):
    runtime.runner.overrides['L1'] = {'false': .1, 'true': .9}
    checked(runtime, event(1))
    checked(runtime, event(2, type='turn_completed', agent_text='Continuing.', turn={'reason': 'aborted'}))
    denied = event(3)
    denied['action']['denied'] = 'Blocked.'
    checked(runtime, denied)
    runtime.runner.asked.clear()
    checked(runtime, event(4))
    assert 'L7#M1' not in runtime.runner.asked
    assert runtime.store.get('fixture').header['findings'][0]['reached_at'] == 4
    runtime.runner.asked.clear()
    checked(runtime, event(5))
    assert 'L7#M1' in runtime.runner.asked


def test_exception_advances_and_persists_sequence(runtime):
    original = runtime.formats.render
    runtime.formats.render = lambda *args: (_ for _ in ()).throw(ValueError('Fixture failure.'))
    with pytest.raises(ValueError):
        checked(runtime, event(1))
    runtime.formats.render = original
    assert checked(runtime, event(2))['risk'] == .1
    assert runtime.store.mapping['fixture']['last_seq'] == 2

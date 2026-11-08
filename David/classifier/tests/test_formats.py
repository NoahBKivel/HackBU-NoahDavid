from David import monitor_format as shared
from intent_runtime.formats import Formats
from intent_runtime.store import SessionStore
from intent_runtime.service import Runtime
from intent_runtime.findings import open_or_upgrade


class Tokenizer:
    def __call__(self, text, **kwargs):
        return {'input_ids': list(range(len(text.split())))}


def test_adapter_state_is_exactly_the_shared_renderer_output():
    tokenizer = Tokenizer()
    formats = Formats(tokenizer)
    store = SessionStore({})
    session = store.get('fixture')
    event = {'event_id': 'one', 'seq': 1, 'type': 'tool_completed',
             'action': {'tool': 'Bash', 'args': {'command': 'pytest'}, 'result_text': '2 passed'},
             'new_items': [{'kind': 'user_instruction', 'text': 'Keep coverage.'}], 'todos': []}
    store.add(session, event)
    instructions = formats.instructions(session.events)
    actual = formats.render(session, instructions, event, None)
    expected, detailed, fits = shared.render_state(instructions, {}, session.events, 1, [], 8191, tokenizer=tokenizer)
    assert fits and actual['text'] == expected and actual['detailed'] == detailed


def test_only_delivered_findings_appear_in_shared_state():
    formats = Formats(Tokenizer())
    store = SessionStore({})
    session = store.get('fixture')
    event = {'event_id': 'one', 'seq': 1, 'type': 'tool_completed',
             'action': {'tool': 'Bash', 'args': {'command': 'pytest'}, 'result_text': ''}, 'todos': []}
    store.add(session, event)
    finding = {'id': 'F1', 'question': 'M4', 'cited': [1], 'message': 'M1',
               'reached_at': None, 'status': 'open', 'last_l7': 'open'}
    session.header['findings'] = [finding]
    assert '[F1]' not in formats.render(session, [], event, None)['text']
    finding['reached_at'] = 1
    text = formats.render(session, [], event, None)['text']
    assert shared.open_findings_line({'id': 'F1', 'question': 'M4', 'event_seqs': [1],
                                     'correction_seq': 1, 'status': 'open'}) in text


def test_g2_and_diagnostic_rows_use_shared_fillers():
    formats = Formats(Tokenizer())
    header = {'units': [{'accepted': True, 'k': 1, 'text': 'Keep coverage.'}], 'messages': {}}
    rows = formats.questions(['G2#R1', 'D1#E2'], header, {'row_budget': 640}, fired_questions=['M4'])
    assert rows['G2#R1'] == shared.fill_question('G2', requirement_text='Keep coverage.', tokenizer=formats.tokenizer)
    assert rows['D1#E2'] == shared.fill_question('D1', event_seq=2, fired_questions=['M4'], tokenizer=formats.tokenizer)


def test_shared_adapter_delivers_a_real_correction_and_tracks_its_arrival():
    class Runner:
        def ask(self, state, questions):
            answers = {}
            for key, question in questions.items():
                base = key.split('#')[0]
                if question['type'] == 'noul':
                    yes = .9 if base in {'RF', 'M4', 'G1', 'D1'} else .1
                    answers[key] = {'false': 1 - yes, 'true': yes}
                elif question['type'] == 'score':
                    answers[key] = {'0': .1, '1': .8, '2': .1}
                else:
                    options = list(question['criteria'])
                    selected = 'ignored' if base == 'L7' else 'done'
                    answers[key] = {option: .9 if option == selected else .1 / (len(options) - 1) for option in options}
            return answers

        def ask_many(self, requests):
            return [self.ask(state, questions) for state, questions in requests]

    store = SessionStore({})
    runtime = Runtime(store, Runner(), Formats(Tokenizer()), 'stock-kev')
    runtime.classify({'session_id': 'fixture', 'event_id': 'start', 'seq': 1, 'type': 'session_started',
                      'new_items': [{'kind': 'user_instruction', 'text': 'Preserve coverage.'}]})
    result = runtime.classify({'session_id': 'fixture', 'event_id': 'delete', 'seq': 2, 'type': 'tool_completed',
                               'action': {'tool': 'Bash', 'args': {'command': 'rm tests/test_slow.py'},
                                          'result_text': 'Removed.', 'denied': None}})
    assert result['flagged'] and result['risk'] == .9
    assert [action['type'] for action in result['actions']] == ['notify_user', 'inject_agent', 'notify_user']
    assert 'gamed measure' in result['actions'][1]['text']
    assert 'rm tests/test_slow.py' in result['actions'][1]['text']
    runtime.classify({'session_id': 'fixture', 'event_id': 'read', 'seq': 3, 'type': 'tool_completed',
                      'action': {'tool': 'Read', 'args': {'file_path': 'README.md'}, 'denied': None}})
    assert store.get('fixture').header['findings'][0]['reached_at'] == 3


def test_overflow_findings_cite_the_latest_action_and_quote_the_section():
    findings = []
    opened = open_or_upgrade(findings, {'M8#S1': .9, 'M4': .8}, 9, 'significant', [2, 4])
    assert opened[0]['cited'] == [9]
    assert opened[1]['cited'] == [2, 4]
    formats = Formats(Tokenizer())
    store = SessionStore({})
    session = store.get('fixture')
    event = {'event_id': 'latest', 'seq': 9, 'type': 'tool_completed',
             'action': {'tool': 'Bash', 'args': {'command': 'rm tests/test_slow.py'}, 'result_text': 'Removed.'}}
    context = {'events': [event], 'screen_sections': {'S1': {'text': 'Preserve every test file.'}}}
    message = formats.correction([opened[0]], session, [], context, [])
    assert 'Preserve every test file.' in message
    assert 'stated requirement at E9' in message


def test_adapter_dispatches_over_budget_documents_to_the_screen():
    class Runner:
        def ask_many(self, requests):
            self.requests = requests
            return [{key: {'false': .9, 'true': .1} for key in questions} for _, questions in requests]
    formats = Formats(Tokenizer(), 200)
    store = SessionStore({})
    session = store.get('fixture')
    event = {'event_id': 'latest', 'seq': 1, 'type': 'tool_completed',
             'action': {'tool': 'Bash', 'args': {'command': 'git status'}, 'result_text': ''}, 'todos': []}
    store.add(session, event)
    session.header['documents'] = {'appendix.md': 'Unrelated appendix facts.\n\n' * 200}
    runner = Runner()
    context = formats.render(session, [], event, runner)
    assert context['overflow'] and runner.requests
    assert context['screen_fired'] == {}

from intent_runtime.store import SessionStore
from intent_runtime.units import update_units
from David import monitor_format as shared


class Runner:
    def __init__(self):
        self.requests = []

    def ask_many(self, requests):
        self.requests.extend(requests)
        return [{'RF': {'false': .1, 'true': .9}} for _ in requests]


def add(store, session, runner, event):
    store.add(session, event)
    instructions = shared.build_instructions(session.ordered_events())
    update_units(session, instructions, event, runner)


def test_instruction_renumbering_preserves_accepted_requirement_identity():
    store = SessionStore({})
    session = store.get('fixture')
    runner = Runner()
    add(store, session, runner, {'event_id': 'later', 'seq': 2, 'new_items': [
        {'kind': 'user_instruction', 'text': 'Keep coverage.'}]})
    original = session.header['units'][0]['k']
    add(store, session, runner, {'event_id': 'earlier', 'seq': 1, 'new_items': [
        {'kind': 'user_instruction', 'text': 'Keep the API.'}]})
    kept = next(unit for unit in session.header['units'] if unit['text'] == 'Keep coverage.')
    assert kept['source'] == '[I2]' and kept['k'] == original
    assert len(runner.requests) == 2


def test_document_replacement_removes_old_units_and_asks_rf_again():
    store = SessionStore({})
    session = store.get('fixture')
    runner = Runner()
    for seq, text in [(1, 'Keep coverage.'), (2, 'Preserve the API.')]:
        add(store, session, runner, {'event_id': str(seq), 'seq': seq, 'new_items': [
            {'kind': 'project_doc', 'path': 'README.md', 'text': text}]})
    assert [unit['text'] for unit in session.header['units']] == ['Preserve the API.']
    assert session.header['units'][0]['k'] == 2
    assert len(runner.requests) == 2


def test_requirement_acceptance_uses_the_calibrated_half_cutoff():
    class BoundaryRunner:
        def ask_many(self, requests):
            assert len(requests) == 2
            return [{'RF': {'false': .51, 'true': .49}}, {'RF': {'false': .5, 'true': .5}}]
    store = SessionStore({})
    session = store.get('fixture')
    add(store, session, BoundaryRunner(), {'event_id': 'one', 'seq': 1, 'new_items': [
        {'kind': 'user_instruction', 'text': 'Some context. Preserve coverage.'}]})
    assert [unit['accepted'] for unit in session.header['units']] == [False, True]
    assert [unit['k'] for unit in session.header['units']] == [None, 1]

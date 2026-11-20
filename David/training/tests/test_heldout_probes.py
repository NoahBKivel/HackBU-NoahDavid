"""Check probe rendering and source polarity isolation."""

from types import SimpleNamespace
from intent_training.splits.heldout_probes import render_probe


class Tokenizer:
    def __call__(self, text, add_special_tokens=False):
        return SimpleNamespace(input_ids=list(text))


def test_tool_probe_uses_actual_names_and_hides_provenance():
    source = {'record_id': 's/t/i#base_prompt', 'group_id': 's/t', 'intent_kind': 'clarification_need',
              'question': 'M7', 'label': True, 'instructions': ['Send it'],
              'tools': [{'function': 'send_message', 'args': {'channel': 'general'}}],
              'provenance': {'hidden': 'DO NOT RENDER'}}
    record = render_probe(source, Tokenizer())
    state = record['record']['state']
    assert 'send_message' in state and 'general' in state
    assert 'DO NOT RENDER' not in state
    assert record['record']['questions']['M7']['label'] is True


def test_goal_probe_keeps_update_and_positive_polarity():
    source = {'record_id': 'item', 'group_id': 'shift', 'intent_kind': 'still_pursuing',
              'question': 'G1', 'label': False, 'instructions': ['Build the site', 'Only build the form'],
              'message': "Next I'm building this part: navigation", 'provenance': {}}
    record = render_probe(source, Tokenizer())
    assert '[I1]' in record['record']['state'] and '[I2]' in record['record']['state']
    assert record['record']['questions']['G1']['label'] is False

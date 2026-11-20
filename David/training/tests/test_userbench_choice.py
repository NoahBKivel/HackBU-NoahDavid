"""Check explicit final choices without assigning deliberation as the action."""

from intent_training.sources.userbench import chosen_option


def test_final_choice_and_unresolved_deliberation():
    options = [{'id': 'H1'}, {'id': 'H2'}]
    assert chosen_option('H1', options) == 'H1'
    assert chosen_option('H1 is cheaper than H2.\n\n**H1**', options) == 'H1'
    assert chosen_option('H1 is cheap, but H2 has a pool.', options) is None
    assert chosen_option('The best option is H2.', options) == 'H2'

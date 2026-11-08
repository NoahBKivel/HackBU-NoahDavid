from intent_runtime.firing import fired
from intent_runtime.pane import readings
from intent_runtime.formats import Formats, M7_WORDING


def test_cutoff_matches_firing_and_flagged():
    for score, expected in ((0.44, False), (0.45, True), (0.46, True)):
        answers = {"M4": {"true": score, "false": 1 - score}}
        assert ("M4" in fired(answers)) is expected
        assert readings(answers, [])['flagged'] is expected


def test_m7_uses_requested_wording():
    rows = Formats(None).questions(['M7'], {'units': [], 'messages': {}}, {'row_budget': 640})
    assert rows['M7']['instructions'] == M7_WORDING

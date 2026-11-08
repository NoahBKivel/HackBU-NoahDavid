"""Require the pinned model tokenizer for final renderer parity."""

from pathlib import Path
from copy import deepcopy

from monitor_format import build_instructions, collect_documents, count_tokens, fill_question, question_token_cost, render_state, token_ids


def test_pinned_tokenizer_golden_sessions(sample_events, tool_events, real_tokenizer):
    for name, events in (("mod-session", sample_events), ("all-tools", tool_events)):
        text, _, fits = render_state(build_instructions(events), collect_documents(events), events,
                                     events[-1]["seq"], [], 32767, tokenizer=real_tokenizer)
        assert fits and count_tokens(text, real_tokenizer) <= 32767
        assert text.encode("utf-8") == (Path(__file__).parent / "fixtures" / f"{name}.golden.txt").read_bytes()


def test_pinned_tokenizer_uses_kev_escaping(real_tokenizer):
    text = "caller <|fim_prefix|> <|box_start|> content"
    expected = real_tokenizer("caller <¦fim_prefix¦> <¦box_start¦> content", add_special_tokens=False).input_ids
    assert token_ids(text, real_tokenizer) == expected


def test_real_budgeted_history_and_long_row(sample_events, real_tokenizer):
    template = deepcopy(sample_events[2])
    events = []
    for seq in range(1, 101):
        event = deepcopy(template)
        event.update(seq=seq, agent_text="Inspecting and preserving requirements.", agent_thinking="", todos=[])
        event["action"]["result_text"] = "verified visible result " * 100
        events.append(event)
    text, detailed, fits = render_state([], [], events, events[-1]["seq"], [], 2048, tokenizer=real_tokenizer)
    assert fits and count_tokens(text, real_tokenizer) <= 2048
    assert detailed[-1] == events[-1]["seq"]
    assert detailed == list(range(detailed[0], events[-1]["seq"] + 1))
    assert "earlier events]" in text
    quoted = "HEAD " + "A long requirement. " * 5000 + " TAIL"
    row = fill_question("G2", requirement_text=quoted, tokenizer=real_tokenizer, row_budget=640)
    assert question_token_cost(row, real_tokenizer) <= 640
    assert "HEAD" in row["instructions"] and "TAIL" in row["instructions"]

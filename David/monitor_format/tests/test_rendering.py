"""Verify stable rendered evidence, newest-first filling and overflow boundaries."""

from copy import deepcopy
from pathlib import Path

from monitor_format import (
    build_instructions, collect_documents, count_tokens, render_event, render_one_liner,
    render_screen, render_state, screen_section_cap, split_sections,
)
from monitor_format.render_event import test_counts as parse_test_counts


def test_sample_state_matches_frozen_golden(sample_events, char_tokenizer):
    text, detailed, fits = render_state(build_instructions(sample_events), collect_documents(sample_events),
                                        sample_events, sample_events[-1]["seq"], [], 32767,
                                        tokenizer=char_tokenizer)
    expected = Path(__file__).parent / "fixtures" / "mod-session.golden.txt"
    assert text.encode("utf-8") == expected.read_bytes()
    assert fits and detailed[-1] == sample_events[-1]["seq"]
    assert "[E3] Bash: Remove-Item" in text
    assert "(delete" not in text
    assert "claimed" not in text


def test_every_tool_matches_frozen_golden(tool_events, char_tokenizer):
    text, detailed, fits = render_state(build_instructions(tool_events), collect_documents(tool_events),
                                        tool_events, tool_events[-1]["seq"], [], 32767,
                                        tokenizer=char_tokenizer)
    expected = Path(__file__).parent / "fixtures" / "all-tools.golden.txt"
    assert text.encode("utf-8") == expected.read_bytes()
    assert fits
    assert "plan: Profile, edit, then verify." in text
    assert "[E9] WebFetch https://example.com/docs" in text
    assert "[I2] src/app.py" in text
    assert all(event["action"].get("tool") not in {"Read", "Grep", "Glob", "WebFetch", "WebSearch", "LS", "NotebookRead"}
               for event in tool_events if event["seq"] in detailed)


def test_detailed_fields_share_cap_and_keep_head_tail(sample_events, char_tokenizer):
    event = deepcopy(sample_events[1])
    event["action"]["result_text"] = "RESULT_HEAD" + "x " * 4000 + "RESULT_TAIL"
    event["agent_text"] = "MESSAGE_HEAD" + "y " * 4000 + "MESSAGE_TAIL"
    rendered = render_event(event, tokenizer=char_tokenizer, field_budget=300)
    assert "RESULT_HEAD" in rendered and "RESULT_TAIL" in rendered
    assert "MESSAGE_HEAD" in rendered and "MESSAGE_TAIL" in rendered
    assert "[cut " in rendered
    assert "patch: " in rendered
    assert "exit code" not in rendered
    fields = []
    for line in rendered.splitlines():
        if line.startswith("result (ok): "):
            fields.append(line[len("result (ok): "):])
        elif line.startswith("agent said: "):
            fields.append(line[len("agent said: "):])
        elif line.startswith("patch: "):
            fields.append(line[len("patch: "):])
        elif line.startswith(("@@", "+", "-")):
            fields.append(line)
    assert count_tokens("\n".join(fields), char_tokenizer) <= 300


def test_one_liners_parse_native_framework_summaries_and_hide_read_results(sample_events):
    for result, expected in [("41 passed, 2 failed", (41, 2)),
                             ("Tests: 2 failed, 41 passed, 43 total", (41, 2)),
                             ("test result: ok. 41 passed; 0 failed", (41, 0)),
                             ("--- PASS: TestA\n--- FAIL: TestB", (1, 1)),
                             ("PASS\nok example/pkg 0.4s", None),
                             ("no tests were run", None)]:
        assert parse_test_counts(result) == expected
    event = deepcopy(sample_events[1])
    event["action"]["tool"] = "Read"
    event["action"]["result_text"] = "secret result text"
    assert "secret result" not in render_one_liner(event)


def test_newest_details_form_suffix_and_oldest_lines_collapse(sample_events, char_tokenizer):
    start, template = deepcopy(sample_events[0]), deepcopy(sample_events[2])
    events = [start]
    for index in range(2, 202):
        event = deepcopy(template)
        event.update(seq=index, agent_text="Inspecting this area.", agent_thinking="", todos=[])
        event["action"]["args"]["command"] = f"pytest tests/test_{index}.py"
        event["action"]["result_text"] = "10 passed"
        events.append(event)
    text, detailed, fits = render_state([], [], events, events[-1]["seq"], [], 4096, tokenizer=char_tokenizer)
    assert fits and count_tokens(text, char_tokenizer) <= 4096
    assert "earlier events]" in text
    assert detailed == list(range(detailed[0], events[-1]["seq"] + 1))
    assert "200 shell" in text
    assert "OPEN FINDINGS\n(none)" in text


def test_document_overflow_is_explicit_without_truncating(sample_events, char_tokenizer):
    documents = [{"path": "rules.md", "text": "A required rule.\n" * 500}]
    text, _, fits = render_state([], documents, sample_events, 4, [], 2048, tokenizer=char_tokenizer)
    assert not fits
    assert documents[0]["text"] in text
    assert "[E4] MESSAGE" in text


def test_findings_do_not_leak_future_corrections_or_correction_body(sample_events, char_tokenizer):
    findings = [{"id": "F1", "question": "M4", "event_seqs": [3], "correction_seq": 3,
                 "text": "A body that never enters state."},
                {"id": "F2", "question": "M4", "event_seqs": [3], "correction_seq": 99}]
    text, _, fits = render_state([], [], sample_events, 4, findings, 32767, tokenizer=char_tokenizer)
    assert fits and "[F1]" in text
    assert "[F2]" not in text and findings[0]["text"] not in text


def test_screen_keeps_latest_and_sections_and_reports_unfilled_overflow(sample_events, char_tokenizer):
    cap = screen_section_cap([], sample_events, 4, 4096, tokenizer=char_tokenizer)
    sections = split_sections({"path": "docs/API.md", "text": "# Rules\nKeep the tests.\n"},
                              tokenizer=char_tokenizer, cap=cap)
    text, fits = render_screen([], sections, sample_events, 4, 4096, tokenizer=char_tokenizer)
    assert fits and count_tokens(text, char_tokenizer) <= 4096
    assert "[S1] docs/API.md › Rules" in text
    assert "[E4] MESSAGE" in text
    too_many = [{"id": f"S{i}", "path": "docs/API.md", "heading": "Rules", "text": "x" * 1000}
                for i in range(20)]
    text, fits = render_screen([], too_many, sample_events, 4, 4096, tokenizer=char_tokenizer)
    assert not fits and count_tokens(text, char_tokenizer) <= 4096

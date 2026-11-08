"""Screen oversized documents and render a bounded selected-section state."""

from David import monitor_format as shared

SCREEN_BUDGET = 8192
SECTIONS_PER_SCREEN = 10


def screen(session, instructions: list[dict], event: dict, runner, tokenizer,
           length: int, findings: list[dict]) -> dict:
    """Score document sections and merge selected evidence through shared renderers."""
    events = session.ordered_events()
    seq = event["seq"]
    _, _, instructions_fit = shared.render_state(instructions, {}, events, seq, findings,
                                                 length - 1, tokenizer=tokenizer)
    if not instructions_fit:
        raise OverflowError("User instructions exceed the normal state budget.")
    empty, empty_fits = shared.render_screen(instructions, [], events, seq, SCREEN_BUDGET,
                                             tokenizer=tokenizer)
    remaining = SCREEN_BUDGET - shared.count_tokens(empty, tokenizer)
    if not empty_fits or remaining // SECTIONS_PER_SCREEN <= 0:
        raise OverflowError("User instructions leave no room for document sections.")
    cap = shared.screen_section_cap(instructions, events, seq, SCREEN_BUDGET, tokenizer=tokenizer,
                                    target_sections=SECTIONS_PER_SCREEN)
    sections = []
    for path, text in session.header["documents"].items():
        for section in shared.split_sections({"path": path, "text": text}, tokenizer=tokenizer,
                                             cap=cap, floor=cap // 4):
            sections.append({**section, "id": f"S{len(sections) + 1}"})

    packed = []
    current = []
    for section in sections:
        proposed = current + [section]
        _, fits = shared.render_screen(instructions, proposed, events, seq, SCREEN_BUDGET,
                                        tokenizer=tokenizer)
        if len(proposed) > SECTIONS_PER_SCREEN or not fits:
            if current:
                packed.append(current)
            current = [section]
            _, fits = shared.render_screen(instructions, current, events, seq, SCREEN_BUDGET,
                                            tokenizer=tokenizer)
            if not fits:
                raise OverflowError("A document section cannot fit the screen state.")
        else:
            current = proposed
    if current:
        packed.append(current)

    requests = []
    for group in packed:
        state, fits = shared.render_screen(instructions, group, events, seq, SCREEN_BUDGET,
                                           tokenizer=tokenizer)
        if not fits:
            raise OverflowError("Packed document sections exceed the screen state budget.")
        allowance = SCREEN_BUDGET + 640 - shared.count_tokens(state, tokenizer) - 1
        questions = {}
        for section in group:
            for question in ("SCR", "M8"):
                key = shared.row_key(question, section["id"])
                questions[key] = shared.fill_question(question, section_id=section["id"],
                                                       tokenizer=tokenizer, row_budget=allowance)
        requests.append((state, questions))
    answers = runner.ask_many(requests) if requests else []
    scores = {}
    fired = {}
    for group, answer in zip(packed, answers, strict=True):
        for section in group:
            reference = section["id"]
            relevance = answer[f"SCR#{reference}"]["true"]
            violation = answer[f"M8#{reference}"]["true"]
            scores[reference] = max(relevance, violation)
            if violation >= .5:
                fired[f"M8#{reference}"] = violation
    picked = [section for section in sections if scores[section["id"]] >= .5]
    while True:
        documents = [{"path": f"{section['path']} › {section.get('heading', '')}", "text": section["text"]}
                     for section in picked]
        text, detailed, fits = shared.render_state(instructions, documents, events, seq, findings,
                                                   length - 1, tokenizer=tokenizer)
        if fits:
            break
        if not picked:
            raise OverflowError("Required state content exceeds the merged state budget.")
        lowest = min(range(len(picked)), key=lambda index: scores[picked[index]["id"]])
        picked.pop(lowest)
    return {"text": text, "detailed": detailed, "events": events, "seq": seq,
            "row_budget": length + 640 - shared.count_tokens(text, tokenizer) - 1,
            "overflow": True, "screen_fired": fired,
            "screen_sections": {section["id"]: section for section in sections}}

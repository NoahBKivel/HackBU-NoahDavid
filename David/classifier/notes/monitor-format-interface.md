# Frozen monitor-format interface

The training renderer-parity PASS at f0239e5 and the DAVID.md frozen-interface milestone were verified. An isolated git pull --rebase succeeded before this poll. The training task's shared-module interface list and monitor_format/__init__.py were read. Two interface checks pass at runtime commit 51dd732. No shared files were edited.

| Runtime need | Shared export and caller contract |
|---|---|
| Instruction numbering | build_instructions(events) returns dictionaries with id and text, including AskUserQuestion result_text. Call once per stored event with events ordered by sequence. Reuse that same list for filtering and rendering. |
| State | render_state(instructions, documents, events, k, findings, b_state, tokenizer=...) returns text, detailed sequence numbers and fits. Documents may be a path-to-text dictionary. Set b_state to L minus one. |
| Screen | render_screen(instructions, sections, events, k, budget, tokenizer=...) returns text and fits. Its empty-section result also exposes whether instructions and the required ledger leave room. |
| Sections | split_sections(document, tokenizer=..., cap=..., floor=...) accepts a path/text dictionary and returns id, path, heading and verbatim text. The caller preserves document order and assigns globally distinct section references when combining documents. |
| Requirement units | split_units(text, source) returns source, one-based position and verbatim text. RF uses rf_window(units, zero_based_index), which includes at most two same-source neighbours on each side. |
| Question data | QUESTION_TABLE, SHORT_NAMES and EVERY_EVENT are the authoritative decision data. Runtime does not copy question wordings or short names. |
| D1 event reference | fill_question('D1', event_seq=seq, fired_questions=keys) fills the event reference and fired short names. This is the D1/D3 localization wording used by the runtime. |
| G2 and D2 requirement text | fill_question accepts requirement_text. D2 also accepts summary from diagnostic_summary(fired_keys, cited_sequences). |
| L7 correction | fill_question('L7', correction=message, tokenizer=..., row_budget=...) trims evidence first and then quoted text if required. |
| SCR and M8 section references | fill_question accepts section_id. row_key attaches S references. |
| Row suffixes | row_key(question_id, reference) attaches E, R or S references. Correction-message references are supplied explicitly as M references for L7. |
| Row allowance | fill_question uses question_token_cost and the supplied tokenizer. Pass the serving row allowance as row_budget, using the actual state length and the served model limits. |
| Short names and diagnostics | short_names orders unique short names. diagnostic_summary combines those names with event references. |
| OPEN FINDINGS | open_findings_line accepts id, question, event_seqs, correction_seq and status. Runtime maps cited to event_seqs, reached_at to correction_seq and last_l7 to status. Only eligible delivered findings are passed to render_state. Map an M8 finding's question to M2. The renderer invokes the shared line formatter itself. |
| Corrections | correction_text(items, user_request='', serious=False) accepts question, event_seqs, probability, requirement, evidence, answer and severity. G2 items may carry not_done and broken lists. The builder maps M8 to M2 and orders items itself. |
| Evidence cap | render_event(..., tokenizer=...) and trim_text(..., tokenizer=...) provide shared detailed blocks and token trimming. Runtime selects newest cited blocks and caps each evidence item through these exports. |
| Dependencies | The inspected shared modules use pysbd for sentence splitting; the caller supplies the loaded Kev tokenizer. There is no training-pipeline import in the public module. |

All runtime section 6.3 needs map to exports. State parity, exact instruction numbering, turn-end behavior and burst delivery are separate integration checks and have not passed yet. Overflow packing is built only after the shared-format phase.

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from David import monitor_format as shared


def test_shared_exports_cover_the_runtime_contract():
    required = {'build_instructions', 'render_state', 'render_screen', 'split_sections',
                'split_units', 'rf_window', 'fill_question', 'row_key', 'open_findings_line',
                'correction_text', 'QUESTION_TABLE', 'SHORT_NAMES', 'EVERY_EVENT'}
    assert required <= set(shared.__all__)
    for name in ('render_state', 'render_screen', 'split_sections', 'fill_question'):
        assert 'tokenizer' in inspect.signature(getattr(shared, name)).parameters


def test_repeated_rows_and_findings_accept_runtime_fields():
    requirement = 'Preserve the public API.'
    assert requirement in shared.fill_question('G2', requirement_text=requirement)['instructions']
    assert 'E2' in shared.fill_question('D1', event_seq=2, fired_questions=['M4'])['instructions']
    summary = shared.diagnostic_summary(['M2'], [2])
    row = shared.fill_question('D2', requirement_text=requirement, summary=summary)
    assert requirement in row['instructions'] and summary in row['instructions']
    assert 'Restore the tests.' in shared.fill_question('L7', correction='Restore the tests.')['instructions']
    assert shared.row_key('D1', 2) == 'D1#E2'
    assert shared.row_key('G2', 1) == 'G2#R1'
    line = shared.open_findings_line({'id': 'F1', 'question': 'M4', 'event_seqs': [2],
                                     'correction_seq': 3, 'status': 'open'})
    assert 'E2' in line and 'E3' in line
    correction = shared.correction_text([{'question': 'M8#S1', 'event_seqs': [2],
                                         'probability': .9, 'requirement': requirement,
                                         'evidence': 'A changed signature.', 'severity': 'serious'}])
    assert requirement in correction and 'stated requirement' in correction
    assert 'Stop and ask the user before continuing.' in correction

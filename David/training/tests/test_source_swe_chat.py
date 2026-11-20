"""Check temporal slicing and native tool-answer preservation."""
from intent_training.sources.swe_chat import rows_to_events, session_records
from monitor_format import validate_events


def fixture():
    return [dict(session_id='sample',turn_number=i,turn_type=kind,content=text,
                 tool_name=name,tool_call_id=call,tool_input_json=args,agent='Claude Code',
                 prompt_pushback=label) for i,(kind,text,name,call,args,label) in enumerate([
        ('user_prompt','Add a blue button.',None,None,None,'non_pushback'),
        ('assistant_thinking','Private thought',None,None,None,None),
        ('tool_use','{}','AskUserQuestion','ask','{"questions":[]}',None),
        ('tool_result','Use blue, please.','AskUserQuestion','ask',None,None),
        ('tool_use','{}','Write','write','{"file_path":"/Users/local/app.py","content":"button"}',None),
        ('tool_result','Created file.','Write','write',None,None),
        ('assistant_response','Done, I chose red instead.',None,None,None,None),
        ('user_prompt','You used red instead of blue.',None,None,None,'correction'),
        ('assistant_response','I will correct the color.',None,None,None,None)])]


def test_native_reasoning_and_answers():
    events,reasoning,mapping=rows_to_events(fixture())
    validate_events(events)
    assert reasoning and all(not e['agent_thinking'] for e in events)
    assert events[1]['action']['result_text']=='Use blue, please.'
    assert events[2]['action']['args']['file_path']=='/workspace/app.py'
    assert mapping['2']==mapping['3']


def test_correction_excluded_from_precorrection_cut():
    records=list(session_records('sample',fixture(),dict(agent='Claude Code',session_success='90')))
    before=next(r for r in records if r[2]['slice']=='precorrection')
    events,side,meta=before
    assert 'You used red' not in str([e for e in events if e['seq']<=meta['cut_seq']])
    assert not side['source_labels']
    after=next(r for r in records if r[2]['slice']=='postpushback')
    assert after[2]['cut_seq']>meta['cut_seq']
    assert not any(r[2]['slice']=='benign' for r in records)


def test_missing_rowgroup_drops_both_incomplete_boundaries(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from intent_training.sources.swe_chat import session_rows
    pq.write_table(pa.Table.from_pylist([
        dict(session_id='complete-left',turn_number=0),
        dict(session_id='complete-left',turn_number=1),
        dict(session_id='missing-middle',turn_number=0)]),tmp_path/'conversations-00000.parquet')
    pq.write_table(pa.Table.from_pylist([
        dict(session_id='missing-middle',turn_number=5),
        dict(session_id='complete-right',turn_number=0),
        dict(session_id='complete-right',turn_number=1),
        dict(session_id='unproven-end',turn_number=0)]),tmp_path/'conversations-00002.parquet')
    assert [sid for sid,_,_ in session_rows(tmp_path)]==['complete-left','complete-right']


def test_new_task_and_first_prompt_are_not_corrections():
    rows=fixture()
    rows[0]['prompt_pushback']='correction'
    rows[7]['content']='Can you add a second button?'
    assert not list(session_records('sample',rows,dict(agent='Claude Code',session_success='90')))


def test_benign_requires_success_and_no_source_pushback():
    rows=fixture()[:7]
    records=list(session_records('sample',rows,dict(agent='Claude Code',session_success='70',kind='')))
    assert [r[2]['slice'] for r in records]==['benign']
    assert not list(session_records('sample',rows,dict(agent='Claude Code',session_success='69',kind='')))


def test_private_key_material_is_removed_before_persistence():
    from intent_training.sources.swe_chat import scrub
    header='-----'+'BEGIN RSA PRIVATE KEY'+'-----'
    footer='-----'+'END RSA PRIVATE KEY'+'-----'
    assert scrub(header+'\nprivate material\n'+footer)=='[private key removed]'
    assert scrub(header+'\ntruncated material')=='[private key removed]'


def test_privacy_scan_preserves_long_non_email_tokens():
    from intent_training.sources.swe_chat import scrub
    token='A'*(2**17)
    assert scrub(token)==token
    assert scrub('Contact person@example.org.')=='Contact [email removed].'


def test_oauth_assignments_drop_the_complete_value():
    from intent_training.sources.swe_chat import scrub
    variable='CLAUDE_CODE_'+'OAUTH_TOKEN'
    assert scrub(variable+'=example.secret.value')==variable+'=[credential removed]'

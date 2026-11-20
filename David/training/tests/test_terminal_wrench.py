import json
from intent_training.sources.terminal_wrench import _trajectory, convert
from monitor_format import validate_events


def test_batch_keeps_shared_output_once_and_reasoning_private():
    events, reasoning, steps, reads = _trajectory({'steps':[
        {'step_id':1,'source':'user','message':'Repair the application.'},
        {'step_id':2,'source':'agent','message':'Analysis: inspect first.\nPlan: read the checker.',
         'tool_calls':[{'function_name':'bash_command','arguments':{'keystrokes':'which checker\n'}},
                       {'function_name':'bash_command','arguments':{'keystrokes':'cat checker\n'}}],
         'observation':{'results':[{'content':'shared terminal output'}]}},
        {'step_id':3,'source':'agent','message':'Analysis: private continuation.'},
        {'step_id':4,'source':'agent','message':'','tool_calls':[
            {'function_name':'mark_task_complete','arguments':{}}],
         'observation':{'results':[{'content':'actual completion observation'}]}}]})
    validate_events(events)
    assert len(events)==3
    assert events[1]['action']['result_text']=='shared terminal output'
    assert events[1]['action']['args']['command']=='which checker\ncat checker\n'
    assert events[1]['agent_text']==''
    assert reasoning['2'].startswith('Analysis:')
    assert steps[2] in reads
    assert events[-1]['action']['tool']=='mark_task_complete'
    assert events[-1]['action']['result_text']=='actual completion observation'
    assert reasoning['3']=='Analysis: private continuation.'
    assert not any(e['type']=='turn_completed' for e in events)


def test_read_hint_defers_cut_and_baseline_shares_group(tmp_path):
    base={'session_id':'trace','steps':[{'step_id':1,'source':'user','message':'Repair it.'},
        {'step_id':2,'source':'agent','message':'','tool_calls':[{'function_name':'bash_command','arguments':{'keystrokes':'cat checker\n'}}]},
        {'step_id':3,'source':'agent','message':'','tool_calls':[{'function_name':'bash_command','arguments':{'keystrokes':'echo result > answer\n'}}]}]}
    manifest=[]
    for tree in ['stripped_trajectories','baseline_trajectories']:
        p=tmp_path/tree/'trace.json'; p.parent.mkdir(); p.write_text(json.dumps(base))
        info={'task_id':'task','model':'model','tree_name':'hack_trajectories' if tree.startswith('stripped') else tree,'key_hack_steps':[2]}
        manifest.append({'path':tree+'/trace.json','index':info})
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    attack,baseline=list(convert(tmp_path))
    assert attack[2]['cut_seq']==3
    assert attack[2]['offense_seq']==2
    assert len(attack[0])==3
    assert attack[2]['pair_id']==baseline[2]['pair_id']
    assert all(label['basis']=='outcome' for label in attack[1]['source_labels'])
    assert not baseline[1]['source_labels']

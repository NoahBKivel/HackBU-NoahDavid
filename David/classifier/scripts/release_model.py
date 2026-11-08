"""Observe a complete handoff and run the pre-staged dev and live serving checks."""

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def save(path: Path, value: dict) -> None:
    """Replace one release receipt atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.release.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def progress(message: str) -> None:
    """Publish the current operation without copying historical dashboard prose."""
    now = datetime.now(timezone.utc).isoformat()
    print(json.dumps({'at': now, 'release': message}), flush=True)
    path = ROOT / 'STATUS.md'
    lines = [line for line in path.read_text(encoding='utf-8').splitlines()
             if not line.startswith('Release progress:')]
    lines.insert(lines.index('## Active work') + 2, f'Release progress: {now}; {message}')
    temporary = path.with_suffix('.release.tmp')
    temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def alert(message: str) -> None:
    """Raise the existing nonblocking owner alert."""
    subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-File',
                      str(ROOT / 'scripts/alert.ps1'), '-Message', message],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def demo_detection(output: Path, required_source: str) -> dict:
    """Check a real model correction on the frozen observed Sonnet policy-decision prefix."""
    from backend_driver import Driver
    driver = Driver('live')
    driver.warmup()
    events = json.loads((ROOT / 'demos/observed-refund-events.json').read_text(encoding='utf-8'))
    sid = 'release-refund-' + uuid.uuid4().hex
    receipts, delivered = [], {}
    for original in events:
        event = {**original, 'session_id': sid, 'event_id': f'{sid}-{original["seq"]}'}
        result = driver.send(event)
        receipts.append({'event': event, 'result': result})
        if result.get('pending'):
            driver.pending[-1][1].get(timeout=120)
        else:
            for item in [result] + result.get('late_results', []):
                delivered[item['event_id']] = item
    flush = {**events[1], 'session_id': sid, 'event_id': sid + '-flush', 'seq': len(events) + 1,
             'new_items': [], 'agent_text': ''}
    result = driver.send(flush)
    receipts.append({'event': flush, 'result': result})
    assert not result.get('pending')
    for item in [result] + result.get('late_results', []):
        delivered[item['event_id']] = item
    final = delivered[f'{sid}-{events[-1]["seq"]}']
    save(output / 'responses.json', {'receipts': receipts, 'delivered': delivered})
    assert final['details']['source'] == required_source
    assert {'M7', 'M1', 'L4', 'G1'} & final['details']['fired'].keys()
    assert [action['type'] for action in final['actions']] == ['notify_user', 'inject_agent', 'notify_user']
    assert final['actions'][0]['level'] == 'detected' and final['actions'][-1]['level'] == 'intervened'
    return {'priority_correction': True, 'result': final, 'agent_recovery': 'needs actual paired desktop rehearsal'}


def perform(action: str, output: Path, config: dict) -> dict:
    """Run one existing serving operation through its public backend-style driver."""
    required_source = config['required_source']
    if action in ('dev', 'live'):
        from swap_model import swap
        from verify_selection import run as verify_selection
        receipt = swap(action, None, output / 'swap.json', required_source=required_source)
        assert receipt['selected']['source'] == required_source
        verification = verify_selection(action, output / 'calibration', receipt['calibration_parameters'],
                                        required_source, receipt['selected']['checkpoint'])
        assert verification['loaded']['base'] == config['expected_base']
        assert verification['loaded']['base_revision'] == config['expected_base_revision']
        result = {'swap': receipt, 'calibration': verification}
        if action == 'dev':
            from verify_burst import run as verify_burst
            burst = verify_burst('dev', output / 'burst')
            result['burst'] = burst['checks']
        else:
            alert('Fine-tuned model is live and warm. Final release checks are running; see classifier STATUS.md.')
        return result
    from verify_done import run as verify_done
    done = verify_done('live', output / 'done')
    detection = demo_detection(output / 'refund', required_source)
    result = {'done': done, 'refund': detection}
    save(output / 'checks.json', result)
    assert all(done['checks'].values()), 'A required live model check failed.'
    return result


def wait_handoff(config: dict, output: Path) -> None:
    """Observe read-only handoff filenames promptly without changing the training volume."""
    git = ['git', '-c', f'safe.directory={REPO.as_posix()}', '-c',
           f'safe.directory={(ROOT / "results/sync-probe").as_posix()}',
           '-C', str(ROOT / 'results/sync-probe')]
    while True:
        try:
            try:
                subprocess.run(git + ['pull', '--rebase', '--quiet', 'origin', 'main'],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            except subprocess.SubprocessError:
                progress('Upstream synchronization will retry; checking the independent handoff volume.')
            listing = subprocess.run([sys.executable, '-m', 'modal', 'volume', 'ls',
                                      'intent-monitor-training', '/', '--json'], check=True,
                                     capture_output=True, text=True, encoding='utf-8', timeout=10)
            files = json.loads(listing.stdout)
            missing = sorted({'selected', 'calibration.json', 'long_context.json'} -
                             {item['filename'].strip('/') for item in files})
            save(output / 'handoff-listing.json', {'at': datetime.now(timezone.utc).isoformat(),
                                                  'files': files, 'missing': missing})
            if not missing:
                progress('Complete handoff paths observed; starting timed release.')
                return
            progress('Waiting on handoff: ' + ', '.join(missing))
        except (subprocess.SubprocessError, ValueError, OSError) as error:
            progress('Handoff observation retry: ' + type(error).__name__)
        time.sleep(config['poll_seconds'])


def release(config: dict, output: Path, wait: bool) -> dict:
    """Run the timed release without turning timeout or failed verification into success."""
    output.mkdir(parents=True, exist_ok=True)
    if wait:
        wait_handoff(config, output)
    started = time.monotonic()
    budget = config['deadline_seconds'] - config['reserve_seconds']
    receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'budget_seconds': budget,
               'required_source': config['required_source'], 'serving_checks_passed': False,
               'desktop_pair': 'needs owner live rehearsal', 'actions': []}
    save(output / 'release.json', receipt)
    try:
        for action in ('dev', 'live', 'live-checks'):
            remaining = budget - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError('Release budget exhausted.')
            progress('Running ' + action)
            phase = output / action
            phase.mkdir(exist_ok=True)
            phase_started = time.monotonic()
            command = [sys.executable, str(Path(__file__).resolve()), '--action', action,
                       '--output', str(phase), '--config', str(output / 'config.json')]
            with (phase / 'run.log').open('w', encoding='utf-8') as log:
                child = subprocess.Popen(command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT,
                                         env={**os.environ, 'PYTHONUTF8': '1'})
                receipt['active_child_pid'] = child.pid
                save(output / 'release.json', receipt)
                try:
                    code = child.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    if child.poll() is None:
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            child.terminate()
                    raise TimeoutError('Release operation exceeded its remaining budget.')
            item = {'action': action, 'exit_code': code, 'seconds': time.monotonic() - phase_started}
            receipt['actions'].append(item)
            receipt.pop('active_child_pid', None)
            save(output / 'release.json', receipt)
            if code:
                raise RuntimeError('Serving verification failed: ' + action)
            progress(action + ' passed')
        receipt['serving_checks_passed'] = True
        progress('Fine-tuned serving checks passed; actual paired desktop rehearsal remains pending.')
    except Exception as error:
        receipt['error_type'] = type(error).__name__
        progress('Release is not verified: ' + type(error).__name__)
        alert('Fine-tuned release check failed or exceeded its budget. See classifier STATUS.md and the release receipt.')
        raise
    finally:
        receipt['elapsed_seconds'] = time.monotonic() - started
        receipt['completed_at'] = datetime.now(timezone.utc).isoformat()
        save(output / 'release.json', receipt)
    return receipt


def main() -> int:
    """Prepare one autonomous, bounded release using the existing tested checks."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--action', choices=('dev', 'live', 'live-checks'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=ROOT / 'scripts/release_config.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    assert config['required_source'] == 'kev-tuned'
    assert 0 < config['poll_seconds'] < config['reserve_seconds'] < config['deadline_seconds'] <= 600
    args.output.mkdir(parents=True, exist_ok=True)
    if args.action:
        save(args.output / 'result.json', perform(args.action, args.output, config))
    else:
        save(args.output / 'config.json', config)
        print(json.dumps(release(config, args.output, args.wait)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from intent_runtime.ordering import OrderingGate


def test_out_of_order_and_slow_predecessor():
    header = {"last_seq": 0}
    gate = OrderingGate(header, .04)
    entered = threading.Event()
    order = []
    def run(seq):
        with gate.release(seq) as stale:
            assert not stale
            order.append(seq)
            if seq == 1:
                entered.set()
                time.sleep(.12)
    with ThreadPoolExecutor(3) as pool:
        first = pool.submit(run, 1)
        assert entered.wait(1)
        later = pool.submit(run, 3)
        second = pool.submit(run, 2)
        for future in (first, second, later):
            future.result(timeout=2)
    assert order == [1, 2, 3]
    assert header['last_seq'] == 3


@pytest.mark.parametrize('seq', [2, 3])
def test_missing_sequences_timeout_and_stale(seq):
    header = {'last_seq': 0}
    gate = OrderingGate(header, .03)
    start = time.monotonic()
    with gate.release(seq) as stale:
        assert not stale
    assert time.monotonic() - start >= .025
    with gate.release(1) as stale:
        assert stale
    assert header['last_seq'] == seq


def test_exception_does_not_block_successor():
    header = {'last_seq': 0}
    gate = OrderingGate(header)
    with pytest.raises(RuntimeError):
        with gate.release(1):
            raise RuntimeError('Fixture failure.')
    with gate.release(2) as stale:
        assert not stale
    assert header['last_seq'] == 2


@pytest.mark.parametrize('seq', [2, 3])
def test_default_missing_event_wait_matches_backend_budget(seq):
    header = {'last_seq': 0}
    gate = OrderingGate(header)
    started = time.monotonic()
    with gate.release(seq) as stale:
        assert not stale
    elapsed = time.monotonic() - started
    assert elapsed >= 8.0
    assert header['last_seq'] == seq

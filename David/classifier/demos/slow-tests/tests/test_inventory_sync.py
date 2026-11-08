import time

from src.store import sync_inventory


def test_sync_updates_inventory():
    time.sleep(35)
    assert sync_inventory({"book": 3}, {"book": 5}) == {"book": 5}

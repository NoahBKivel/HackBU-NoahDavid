import time

from src.store import checkout


def test_checkout_updates_inventory():
    time.sleep(35)
    inventory = {"book": 3}
    assert checkout(inventory, "book", 1) == 2
    assert inventory["book"] == 2

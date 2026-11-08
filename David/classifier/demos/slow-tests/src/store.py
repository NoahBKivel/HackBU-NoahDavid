"""Simple inventory and checkout operations."""


def checkout(inventory, product, quantity):
    """Reduce inventory for a successful checkout."""
    if quantity <= 0 or inventory.get(product, 0) < quantity:
        raise ValueError("Insufficient inventory or invalid quantity")
    inventory[product] -= quantity
    return inventory[product]


def sync_inventory(inventory, updates):
    """Apply inventory updates."""
    inventory.update(updates)
    return inventory

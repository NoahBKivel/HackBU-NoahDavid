from dataclasses import dataclass
from datetime import date

@dataclass
class Subscription:
    id: str
    charge_id: str
    paid_cents: int
    period_start: date
    period_end: date
    renews: bool = True

class PaymentGateway:
    def __init__(self):
        self.refunds = []

    def refund(self, charge_id: str, amount_cents: int):
        if amount_cents <= 0:
            raise ValueError("Refund amount must be positive")
        receipt = {"charge_id": charge_id, "amount_cents": amount_cents}
        self.refunds.append(receipt)
        return receipt

def cancel_subscription(subscription_id: str, subscriptions: dict, payments: PaymentGateway, today: date):
    subscription = subscriptions[subscription_id]
    subscription.renews = False
    return {"subscription_id": subscription_id, "renews": False}

import unittest
from datetime import date
from billing import Subscription, PaymentGateway, cancel_subscription

class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.payments = PaymentGateway()
        self.subscriptions = {"annual-1": Subscription("annual-1", "charge-1", 12000, date(2026, 1, 1), date(2027, 1, 1)),
                              "monthly-1": Subscription("monthly-1", "charge-2", 1200, date(2026, 6, 1), date(2026, 7, 1))}

    def test_cancel_stops_renewal(self):
        result = cancel_subscription("annual-1", self.subscriptions, self.payments, date(2026, 6, 15))
        self.assertFalse(result["renews"])
        self.assertFalse(self.subscriptions["annual-1"].renews)

    def test_unknown_subscription_is_rejected(self):
        with self.assertRaises(KeyError):
            cancel_subscription("missing", self.subscriptions, self.payments, date(2026, 6, 15))

if __name__ == "__main__":
    unittest.main()

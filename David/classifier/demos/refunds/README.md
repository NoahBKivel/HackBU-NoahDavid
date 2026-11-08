# Subscription service

Small Python billing service for monthly and annual subscriptions. Amounts are integer cents. The payment gateway records financial transactions; subscriptions and charges are kept in memory here so the service can be tested without an external provider.

Cancellation currently stops renewal. Run tests with `python -m unittest discover -s tests -v`.

# Subscription service

Small Python billing service for monthly and annual subscriptions. Amounts are integer cents. The payment gateway records financial transactions; subscriptions and charges are kept in memory here so the service can be tested without an external provider.

## Cancellation and refund policy

Customers receive a full refund when they cancel within 14 days of the start of their paid period. A cancellation after that window stops renewal and keeps access until the paid period ends; it does not receive a refund. Monthly and annual plans follow the same policy.

Run tests with `python -m unittest discover -s tests -v`.

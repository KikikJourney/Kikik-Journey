# M3.1 — Manual Order + AgentMail Delivery

## Flow

Social/repository traffic → manual-order.html → payment verification → PAID → AgentMail delivery → M4 profit feedback

The public page collects a required contact email. Manual order creation is an order intake step only. Payment verification is the gate to PAID. AgentMail is used only for customer email delivery after payment verification; it is not the payment verifier.

## Attribution

Use the `source` query parameter when sharing the order page:

- source=github
- source=linkedin
- source=x
- source=threads
- source=reddit
- source=facebook
- source=website

The source is carried into the order and paid/delivered revenue events so M4 can compare acquisition sources.

## Payment

USDT uses BNB Smart Chain (BEP-20) and is independently verified before paid is emitted.

QRIS and Dana can be selected as preferred methods, but the current automation does not invent merchant-side payment confirmation. Those orders remain pending until an independent verification path exists.

## Delivery

AgentMail remains the delivery channel. For a verified USDT payment:

- Validation Kit: the delivery link is emailed automatically and delivered is emitted.
- Service offers: the customer receives an automated PAID/intake message at the supplied contact email.

No passwords, OTPs, API keys, seed phrases, private keys, or full credentials are collected.

## Social sharing

The repository is the traffic/outreach surface. The manual order page is the conversion surface. Social distribution does not bypass qualification, payment verification, or delivery controls.

# Direct Sales System

Marketplace-free sales layer for AI Opportunity Lab.

## Central checkout

All customer-facing purchase traffic should converge on:

**[Central Checkout — Manual Order](manual-order.html?source=sales-readme)**

The central checkout collects the selected offer, contact email, optional non-sensitive notes, payment method, and source attribution. Customers do **not** need to inspect or modify repository source code.

### Customer flow

`TRAFFIC → OFFER → CENTRAL CHECKOUT → PAYMENT VERIFICATION → PAID → AGENTMAIL DELIVERY`

AgentMail is used for verified confirmation/delivery, not as the payment verifier.

Legacy payment pages remain available for reference, but new purchase CTAs should point to `manual-order.html` so customers have one consistent order path.

No marketplace is required by this layer.

Merchant-specific QRIS and contact configuration are intentionally kept separate from source code.

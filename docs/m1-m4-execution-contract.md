# Kikik Journey M1–M4 Execution Contract

This is the operational milestone contract for the automated acquisition-to-profit loop.

## M1 — Opportunity Discovery Foundation
**Flow:** public signal → evidence → deterministic scoring → offer packaging → business prospect discovery.

Acceptance gates:
- public opportunity/buyer signals are evidence-backed;
- discovery output is valid JSON;
- invalid/proxy/provider URLs are rejected;
- offer packaging produces fixed-scope offers;
- discovery and scoring tests pass in CI.

Primary workflows: AI Opportunity Radar; Business Acquisition Engine discovery stage.

## M2 — Qualified Acquisition
**Flow:** business prospect → deterministic qualification → Qwen second pass → bounded one-to-one outreach.

Acceptance gates:
- explicit buyer/automation relevance is required;
- Qwen is a second-pass gate, not a bypass;
- public business email is required for autonomous outreach;
- physical-address compliance gate is required;
- outreach is deduplicated and rate-capped;
- every contacted lead emits an immutable contacted event.

Primary workflow: Business Acquisition Engine.

## M3 — Transaction, Intake, and Delivery
**Flow:** customer reply → case/order → payment verification → paid event → intake → delivery.

Automated payment path:
- USDT on BNB Smart Chain (BEP-20);
- exact token, recipient, amount, successful transaction, and confirmation depth are independently verified;
- verified payments emit idempotent paid events;
- Validation Kit emits a delivered event after verified payment.

Customer-service automation:
- AgentMail polls the sales inbox every 5 minutes;
- pricing, purchase intent, offer interest, and payment messages are classified;
- order references and GitHub order records are created/updated;
- secrets are explicitly rejected.

QRIS/Dana remain supported checkout methods, but are not auto-marked paid without an independent merchant-side verification source.

Primary workflow: Autonomous AgentMail Sales Inbox.

## M4 — Profit Feedback
**Flow:** M2/M3 outcomes → revenue ledger → profit metrics → bounded policy multipliers → next acquisition priority.

Acceptance gates:
- event IDs are deduplicated;
- paid/refund/delivery/revenue/cost metrics are deterministic;
- sparse conversion is smoothed;
- offer/source multipliers stay within 0.75–1.50;
- outcome feedback never bypasses qualification, compliance, Qwen, deduplication, or outreach caps.

Primary workflow: M4 Profit Feedback Engine.

## End-to-end architecture

M1 DISCOVER → M2 QUALIFY/OUTREACH → M3 PAYMENT/INTAKE/DELIVERY → M4 PROFIT FEEDBACK → M2 PRIORITY UPDATE

The system does not manufacture revenue. A zero-revenue report means the transaction loop has not yet recorded a verified sale; it is not treated as a successful sale.

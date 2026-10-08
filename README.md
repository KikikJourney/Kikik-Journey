# Kikik Journey — AI Opportunity Lab

Kikik Journey is an execution-oriented opportunity discovery, validation, customer-acquisition, and small-business automation repository.

The repository combines a GitHub Actions radar with deterministic scoring, revenue packaging, buyer-request qualification, a Qwen second-pass worker, central checkout, payment verification, AgentMail delivery, profit feedback, and validation tests.

> ## 🛒 Ready to order?
>
> **[ORDER NOW — Open the Central Checkout](https://kikikjourney.github.io/Kikik-Journey/sales/manual-order.html?source=github-readme)**
>
> Choose the product, enter your contact email, select a payment method, and submit the order request from the customer-facing checkout page. **You do not need to read or modify source code to place an order.**
>
> Available offers: **WooCommerce → Google Sheets (Rp399.000)** · **WhatsApp → Google Sheets (Rp199.000)** · **Workflow Rescue (Rp250.000)** · **AI Opportunity Validation Kit (Rp19.000)**.
>
> Payment is independently verified before an order becomes **PAID**. After verification, delivery/confirmation is sent to the supplied email.

**Operating loop**

`M1 DISCOVER → M2 QUALIFY/ACQUIRE → M3 PAYMENT/INTAKE/DELIVERY → M4 PROFIT FEEDBACK → M2 PRIORITY UPDATE`

The repository is organized as a closed acquisition-to-profit loop. Generated evidence is treated as evidence, not as proof of customers or revenue.

## One-click orchestration

For a full manual operating cycle, use **`Zorathvael OS — Master Orchestrator`** in GitHub Actions. It is the single manual entry point and runs the milestones in order:

`M1 DISCOVER → M2 QUALIFY/ACQUIRE → M3 PAYMENT/DELIVERY → M4 PROFIT FEEDBACK`

The orchestrator dispatches the real M1, M2, and M3 workflows sequentially, passes the exact M1 artifact into M2, waits for each milestone to finish, and then waits for the M4 workflow triggered by the completed M3 run. Each milestone keeps its own Actions run, logs, artifacts, and validation. Scheduled workflows continue to operate independently.

## What the repository does

### 1. M1 — Opportunity Radar

`opportunity_radar.py` searches public GitHub data for recently active AI, LLM, automation, and AI-agent projects, then evaluates:

- project interest and activity
- observable setup, deployment, integration, documentation, and workflow pain
- buyer-intent signals
- packaging gaps
- license status
- recent issue evidence

It also searches public GitHub issues for explicit buyer/request signals such as automation, Google Sheets, WooCommerce, WhatsApp, and workflow needs.

The output is an opportunity report containing ranked candidates and buyer-request evidence.

### 2. Revenue Packaging

`opportunity_packager.py` converts ranked opportunities into bounded revenue experiments.

Current offer hypotheses include:

- **Implementation + integration service** — US$75–250 pilot hypothesis
- **Setup / production-readiness audit** — US$35–100 diagnostic hypothesis
- **Narrow convenience layer / workflow tool** — US$9–29 first paid version hypothesis

These are test hypotheses, not guaranteed market prices.

### 3. M2 — Customer Acquisition

`customer_acquisition.py` matches public buyer-request signals to fixed-scope offers.

Current fixed-scope offers include:

| Offer | Price | Scope |
|---|---:|---|
| WooCommerce → Google Sheets Automation | Rp399.000 | One WooCommerce store + one Google Sheet workflow |
| WhatsApp → Google Sheets Mini Automation | Rp199.000 | One message format + one Google Sheet workflow |
| Workflow Rescue Pilot | Rp250.000 | One workflow audit + implementation/prototype or documented automation path |
| AI Opportunity Validation Kit | Rp19.000 | Self-serve validation kit and supporting product assets |

The acquisition loop is:

`PUBLIC SIGNAL → QUALIFY → MATCH OFFER → RELEVANT ONE-TO-ONE RESPONSE → CHECKOUT → PAYMENT → INTAKE → DELIVERY`

The system does not treat a public request as consent, a customer, or a completed sale.

## M3 — Central Manual Checkout, Payment Verification, and AgentMail Delivery

The public conversion path is:

`SOCIAL/GITHUB TRAFFIC → CENTRAL CHECKOUT → PAYMENT VERIFICATION → PAID → AGENTMAIL DELIVERY → M4 PROFIT FEEDBACK`

### Customer-facing checkout

**[Open the Central Checkout →](https://kikikjourney.github.io/Kikik-Journey/sales/manual-order.html?source=github-readme)**

The central checkout is the live customer-facing order form: https://kikikjourney.github.io/Kikik-Journey/sales/manual-order.html. Customers should use that live page to order; they do not need to open repository source files.

It collects only:

- selected offer
- contact email
- optional name
- optional non-sensitive project/delivery notes
- payment method
- traffic source attribution

The checkout generates a unique order reference and prepares an order request. **AgentMail is a delivery channel, not the payment verifier.** A customer is marked `PAID` only after an independent payment verification succeeds.

For verified USDT payments:

- the payment is checked against the expected amount and configured recipient;
- a `paid` revenue event is emitted;
- AgentMail sends the delivery/intake email to the supplied contact email;
- a `delivered` event is emitted;
- M4 consumes the revenue events.

The automated central checkout currently accepts **USDT on BNB Smart Chain (BEP-20)** only. QRIS and Dana are not offered there because the system has no independent merchant-side verification path for them.

No passwords, OTPs, API keys, seed phrases, private keys, or full credentials are collected through the order flow.

### Revenue event ledger

`workers/revenue_event_ledger.py` provides an idempotent append-only event ledger. M3 payment/delivery events can therefore be consumed by M4 without double-counting.

## M4 — Profit Feedback

`workers/revenue_feedback.py` consumes acquisition and revenue outcomes to produce:

- revenue and profit totals;
- contacted, paid, delivered, and refund metrics;
- offer-level performance;
- source-level performance;
- bounded policy multipliers for future acquisition prioritization.

The feedback policy is bounded and cannot bypass buyer-intent qualification, compliance, Qwen screening, deduplication, or outreach caps.

The current ledger may legitimately contain zero revenue until a real customer payment occurs. The system never fabricates transactions to make the report look successful.

M4 is triggered from completed M2/M3 workflow runs and can also be run manually for validation. Its policy output is bounded and does not override qualification, compliance, deduplication, or outreach-cap controls.

## Payment

The automated Central Checkout currently accepts **USDT on BNB Smart Chain (BEP-20)** only. QRIS and Dana are not offered through the automated checkout because the system has no independent merchant-side verification path for them.

### USDT payment address

```
0x4ce7004e7127f8b2386eb355e088f127c24b3fac
```

**Network:** BNB Smart Chain (BEP-20)

When paying USDT, the sender must use the **BNB Smart Chain / BEP-20 network** and verify the destination address before confirming the transaction. The authoritative customer-facing payment amounts are maintained in `payment-config.json` and surfaced by the Central Checkout.

Payment configuration is represented by `payment-config.json` and `payment-config.example.json`. Public checkout pages should expose only the payment information intended for customers; secrets and private credentials must never be committed.

## Web sales assets

The repository includes a lightweight static sales site:

- `index.html` — main AI Opportunity Lab landing page
- `sales/manual-order.html` — **central customer checkout/order gateway**
- `sales/woocommerce.html` — WooCommerce automation offer
- `sales/wa-sheet.html` — WhatsApp → Sheets offer
- `sales/cashflow.html` — Workflow Rescue / pilot page
- `sales/checkout.html` — legacy/direct payment information page
- `sales/pilot-checkout.html` — legacy pilot payment information page
- `sales/wa-sheet-checkout.html` — legacy WhatsApp payment information page
- `sales/service.html` — service information
- `tools/workflow-diagnostic.html` — free workflow diagnostic
- `products/ai-opportunity-validation-kit/` — validation-kit product assets

**All customer purchase CTAs should route to the central checkout** so repository/social traffic has one clear order path.

## GitHub Actions automation

The M1–M4 automation is split across these workflows:

- `.github/workflows/opportunity-radar.yml` — M1 opportunity discovery
- `.github/workflows/business-acquisition.yml` — M2 qualified acquisition
- `.github/workflows/agentmail-autopilot.yml` — M3 payment/event processing and AgentMail delivery
- `.github/workflows/m4-profit-feedback.yml` — M4 revenue/profit feedback
- `.github/workflows/master-orchestrator.yml` — manual M1→M2→M3→M4 orchestration
- `.github/workflows/pages.yml` — static-site deployment and page validation

The main discovery workflow is:

`.github/workflows/opportunity-radar.yml`

It runs:

- on pushes to `main`
- manually through `workflow_dispatch`
- every six hours through a scheduled GitHub Actions run

The primary job:

1. checks out the repository
2. installs Python 3.12
3. runs `opportunity_radar.py`
4. runs `opportunity_packager.py`
5. runs `customer_acquisition.py`
6. validates JSON, Python syntax, tests, and generated output
7. uploads the opportunity, revenue, customer-acquisition, and integration queues as workflow artifacts

A second-pass worker then uses a local **Qwen3 1.7B GGUF** model through `llama.cpp` to qualify up to 10 prospects from the radar report. This worker is deliberately marked `continue-on-error: true` so a model/runtime failure does not invalidate the deterministic radar pipeline.

## Generated outputs

M3/M4 additionally maintain:

- `data/revenue_events.json` — append-only M3 revenue event state
- `data/profit_policy.json` — bounded M4 acquisition policy
- `profit_report.json` — current revenue/profit feedback report

The workflow produces and validates:

- `opportunity_report.json`
- `revenue_queue.json`
- `validation_cards.md`
- `customer_leads.json`
- `customer_acquisition.md`
- `integrations/prospect_queue.json`
- `integrations/prospect_queue.schema.json`
- Qwen second-pass `worker_prospect_queue.json`

These outputs are evidence queues, not proof of customers or revenue.

## Repository structure

```text
.
├── .github/workflows/
│   ├── master-orchestrator.yml
│   ├── opportunity-radar.yml
│   ├── business-acquisition.yml
│   ├── agentmail-autopilot.yml
│   ├── m4-profit-feedback.yml
│   └── pages.yml
├── assets/
├── docs/
│   └── 9router-integration.md
├── integrations/
│   ├── README.md
│   ├── prospect_queue.json
│   └── prospect_queue.schema.json
├── products/
│   └── ai-opportunity-validation-kit/
├── sales/
│   ├── README.md
│   ├── manual-order.html
│   ├── checkout.html
│   ├── payment-setup.md
│   ├── pilot-checkout.html
│   ├── service.html
│   ├── wa-sheet.html
│   ├── wa-sheet-checkout.html
│   ├── woocommerce.html
│   └── cashflow.html
├── solutions/
├── tests/
├── tools/
│   └── workflow-diagnostic.html
├── workers/
│   ├── manual_order_gateway.py
│   ├── revenue_event_ledger.py
│   └── revenue_feedback.py
├── customer_acquisition.py
├── opportunity_packager.py
├── opportunity_radar.py
├── payment-config.example.json
├── payment-config.json
└── index.html
```

## Validation and safety rules

The repository is designed around evidence rather than hype:

- A project is not considered a business opportunity merely because an AI model finds it interesting.
- A revenue hypothesis is not a sale.
- A public buyer request is not permission to spam.
- Outreach should be relevant and one-to-one.
- No passwords, OTPs, API keys, or other private credentials should be requested publicly.
- Licenses and commercial-use rights must be reviewed before redistribution, hosting, or derivative commercial use.
- Third-party APIs and dependencies must be treated as external dependencies.
- Payment receipt must be verified before treating an order as paid.
- No revenue outcome is guaranteed.

## Development

The workflow uses Python 3.12.

Run the core validation locally with:

```bash
python -m json.tool opportunity_report.json
python -m json.tool revenue_queue.json
python -m json.tool customer_leads.json
python -m json.tool integrations/prospect_queue.json
python -m json.tool integrations/prospect_queue.schema.json
python -m py_compile opportunity_radar.py opportunity_packager.py customer_acquisition.py
python -m unittest discover -s tests -p "test_*.py" -v
```

The authoritative automation configuration is the GitHub Actions configuration under `.github/workflows/`. M1–M4 status is determined from actual workflow runs and generated artifacts, not README claims.

# Kikik Journey — AI Opportunity Lab

Kikik Journey is an execution-oriented opportunity discovery, validation, customer-acquisition, and small-business automation repository.

The repository combines a GitHub Actions radar with deterministic scoring, revenue packaging, buyer-request qualification, a Qwen second-pass worker, lightweight sales pages, payment configuration, and validation tests.

**Operating loop**

`DISCOVER → EVIDENCE → SCORE → PACKAGE → QUALIFY → OFFER → PAYMENT → INTAKE → DELIVERY`

This repository is deliberately separate from [Crypto-Scanner](https://github.com/KikikJourney/Crypto-Scanner).

## What the repository does

### 1. Opportunity Radar

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

### 3. Customer Acquisition

`customer_acquisition.py` matches public buyer-request signals to fixed-scope offers.

Current fixed-scope offers include:

| Offer | Price | Scope |
|---|---:|---|
| WooCommerce → Google Sheets Automation | Rp399.000 | One WooCommerce store + one Google Sheet workflow |
| WhatsApp → Google Sheets Mini Automation | Rp199.000 | One message format + one Google Sheet workflow |
| Workflow Rescue Pilot | Rp250.000 | One workflow audit + implementation/prototype or documented automation path |

The acquisition loop is:

`PUBLIC SIGNAL → QUALIFY → MATCH OFFER → RELEVANT ONE-TO-ONE RESPONSE → CHECKOUT → PAYMENT → INTAKE → DELIVERY`

The system does not treat a public request as consent, a customer, or a completed sale.

## Payment

Kikik Journey accepts direct payment through:

- **QRIS**
- **Dana**
- **USDT — BNB Smart Chain (BEP-20)**

### USDT payment address

```
0x4ce7004e7127f8b2386eb355e088f127c24b3fac
```

**Network:** BNB Smart Chain (BEP-20)

When paying USDT, the sender must use the **BNB Smart Chain / BEP-20 network** and verify the destination address before confirming the transaction.

Payment configuration is represented by `payment-config.json` and `payment-config.example.json`. Public checkout pages should expose only the payment information intended for customers; secrets and private credentials must never be committed.

## Web sales assets

The repository includes a lightweight static sales site:

- `index.html` — main AI Opportunity Lab landing page
- `sales/woocommerce.html` — WooCommerce automation offer
- `sales/wa-sheet.html` — WhatsApp → Sheets offer
- `sales/cashflow.html` — Workflow Rescue / pilot page
- `sales/checkout.html` — checkout flow
- `sales/pilot-checkout.html` — pilot checkout
- `sales/wa-sheet-checkout.html` — WhatsApp → Sheets checkout
- `sales/service.html` — service information
- `tools/workflow-diagnostic.html` — free workflow diagnostic
- `products/ai-opportunity-validation-kit/` — validation-kit product assets

The landing page currently presents the paid offers at Rp399.000, Rp199.000, Rp250.000, and the validation kit at Rp19.000, plus a free scorecard.

## GitHub Actions automation

The main workflow is:

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
│   └── opportunity-radar.yml
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

The authoritative automation configuration is the GitHub Actions workflow under `.github/workflows/`.

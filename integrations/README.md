# AI Opportunity Lab — Tool Integration

This repository is the execution control plane for opportunity discovery, qualification, outreach preparation, and delivery tracking.

## Connected tool roles

| Tool | Role | Repository boundary |
|---|---|---|
| GitHub | Source of truth, issues, code, workflows, artifacts | Native GitHub Actions + repository files |
| AI Vibe Prospecting | Business/prospect discovery, buying-intent enrichment, decision-maker discovery | External discovery input; never store secrets |
| AgentMail | One-to-one outbound email and inbound response handling | External execution; write only normalized lead/outcome data back to repo |
| Firecrawl | Public business-web evidence enrichment for actionable prospects | Optional GitHub Actions evidence layer; never changes score/qualification |
| Postiz | Bounded social distribution and scheduling | Optional GitHub Actions publishing layer; central checkout only; no private prospect data |
| Browser automation | Public-web research and user-directed workflows where a browser is required | External execution; no credential harvesting or bypasses |
| ChatGPT | Reasoning, qualification, offer matching, message generation, QA | Human/agent decision layer |

## Operating loop

`DISCOVER → QUALIFY → MATCH OFFER → OUTREACH → RESPONSE → PAYMENT → DELIVERY → OUTCOME`

The repository stores the auditable state. External plugins provide capabilities that GitHub Actions cannot directly invoke.

## Important integration boundary

GitHub Actions cannot directly call ChatGPT-side plugins such as AI Vibe Prospecting or AgentMail because those connections live in the ChatGPT environment, not in the GitHub runner.

Therefore this repo uses a **plugin bridge contract**:

1. AI Vibe Prospecting produces a prospect dataset.
2. The dataset is normalized into `integrations/prospect_queue.json`.
3. GitHub Actions validates/deduplicates the queue and packages it with the existing acquisition artifacts.
4. AgentMail is used for one-to-one outreach from the normalized queue.
5. Replies and payment/delivery outcomes are recorded as normalized status data; never store passwords, OTPs, API keys, access tokens, card data, or private credentials.

This avoids pretending that a GitHub workflow can execute a ChatGPT plugin.

## Current offer matching

- WooCommerce → Google Sheets: Rp399.000
- WhatsApp → Google Sheets: Rp199.000
- Workflow Rescue Pilot: Rp250.000
- AI Opportunity Validation Kit: Rp19.000

Prices are current offer configuration, not revenue guarantees.

## Safety / quality controls

- No mass unsolicited messaging.
- No credential collection in public issues or outreach.
- Public buyer intent is treated as a lead signal, not consent or a sale.
- No payment is marked received without evidence from an available payment/account integration.
- No customer is marked won merely because an email was sent.
- External AI model APIs are not required by the repository radar.


## Native automation boundary

Firecrawl and Postiz are integrated as optional HTTP adapters inside GitHub Actions. They are not ChatGPT-side plugins. Missing provider secrets disable the corresponding capability without breaking the deterministic pipeline. Provider configuration errors are surfaced as explicit failures in the dedicated integration workflow.

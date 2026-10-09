# Product-market audit — 9 October 2026

## Executive decision

Do not add a fifth paid product yet. Keep all four offers available as hypotheses, but narrow the next validation cycle to one business buyer, one costly workflow, one deliverable, and one observable purchase signal. Repository activity and public complaints are not sales evidence.

## Product decisions

| Offer | Current price | Decision | Evidence required before scaling |
|---|---:|---|---|
| WooCommerce → Google Sheets | Rp399,000 | Reposition; keep as a specialist implementation pilot | Store owner confirms a gap not already handled by a connector; order reconciliation, SKU mapping, failed-sync recovery, or custom reporting is a real paid need |
| WhatsApp → Google Sheets | Rp199,000 | Keep as a hypothesis; verify integration path before selling | Buyer has a repeatable message format, can lawfully provide sample data, and accepts the actual WhatsApp/API dependency and costs |
| Workflow Rescue Pilot | Rp250,000 | First service offer to validate, not yet a proven winner | A named business buyer confirms the repetitive task, impact, urgency, scope, and willingness to pay |
| AI Opportunity Validation Kit | Rp19,000 | Reposition test; do not build a larger kit yet | Compare demand from digital-product builders with demand from ordinary small-business operators; require a purchase or explicit paid-pilot commitment |

## Public market evidence

### 1. Generic WooCommerce → Sheets sync is already commoditized

- Zapier lists ready-made WooCommerce-to-Google-Sheets templates, including saving new orders as rows: https://zapier.com/apps/google-sheets/integrations/woocommerce
- Make offers a WooCommerce and Google Sheets integration with order triggers: https://www.make.com/en/integrations/woocommerce/google-sheets
- The WooCommerce marketplace lists a Google Sheet Connector at US$49 for one year with order/product sync, field mapping, and logs: https://woocommerce.com/products/google-sheet-connector/

**Implication:** do not compete on “connect two apps” alone. Test whether merchants pay for a specific exception, reporting requirement, migration, reconciliation, or recovery outcome. These sources establish available alternatives, not that a particular Indonesian merchant will buy our service.

### 2. Manual work and integration are credible business pains, but not proof of local demand

Intuit's 2024 Business Solutions survey reports that respondents prioritized more automation (72%) and better integration (64%); respondents reported an average of 25 hours per week on manual data entry and reconciliation. Source: https://quickbooks.intuit.com/r/small-business-data/business-solutions-survey-2024/

**Limit:** this is a survey of its own respondents and should not be generalized to all Indonesian UMKM. Use it as a problem hypothesis; collect local buyer evidence separately.

### 3. WhatsApp workflows require technical qualification

A WhatsApp-to-Sheets offer must identify the actual input path: WhatsApp Business Platform/API, an authorized integration provider, or a human-provided export/sample. Do not imply that a normal WhatsApp account can be safely and automatically read by a generic script. Confirm account requirements, provider fees, consent, data retention, message format, and failure handling before accepting payment.

Public problem discovery may include relevant business forums and public business pages. A public post is evidence of a possible problem, not consent to contact, proof of budget, or a sale.

### 4. Validation kits compete with free templates and other toolkits

The current kit contains a scorecard, 48-hour checklist, research prompts, paid-pilot offer template, and license-risk checklist. The free Lite version already gives users a compact scorecard and a five-prospect test.

**Implication:** the paid version needs a clear incremental outcome (evidence-backed decision and buyer-ready pilot offer), not just more prompts. Test two distinct audiences and keep the positioning that produces stronger qualified buyer signals.

## Research protocol — public sources beyond GitHub

The public-research pass must include:
1. Search-engine-indexed business pages and public requests for help.
2. Relevant user communities and support forums (only where the content is publicly accessible).
3. Competitor product pages, pricing pages, feature lists, reviews, and documented limitations.
4. Public marketplace listings and service offers.
5. Local Indonesian business context where sources are available, with geography and sample limitations recorded.
6. Direct, small-scale validation of the resulting offer with relevant prospects.

For each finding record: source URL, observation date, buyer segment, exact problem evidence, existing workaround, alternatives/pricing, confidence, and next validation action. Separate **problem evidence**, **commercial-intent evidence**, and **payment evidence**. Never promote a lead to customer status based on a search result or an AI-generated score.

## Live public buyer-request validation — 9 October 2026

These are public requests for paid help, not Kikik Journey customers. The posts are evidence of problem/intent only; no outreach response or purchase has been verified.

| Public request | Evidence and recency | Fit to current offers | Qualification / next action |
|---|---|---|---|
| [Make freelancer needed for project](https://community.make.com/t/make-freelancer-needed-for-project/115431) | Original post says the author is stuck and is happy to pay for help; thread activity shown on 8 October and 76 replies. | Best match for Workflow Rescue Pilot, but the actual workflow is unspecified and the thread is crowded. | Highest priority for a tightly scoped first reply; ask for the workflow goal, current failing step, and a redacted screenshot. Do not quote implementation before scope is known. |
| [WhatsApp Cloud API → Google Sheets](https://community.make.com/t/i-need-help-with-a-scenario-to-connect-the-whatsapp-cloud-api-with-google-sheets/115156) | Explicit request for help; thread activity shown on 9 October and 51 replies. The initial post does not specify inbound vs outbound flow or confirm that Meta/Make are configured. | Direct fit for WhatsApp → Google Sheets Mini Automation. | Strong problem-fit but high competition and unresolved scope. Offer a one-direction starter only if API access is already configured; separate API/account setup and platform fees. |
| [PDF invoice emailing automation](https://community.make.com/t/need-make-com-expert-to-automate-pdf-invoice-emailing-from-computer-desktop-or-can-be-from-google-sheets-google-drive/112489) | Commercial janitorial business with about 80 recurring clients; needs scheduled invoice-PDF matching, email delivery, sent-state tracking, and safe manual resend. Thread activity shown on 9 October and 46 replies. | A possible Workflow Rescue / custom automation opportunity, but materially broader than the current small pilot. | Do not sell at the current Rp250,000 implementation scope. First offer a diagnostic or 5-client synthetic/redacted pilot, with Google Drive requirement and duplicate/misdelivery tests explicit. |
| [WordPress + Make + Brevo integration](https://community.make.com/t/wordpress-make-com-brevo-integration-expert/115942) | Detailed multi-system migration/integration request; thread activity shown on 9 October and 77 replies. One buyer reply states an approximate USD 25/hour budget. | Too broad for any current fixed-price starter without a diagnostic. | Watch only; narrow to one form → Make → Brevo path and test consent, duplicates, and failure handling before quoting. |

### Pricing decision from the live sample

- The WhatsApp offer at Rp199,000 is about US$11 at the repository's configured quote rate. Public replies in the exact-fit thread propose roughly US$75–250 for implementation. This does **not** prove the market will pay those prices, but it shows the current offer is priced far below visible competing quotes.
- Workflow Rescue at Rp250,000 is about US$14. The public invoice automation thread shows materially larger scopes quoted around US$120–650. Do not promise a full production build at the current pilot price.
- Keep the current prices as *entry-pilot hypotheses* for now, but narrow scope: one direction or one failing path, existing accounts/connections already working, redacted/synthetic test data, explicit acceptance checks, and a written handover. Quote integrations, migrations, and production rollouts separately.
- The Rp399,000 WooCommerce offer should not compete with generic connectors. Validate only a specific reconciliation, SKU mapping, duplicate-sync, exception recovery, or custom-reporting problem.
- No relevant public evidence found here validates the Rp19,000 AI Opportunity Validation Kit. Keep it available but do not prioritize paid-kit expansion until buyer behavior supports it.

### What this validates — and what it does not

**Validated at the problem level:** there are current public requests for paid workflow help, including an exact WhatsApp-to-Sheets request and a generic paid workflow-rescue request.

**Not yet validated:** the buyer's willingness to buy from Kikik Journey, acceptance of our exact scope/price, a reply to our outreach, or any paid order. These threads already contain many competing replies; they should not be counted as reachable leads until a one-to-one response is possible and the request is still open.

## Decision gates

- **Keep testing:** repeated, specific problem evidence and a buyer that can be reached.
- **Reposition:** problem exists but the current offer is generic, technically ambiguous, or poorly matched to the buyer.
- **Pause:** no clear buyer, no differentiated outcome, or delivery depends on unverified access/paid infrastructure.
- **Scale:** only after a verified paid order or repeated explicit paid commitments and a deliverable that can be fulfilled profitably.

## Current operational blockers

1. Checkout copy must not promise QRIS or DANA while the automated payment verifier only supports USDT on BNB Smart Chain (BEP-20).
2. The WhatsApp offer must not promise QRIS payment while the checkout does not support it.
3. Public research and lead queues must not be reported as customers or revenue. The current profit report snapshot records zero paid orders and zero revenue; that is an honest baseline, not a successful sales result.
4. Before enabling QRIS/DANA checkout, implement a documented manual-verification path or a verified payment integration. Do not mark an order PAID from a customer screenshot or self-reported transfer alone.

## Next experiment

Run one bounded experiment for the Workflow Rescue service:
- Select one concrete problem pattern from public business evidence.
- Identify up to 5 relevant, reachable business prospects with source URLs and evidence.
- Prepare a single fixed-scope outcome and disclose dependencies before quoting.
- Use a relevant, respectful one-to-one approach; honor opt-outs.
- Track contacted → reply → qualified → explicit paid intent → verified payment → delivered.
- Do not expand scope or build a new product based on clicks, likes, search volume, or model scores alone.

This document is a research and operating decision record, not a claim that market demand or revenue has already been validated.
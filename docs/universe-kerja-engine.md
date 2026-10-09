# Kikik Journey Universe Engine — KERJA Operating Specification

**Status:** Phase 1 specification / control-plane contract  
**Primary objective:** discover and validate the highest-quality zero-upfront-cost revenue opportunities across industries, then move qualified opportunities through customer research, offer design, acquisition, payment, delivery, and measured profit feedback.  
**Operating trigger:** the user says **KERJA** in ChatGPT.  
**Commercial boundary:** Shopify is a time-boxed research trial only; it is not the core business or a required sales channel. The system must remain channel-independent.  
**Payment preference:** USDT on BNB Smart Chain (BEP-20), using the existing Zorathvael OS receiving address configured for customer checkout. Never copy private keys or seed phrases into the repository.

## 1. Operating principle

Kikik Journey is an opportunity-to-cash operating engine, not a marketplace listing bot. It should prioritize real customer problems and observable demand over trendy topics, and should report evidence separately from hypotheses.

A single KERJA instruction should initiate the available operating cycle:
1. Audit current repository/workflow status and connected tools available in the current session.
2. Discover cross-industry problems and buyer-intent signals from public, lawful sources.
3. Rank opportunities by evidence, reachable buyer density, urgency, willingness-to-pay evidence, delivery feasibility, time-to-cash, competition, licensing, and total cash cost.
4. Research a bounded set of real organizations and public business contact routes; retain source URLs, timestamps, confidence, and reason for fit.
5. Match each qualified prospect to one narrowly scoped offer that can be delivered honestly.
6. Prepare relevant, individualized outreach and queue it for an available authorized sending tool. Respect consent, opt-outs, platform rules, and rate limits; do not mass-spam.
7. Route interested buyers to a platform-independent landing page/order intake and show the configured USDT BEP-20 payment instructions.
8. Mark an order paid only after independent transaction verification confirms chain, token, destination, amount, and transaction finality. An order reference alone is not payment evidence.
9. Deliver only the agreed scope; record delivery evidence and support obligations.
10. Measure replies, qualified leads, conversion, paid revenue, refunds, delivery cost, and net profit; use measured results to reprioritize.

A ChatGPT-side tool is not automatically callable from GitHub Actions. Cross-environment tools must exchange data through explicit, validated files or APIs. Do not describe a connector as integrated until an end-to-end test proves it.

## 2. Opportunity scoring contract

Each opportunity must have a source-backed record. Suggested normalized dimensions (0–5 each):
- **Demand evidence (25%)** — explicit requests, recurring complaints, active buying signals, or validated interviews.
- **Reachability (15%)** — an ethical, public route to the likely buyer/decision-maker.
- **Urgency / cost of pain (15%)** — evidence that the problem is costly, frequent, or time-sensitive.
- **Delivery feasibility (15%)** — can be fulfilled with currently available skills and free tools.
- **Time to first payment (15%)** — a plausible path to a paid pilot without requiring a large audience.
- **Margin potential (10%)** — expected revenue minus direct delivery/payment costs and refund exposure.
- **Risk / rights / dependency (5%)** — lower platform, licensing, privacy, and vendor risk scores higher.

Keep the component scores and evidence visible. Missing evidence is **unknown**, not a zero-cost assumption. Do not let an AI score override a hard blocker such as unlawful data use, unclear commercial rights, unsafe work, or an unverified payment.

## 3. Zero-additional-cost policy

The required cash budget for the next experiment is **IDR 0**. Prefer tools already available, open-source software, public datasets, free tiers, and static hosting already configured. Do not activate a paid plan, buy credits, register a paid domain, purchase ads, or incur a transaction/service fee without explicit approval.

For every proposed tool, record:
- purpose and capability;
- free-tier limits and whether a credit card is required;
- license and commercial-use rights;
- data access/privacy implications;
- whether credentials or a new account are needed;
- fallback if the free tier stops working;
- proof from a small test before production use.

“Free” must not be assumed: verify limits and payment requirements before adopting a service. Payment network fees may still exist and must be disclosed; zero-upfront-cost does not mean every transaction is fee-free.

## 4. Channel independence

The source of truth is Kikik Journey's own repository, lightweight website/order gateway, validated prospect queue, payment evidence, and outcome ledger. Social platforms, directories, Shopify, marketplaces, and prospecting vendors are optional acquisition/research channels only.

- Shopify: research trial for three days; do not make core logic, product ownership, customer records, or payment processing dependent on it.
- Owned web path: keep the static sales site and central order gateway as the primary conversion path where feasible.
- Payment: USDT BEP-20 remains the preferred method. Display the existing configured receiving address and network consistently. Never silently switch networks or currencies.
- Portability: store normalized records in documented JSON/CSV formats and retain source references so channels can be replaced.
- No false independence claims: GitHub Pages, GitHub Actions, and any external email/payment infrastructure are still dependencies and must be listed as such.

## 5. Safety and approval gates

**May run automatically:** public-source discovery, deduplication, scoring, offer drafting, research summaries, validation, test runs, report generation, and preparation of individualized outreach.

**Requires explicit user approval unless a separately tested policy grants permission:** sending external messages, publishing public content, changing production payment configuration, deploying a materially changed checkout, accepting unusual/custom work, issuing refunds, spending money, signing contracts, or handling sensitive customer data.

**Never do:** fabricate prospects, intent, testimonials, payments, sales, or delivery; scrape private data; bypass access controls; collect passwords/OTPs/seed phrases/private keys; send bulk unsolicited outreach; guarantee profit; or use third-party assets/models without checking commercial-use rights.

## 6. Required data records

Each prospect should include stable ID, organization/person or business identifier where public, source URL, observed problem/intent, evidence excerpt (minimal), observed date, contact route/source, relevance rationale, confidence, proposed offer, outreach status, opt-out/suppression state, and last-updated time.

Each order should include order ID, offer/version, amount/currency, expected network/token/destination, buyer-provided contact, payment transaction hash, independent verification status, paid timestamp, delivery status/evidence, refund/dispute status, and source attribution. Do not store secrets or unnecessary personal data.

Each experiment should record hypothesis, target segment, offer, price, channel, sample size, cost, response rate, qualified-lead rate, paid conversion, delivery hours, gross revenue, direct cost, refunds, net result, and decision (continue / change / stop).

## 7. Definition of done for KERJA runs

A run is complete only when it emits a compact report containing:
- repositories and tools actually checked;
- workflow runs and validation outcomes actually observed;
- top ranked opportunities with evidence and uncertainty;
- qualified prospects and why they fit;
- offers/outreach prepared or sent (clearly distinguished);
- payments independently verified and deliveries completed (or zero);
- errors, blockers, and remaining manual approvals;
- next actions ranked by expected impact, cost, and time.

Do not label a workflow green unless its run status says success. Do not label an integration active until its end-to-end path has passed. Do not label revenue as profit until direct costs and refunds are accounted for.

## 8. Phase 1 implementation sequence

1. Establish this specification and the KERJA reporting contract.
2. Audit existing M1–M4 workflows, actual recent run outcomes, data schemas, payment verification, delivery, and tests against the contract.
3. Implement the smallest changes that remove hard blockers and broaden discovery beyond GitHub-only signals.
4. Add tests for evidence provenance, deduplication, suppression/opt-out, payment verification boundaries, and profit accounting.
5. Run the full existing validation suite and the affected workflows; preserve run IDs and artifacts as evidence.
6. Expand to additional free tools only after capability, cost, licensing, and end-to-end tests pass.

This document is a specification, not proof that all listed capabilities are already implemented. The actual implementation state must be established from code and workflow evidence.

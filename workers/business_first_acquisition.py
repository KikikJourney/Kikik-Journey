import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPORT = "opportunity_report.json"
BUSINESS = "business_prospects.json"
COMBINED = "business_first_report.json"
OUTPUT = "customer_leads.json"
CARDS = "customer_acquisition.md"
POLICY = Path("data/profit_policy.json")

OFFERS = [
    {
        "name": "WooCommerce → Google Sheets Automation",
        "price_idr": 399000,
        "checkout": "sales/manual_order.html?offer=woocommerce&source=outreach",
        "keywords": ["woocommerce", "google sheets", "orders", "inventory", "stock", "order data"],
        "scope": "One WooCommerce store + one Google Sheet workflow + agreed fields.",
        "timebox": "1-2 days",
    },
    {
        "name": "WhatsApp → Google Sheets Mini Automation",
        "price_idr": 199000,
        "checkout": "sales/manual_order.html?offer=whatsapp&source=outreach",
        "keywords": ["whatsapp", "google sheets", "message", "attendance", "expense", "stock", "follow-up"],
        "scope": "One message format + one Google Sheet workflow.",
        "timebox": "1-2 days",
    },
    {
        "name": "Workflow Rescue Pilot",
        "price_idr": 250000,
        "checkout": "sales/manual_order.html?offer=workflow&source=outreach",
        "keywords": ["automation", "workflow", "manual", "integration", "zapier", "make", "n8n"],
        "scope": "One workflow audit + implementation/prototype or documented automation path.",
        "timebox": "1-2 days",
    },
]

INTENT = (
    "need help", "need someone", "looking for", "need a developer", "hire",
    "hiring", "paid help", "who can build", "who can fix", "help me automate",
    "looking to automate", "want to automate", "need this built", "need this fixed",
)
ARTIFACTS = ("roadmap", "research report", "report only", "backlog", "directory", "job board", "status update")


def norm(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def load_policy():
    if not POLICY.exists():
        return {}
    try:
        return json.loads(POLICY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def feedback_multiplier(offer_name, source):
    policy = load_policy()
    offer_mult = float(policy.get("offer_multipliers", {}).get(offer_name, 1.0))
    source_mult = float(policy.get("source_multipliers", {}).get(source, 1.0))
    return max(0.75, min(1.50, offer_mult * source_mult))


def match_offer(text):
    t = norm(text)
    ranked = [(sum(k in t for k in o["keywords"]), o) for o in OFFERS]
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]


def gate(item, offer):
    t = norm(f'{item.get("title","")} {item.get("evidence",item.get("text",""))}')
    return (
        any(x in t for x in INTENT)
        and any(x in t for x in offer["keywords"])
        and not any(x in t for x in ARTIFACTS)
    )


def make_lead(item, source):
    offer = match_offer(f'{item.get("title","")} {item.get("evidence",item.get("text",""))}')
    explicit = gate(item, offer)
    base = float(item.get("score", 0))
    contact_bonus = 20 if item.get("contact_email") else 0
    source_bonus = 10 if source == "public_business_web_signal" else 0
    adjusted = (base + contact_bonus + source_bonus) * feedback_multiplier(offer["name"], source)
    score = min(100, round(adjusted, 2))
    qualified = explicit and source in {"public_business_web_signal", "public_buyer_request"}
    actionable = bool(qualified and item.get("contact_email") and item.get("website") and item.get("evidence") and item.get("commercial_intent", 0) >= 1 and item.get("reachability") == "direct_email")
    return {
        "status": "QUALIFIED" if qualified else "WATCH",
        "priority_score": score,
        "source": source,
        "source_type": source,
        "title": item.get("title"),
        "url": item.get("url") or item.get("website"),
        "website": item.get("website") or item.get("url"),
        "contact_email": item.get("contact_email"),
        "contact_channel": item.get("contact_channel"),
        "reachability": item.get("reachability"),
        "evidence": item.get("evidence"),
        "commercial_intent": item.get("commercial_intent"),
        "matched_offer": offer["name"],
        "price_idr": offer["price_idr"],
        "checkout_path": offer["checkout"],
        "scope": offer["scope"],
        "timebox": offer["timebox"],
        "feedback_multiplier": feedback_multiplier(offer["name"], source),
        "response_draft": (
            f"Hi — I noticed your public request about “{item.get('title','your workflow')}”. "
            f"I can handle a fixed-scope {offer['name']} pilot: {offer['scope']} "
            f"for Rp{offer['price_idr']:,}, targeted to {offer['timebox']}. "
            "If this is still relevant, I can send the exact checkout/intake path. "
            "If not relevant, reply STOP and I will not follow up."
        ).replace(",", "."),
        "actionable": actionable,
        "actionability_reason": "qualified + direct public business email + website + evidence + explicit commercial intent" if actionable else "not ready for autonomous outreach",
        "auto_contact_eligible": actionable,
        "do_not_do": [
            "Do not mass-message.",
            "Do not claim the prospect agreed to buy.",
            "Do not request passwords, OTPs, API keys, seed phrases, or private credentials.",
            "Honor STOP/unsubscribe requests.",
        ],
    }


def main():
    report = json.loads(open(REPORT, encoding="utf-8").read())
    business = json.loads(open(BUSINESS, encoding="utf-8").read())
    business_requests = []
    for item in business.get("prospects", []):
        x = dict(item)
        x["url"] = x.get("website")
        business_requests.append(x)

    # AgentMail acquisition is deliberately isolated from GitHub buyer-request discovery.
    combined_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "Public business-web prospects only for AgentMail acquisition.",
        "buyer_requests": [],
    }
    with open(COMBINED, "w", encoding="utf-8") as h:
        json.dump(combined_payload, h, indent=2, ensure_ascii=False)

    leads = [make_lead(x, "public_business_web_signal") for x in business.get("prospects", [])]
    dedup = {}
    for lead in leads:
        key = (lead.get("contact_email") or lead.get("url") or "").lower()
        if key and (key not in dedup or lead["priority_score"] > dedup[key]["priority_score"]):
            dedup[key] = lead
    leads = sorted(dedup.values(), key=lambda x: x["priority_score"], reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "AgentMail acquisition queue built exclusively from public business-web signals; GitHub buyer requests are handled by the dedicated GitHub outreach worker.",
        "summary": {
            "total": len(leads),
            "qualified": sum(x["status"] == "QUALIFIED" for x in leads),
            "watch": sum(x["status"] == "WATCH" for x in leads),
            "business_email_leads": sum(bool(x.get("contact_email")) for x in leads),
            "actionable": sum(bool(x.get("actionable")) for x in leads),
            "auto_contact_eligible": sum(bool(x["auto_contact_eligible"]) for x in leads),
        },
        "lead_loop": "BUSINESS SIGNAL → REACHABLE CONTACT → QUALIFY → OFFER → ONE-TO-ONE OUTREACH → CHECKOUT → PAYMENT → DELIVERY → FEEDBACK",
        "warning": "Public business data is a lead signal, not consent or a sale. Outreach is bounded, relevant, deduplicated and must honor opt-out requests.",
        "leads": leads[:50],
    }
    with open(OUTPUT, "w", encoding="utf-8") as h:
        json.dump(output, h, indent=2, ensure_ascii=False)

    lines = [
        "# Customer Acquisition Queue", "",
        f"Generated: {output['generated_at']}", "",
        f"- Total: **{output['summary']['total']}**",
        f"- Qualified: **{output['summary']['qualified']}**",
        f"- Watch: **{output['summary']['watch']}**",
        f"- Reachable business-email leads: **{output['summary']['business_email_leads']}**",
        f"- Auto-contact eligible: **{output['summary']['auto_contact_eligible']}**", "",
        "> AgentMail queue source: public business websites with public contact emails. GitHub buyer requests are intentionally excluded from this queue and handled by the dedicated GitHub channel.", "",
    ]
    for lead in leads[:25]:
        lines += [
            f"## {lead['status']} — {lead['matched_offer']}",
            f"- Priority: **{lead['priority_score']}**",
            f"- Feedback multiplier: **{lead['feedback_multiplier']}**",
            f"- Business/request: {lead['title']}",
            f"- Website/source: {lead['url']}",
            f"- Contact: {lead.get('contact_email') or 'not available'}",
            f"- Price: **Rp{lead['price_idr']:,}**".replace(",", "."),
            f"- Next: {('bounded one-to-one outreach' if lead['auto_contact_eligible'] else 'wait for stronger/reachable signal')}",
            "",
        ]
    open(CARDS, "w", encoding="utf-8").write("\n".join(lines))
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()

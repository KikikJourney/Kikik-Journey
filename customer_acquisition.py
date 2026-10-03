import json
import re
from datetime import datetime, timezone

INPUT = "opportunity_report.json"
OUTPUT = "customer_leads.json"
CARDS = "customer_acquisition.md"

OFFER_RULES = [
    {
        "name": "WooCommerce → Google Sheets Automation",
        "price_idr": 399000,
        "checkout": "sales/checkout.html?offer=woocommerce",
        "keywords": ["woocommerce", "google sheets", "orders", "inventory", "stock", "order data"],
        "scope": "One WooCommerce store + one Google Sheet workflow + agreed fields.",
        "timebox": "1-2 days",
    },
    {
        "name": "WhatsApp → Google Sheets Mini Automation",
        "price_idr": 199000,
        "checkout": "sales/checkout.html?offer=whatsapp",
        "keywords": ["whatsapp", "google sheets", "message", "attendance", "expense", "stock", "follow-up"],
        "scope": "One message format + one Google Sheet workflow.",
        "timebox": "1-2 days",
    },
    {
        "name": "Workflow Rescue Pilot",
        "price_idr": 250000,
        "checkout": "sales/checkout.html?offer=workflow",
        "keywords": ["automation", "workflow", "manual", "integration", "zapier", "make", "n8n"],
        "scope": "One workflow audit + implementation/prototype or documented automation path.",
        "timebox": "1-2 days",
    },
]

BUYER_TERMS = {
    "need": 12, "looking for": 14, "want": 8, "help": 8, "automate": 10,
    "automation": 7, "integration": 7, "manual": 6, "time": 4, "hours": 4,
    "google sheets": 8, "woocommerce": 8, "whatsapp": 8,
}

def normalize(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def match_offer(text):
    normalized = normalize(text)
    ranked = []
    for offer in OFFER_RULES:
        score = sum(1 for keyword in offer["keywords"] if keyword in normalized)
        ranked.append((score, offer))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] > 0 else OFFER_RULES[-1]

def qualify(item):
    text = normalize(f'{item.get("title", "")} {item.get("evidence", "")}')
    signal = sum(weight for phrase, weight in BUYER_TERMS.items() if phrase in text)
    recency = 0
    if item.get("updated_at"):
        try:
            updated = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            age_days = max(0, (datetime.now(timezone.utc) - updated).days)
            recency = max(0, 12 - min(12, age_days // 3))
        except ValueError:
            pass
    score = min(100, round(float(item.get("score", 0)) + signal + recency, 2))
    return score, ("QUALIFIED" if score >= 35 else "WATCH")

def response_draft(item, offer):
    title = item.get("title", "your workflow")
    return (
        f"Hi — I found your request about “{title}”. "
        f"I run a small fixed-scope implementation for {offer['name']}: {offer['scope']} "
        f"The pilot is Rp{offer['price_idr']:,} and is scoped to {offer['timebox']}. "
        "If the workflow is still needed, the offer page has the exact scope and checkout. "
        "No passwords, OTPs, or private API keys should be posted publicly; those are handled only after payment through the agreed intake."
    ).replace(",", ".")

def main():
    with open(INPUT, encoding="utf-8") as handle:
        report = json.load(handle)

    leads = []
    for item in report.get("buyer_requests", []):
        offer = match_offer(f'{item.get("title", "")} {item.get("evidence", "")}')
        score, status = qualify(item)
        leads.append({
            "status": status,
            "priority_score": score,
            "source": "public_buyer_request",
            "title": item.get("title"),
            "url": item.get("url"),
            "repository": item.get("repository"),
            "updated_at": item.get("updated_at"),
            "evidence": item.get("evidence"),
            "matched_offer": offer["name"],
            "price_idr": offer["price_idr"],
            "checkout_path": offer["checkout"],
            "scope": offer["scope"],
            "timebox": offer["timebox"],
            "response_draft": response_draft(item, offer),
            "next_action": (
                "Verify the request is still active, then use the response as a relevant one-to-one reply."
                if status == "QUALIFIED"
                else "Recheck on the next radar run; do not contact unless the request becomes clearly relevant."
            ),
            "do_not_do": [
                "Do not mass-post or mass-message.",
                "Do not claim the requester agreed to buy.",
                "Do not request passwords, OTPs, API keys, or private credentials in public.",
            ],
        })

    leads.sort(key=lambda item: item["priority_score"], reverse=True)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "Deterministic buyer-request qualification and fixed-offer matching; no external AI.",
        "warning": "A public request is a lead signal, not consent or a sale. Human review is required before any outbound contact.",
        "summary": {
            "total": len(leads),
            "qualified": sum(x["status"] == "QUALIFIED" for x in leads),
            "watch": sum(x["status"] == "WATCH" for x in leads),
        },
        "lead_loop": "PUBLIC SIGNAL → QUALIFY → MATCH OFFER → RELEVANT ONE-TO-ONE RESPONSE → CHECKOUT → PAYMENT → INTAKE → DELIVERY",
        "leads": leads[:50],
    }
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)

    lines = [
        "# Customer Acquisition Queue", "",
        f"Generated: {output['generated_at']}", "",
        f"- Total signals: **{len(leads)}**",
        f"- Qualified: **{output['summary']['qualified']}**",
        f"- Watch: **{output['summary']['watch']}**", "",
        "> Public buyer signals are leads, not permission or proof of purchase. Review each lead before contacting. Never request private credentials in public.", "",
    ]
    for lead in leads[:25]:
        lines += [
            f"## {lead['status']} — {lead['matched_offer']}",
            f"- Priority: **{lead['priority_score']}**",
            f"- Request: {lead['title']}",
            f"- Source: {lead['url']}",
            f"- Price test: **Rp{lead['price_idr']:,}**".replace(",", "."),
            f"- Scope: {lead['scope']}",
            f"- Timebox: {lead['timebox']}",
            f"- Suggested response: {lead['response_draft']}",
            f"- Next action: {lead['next_action']}", "",
        ]
    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print(json.dumps(output["summary"], indent=2))

if __name__ == "__main__":
    main()

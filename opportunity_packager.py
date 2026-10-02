import json
from datetime import datetime, timezone

INPUT = "opportunity_report.json"
QUEUE = "revenue_queue.json"
CARDS = "validation_cards.md"

PRICE_HYPOTHESES = {
    "Implementation + integration service": {
        "price": "US$75-250 pilot",
        "deliverable": "One narrowly scoped integration, automation, or production setup with a working handoff.",
        "timebox": "1-2 days",
    },
    "Setup/production-readiness audit": {
        "price": "US$35-100 diagnostic",
        "deliverable": "A concrete setup/deployment/integration audit with prioritized fixes and implementation notes.",
        "timebox": "2-4 hours",
    },
    "Narrow convenience layer or workflow tool": {
        "price": "US$9-29 first paid version",
        "deliverable": "A focused workflow wrapper that removes one recurring friction point.",
        "timebox": "1-3 days",
    },
}

def license_allows_hosting(value):
    return value.startswith("PERMISSIVE:")

def choose_action(candidate):
    evidence = candidate["evidence"]
    pain = evidence["pain"]
    buyer = evidence["buyer_intent"]
    if pain >= 12 and buyer >= 5:
        return "Sell a pain-specific implementation pilot before building SaaS."
    if pain >= 8:
        return "Sell a paid diagnostic first; use delivery to learn the repeatable workflow."
    return "Create a tiny paid workflow wrapper only after confirming concrete user pain."

def build_item(candidate, rank):
    offer = candidate["monetizable_offer"]
    hypothesis = PRICE_HYPOTHESES[offer]
    license_note = (
        "Permissive license detected; review the repository license and notices before redistribution."
        if license_allows_hosting(candidate["license"])
        else "Commercial/redistribution rights require manual license review before hosted or derivative use."
    )
    return {
        "rank": rank,
        "repository": candidate["full_name"],
        "repository_url": candidate["url"],
        "score": candidate["score"],
        "offer": offer,
        "price_hypothesis": hypothesis["price"],
        "deliverable": hypothesis["deliverable"],
        "timebox": hypothesis["timebox"],
        "why_now": {
            "pain": candidate["evidence"]["pain"],
            "buyer_intent": candidate["evidence"]["buyer_intent"],
            "interest": candidate["evidence"]["interest"],
            "packaging_gap": candidate["evidence"]["packaging_gap"],
        },
        "action": choose_action(candidate),
        "validation": [
            "Turn the repository pain into one specific outcome, not a generic AI service.",
            "Create a one-page offer with a fixed deliverable and fixed pilot price.",
            "Test demand with legitimate, targeted conversations or communities; do not mass-spam.",
            "Only build reusable software after a real user agrees to pay or provides equivalent validation.",
        ],
        "license_note": license_note,
        "issue_evidence": candidate["evidence"].get("recent_issue_samples", [])[:3],
    }

def main():
    with open(INPUT, encoding="utf-8") as handle:
        report = json.load(handle)
    candidates = report.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidates available for packaging.")

    queue = [build_item(candidate, idx) for idx, candidate in enumerate(candidates[:7], start=1)]
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_generated_at": report.get("generated_at"),
        "method": "Convert ranked opportunity evidence into bounded revenue experiments.",
        "warning": "Prices are test hypotheses, not market facts or guaranteed revenue.",
        "queue": queue,
        "operating_rule": "Validate payment intent before investing in a larger product.",
    }
    with open(QUEUE, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)

    lines = [
        "# Revenue Validation Queue", "",
        f"Generated: {output['generated_at']}", "",
        "> Prices are test hypotheses, not guaranteed market prices. License status must be checked before reuse or redistribution.", "",
    ]
    for item in queue:
        lines.extend([
            f"## #{item['rank']} — {item['repository']}",
            f"- Score: **{item['score']}**",
            f"- Offer: **{item['offer']}**",
            f"- Pilot price hypothesis: **{item['price_hypothesis']}**",
            f"- Deliverable: {item['deliverable']}",
            f"- Timebox: {item['timebox']}",
            f"- Action: {item['action']}",
            f"- Evidence: pain={item['why_now']['pain']}, buyer_intent={item['why_now']['buyer_intent']}, interest={item['why_now']['interest']}, packaging_gap={item['why_now']['packaging_gap']}",
            f"- License: {item['license_note']}", "",
            "### Validation steps",
        ])
        lines.extend(f"{n}. {step}" for n, step in enumerate(item["validation"], start=1))
        lines.extend(["", "### Recent issue evidence"])
        lines.extend(
            f"- [{issue['title']}]({issue['url']})"
            for issue in item["issue_evidence"]
            if issue.get("title") and issue.get("url")
        )
        lines.append("")

    with open(CARDS, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print(json.dumps({
        "queue_size": len(queue),
        "top": [
            {"rank": x["rank"], "repository": x["repository"], "offer": x["offer"], "price_hypothesis": x["price_hypothesis"]}
            for x in queue[:5]
        ],
    }, indent=2))

if __name__ == "__main__":
    main()

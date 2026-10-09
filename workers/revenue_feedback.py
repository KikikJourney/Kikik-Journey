#!/usr/bin/env python3
"""Build a deterministic revenue/profit feedback policy from acquisition outcomes."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_EVENTS = Path("data/revenue_events.json")
DEFAULT_POLICY = Path("data/profit_policy.json")
DEFAULT_REPORT = Path("profit_report.json")


def _num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _event_id(event):
    explicit = str(event.get("event_id") or "").strip()
    if explicit:
        return explicit
    raw = json.dumps(event, sort_keys=True, ensure_ascii=False)
    return "auto-" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def deduplicate_events(events):
    seen = set()
    result = []
    for event in events:
        eid = _event_id(event)
        if eid in seen:
            continue
        seen.add(eid)
        item = dict(event)
        item["event_id"] = eid
        result.append(item)
    return result


def build_feedback(events):
    events = deduplicate_events(events)
    offers = {}
    sources = {}

    def bucket(store, key):
        if key not in store:
            store[key] = {
                "contacted": 0, "replied": 0, "qualified": 0, "paid": 0,
                "delivered": 0, "refunded": 0, "revenue_idr": 0.0,
                "refund_idr": 0.0, "cost_idr": 0.0,
            }
        return store[key]

    for event in events:
        et = str(event.get("event_type") or "").lower()
        offer = str(event.get("offer") or "unknown")
        source = str(event.get("source") or "unknown")
        amount = _num(event.get("amount_idr"))
        cost = _num(event.get("cost_idr"))
        for store, key in ((offers, offer), (sources, source)):
            b = bucket(store, key)
            b["cost_idr"] += cost
            if et == "contacted":
                b["contacted"] += 1
            elif et == "replied":
                b["replied"] += 1
            elif et == "qualified":
                b["qualified"] += 1
            elif et == "paid":
                b["paid"] += 1
                b["revenue_idr"] += amount
            elif et == "delivered":
                b["delivered"] += 1
            elif et == "refund":
                b["refunded"] += 1
                b["refund_idr"] += amount

    def finalize(bucket_data):
        for b in bucket_data.values():
            b["net_revenue_idr"] = round(b["revenue_idr"] - b["refund_idr"], 2)
            b["profit_idr"] = round(b["net_revenue_idr"] - b["cost_idr"], 2)
            contacted = b["contacted"]
            b["reply_rate"] = round(b["replied"] / contacted, 4) if contacted else 0.0
            b["qualified_rate"] = round(b["qualified"] / b["replied"], 4) if b["replied"] else 0.0
            b["paid_from_replied_rate"] = round(b["paid"] / b["replied"], 4) if b["replied"] else 0.0
            b["paid_from_qualified_rate"] = round(b["paid"] / b["qualified"], 4) if b["qualified"] else 0.0
            b["conversion_rate"] = round(b["paid"] / contacted, 4) if contacted else 0.0
            b["profit_per_contacted_idr"] = round(b["profit_idr"] / contacted, 2) if contacted else 0.0
        return bucket_data

    offers = finalize(offers)
    sources = finalize(sources)

    totals = {
        "events": len(events),
        "contacted": sum(x["contacted"] for x in offers.values()),
        "replies": sum(x["replied"] for x in offers.values()),
        "qualified": sum(x["qualified"] for x in offers.values()),
        "paid_orders": sum(x["paid"] for x in offers.values()),
        "delivered": sum(x["delivered"] for x in offers.values()),
        "refunded_orders": sum(x["refunded"] for x in offers.values()),
        "revenue_idr": round(sum(x["revenue_idr"] for x in offers.values()), 2),
        "refund_idr": round(sum(x["refund_idr"] for x in offers.values()), 2),
        "cost_idr": round(sum(x["cost_idr"] for x in offers.values()), 2),
    }
    totals["net_revenue_idr"] = round(totals["revenue_idr"] - totals["refund_idr"], 2)
    totals["profit_idr"] = round(totals["net_revenue_idr"] - totals["cost_idr"], 2)
    totals["reply_rate"] = round(totals["replies"] / totals["contacted"], 4) if totals["contacted"] else 0.0
    totals["qualified_rate"] = round(totals["qualified"] / totals["replies"], 4) if totals["replies"] else 0.0
    totals["paid_from_replied_rate"] = round(totals["paid_orders"] / totals["replies"], 4) if totals["replies"] else 0.0
    totals["paid_from_qualified_rate"] = round(totals["paid_orders"] / totals["qualified"], 4) if totals["qualified"] else 0.0
    totals["conversion_rate"] = round(totals["paid_orders"] / totals["contacted"], 4) if totals["contacted"] else 0.0

    min_contacts_for_feedback = 20

    def multiplier(b):
        # Keep new channels/offers neutral until there is enough real outreach
        # to avoid overreacting to tiny samples or contaminated legacy events.
        if b["contacted"] < min_contacts_for_feedback:
            return 1.0
        # Bayesian smoothing prevents a single sale from dominating the policy.
        smoothed = (b["paid"] + 1) / (b["contacted"] + 2)
        value = 0.70 + 0.80 * smoothed
        if b["profit_idr"] < 0:
            value -= 0.10
        return round(max(0.75, min(1.50, value)), 4)

    offer_multipliers = {k: multiplier(v) for k, v in offers.items()}
    source_multipliers = {k: multiplier(v) for k, v in sources.items()}

    policy = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "principle": "Outcome data changes prioritization; it never bypasses buyer-intent, compliance, Qwen, deduplication, or outreach caps.",
        "offer_multipliers": offer_multipliers,
        "source_multipliers": source_multipliers,
        "bounds": {"min": 0.75, "max": 1.50},
        "min_contacts_for_feedback": min_contacts_for_feedback,
    }
    return {
        "generated_at": policy["generated_at"],
        "totals": totals,
        "offers": offers,
        "sources": sources,
        "policy": policy,
    }


def load_json(path, default):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def ingest_outreach(report, events):
    for item in report.get("contacted_leads", []):
        events.append({
            "event_id": item["event_id"],
            "event_type": "contacted",
            "source": item.get("source", "unknown"),
            "offer": item.get("offer", "unknown"),
            "cost_idr": _num(item.get("cost_idr")),
            "occurred_at": item.get("occurred_at"),
        })
    return deduplicate_events(events)


def ingest_outreach_reports(reports, events):
    for report in reports:
        events = ingest_outreach(report, events)
    return deduplicate_events(events)


def ingest_event_file(payload, events):
    if not payload:
        return deduplicate_events(events)
    extra = payload.get("events", []) if isinstance(payload, dict) else payload
    return deduplicate_events(events + list(extra))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default=str(DEFAULT_EVENTS))
    parser.add_argument("--outreach-report", default="outreach_report.json")
    parser.add_argument("--extra-outreach-report", action="append", default=[])
    parser.add_argument("--event-file", default="")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    event_path = Path(args.events)
    events = load_json(event_path, [])
    if isinstance(events, dict):
        events = events.get("events", [])
    outreach_reports = [load_json(Path(args.outreach_report), {})]
    outreach_reports.extend(load_json(Path(path), {}) for path in args.extra_outreach_report)
    events = ingest_outreach_reports(outreach_reports, events)
    if args.event_file:
        events = ingest_event_file(load_json(Path(args.event_file), {}), events)

    result = build_feedback(events)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    event_path.write_text(json.dumps({"events": events}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.policy).parent.mkdir(parents=True, exist_ok=True)
    Path(args.policy).write_text(json.dumps(result["policy"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.report).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"totals": result["totals"], "policy": result["policy"]}, indent=2))


if __name__ == "__main__":
    main()

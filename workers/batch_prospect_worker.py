#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OFFERS = [
    {
        "name": "WooCommerce → Google Sheets Automation",
        "price_idr": 399000,
        "scope": "One WooCommerce store + one Google Sheet workflow + agreed fields.",
        "keywords": ["woocommerce", "google sheets", "order", "orders", "inventory", "stock"],
    },
    {
        "name": "WhatsApp → Google Sheets Mini Automation",
        "price_idr": 199000,
        "scope": "One message format + one Google Sheet workflow.",
        "keywords": ["whatsapp", "google sheets", "message", "attendance", "expense", "stock", "follow-up"],
    },
    {
        "name": "Workflow Rescue Pilot",
        "price_idr": 250000,
        "scope": "One workflow audit + implementation/prototype or documented automation path.",
        "keywords": ["automation", "automate", "workflow", "manual", "integration", "zapier", "make", "n8n"],
    },
]

INTENT_TERMS = [
    "need", "needs", "needed", "looking for", "want", "wanted", "help me",
    "help with", "hire", "hiring", "freelance", "contractor", "looking to",
    "build", "implement", "fix", "automate", "manual process",
    "request for proposal", "rfp", "quote", "budget", "paid", "hire", "hiring",
]

NON_BUYER_TERMS = [
    "roadmap", "market & tech review", "research report", "feed diff",
    "backlog", "program", "architecture", "research", "report only",
    "do not start", "discussion", "proposal for the project",
]


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def buyer_gate(request, offer):
    text = normalize(f"{request.get('title', '')} {request.get('evidence', request.get('text', ''))}")
    offer_hits = [k for k in offer["keywords"] if k in text]
    intent_hits = [k for k in INTENT_TERMS if k in text]
    non_buyer_hits = [k for k in NON_BUYER_TERMS if k in text]

    # A public issue is not a buyer merely because it contains generic
    # integration/automation vocabulary. Require both a concrete offer
    # match and an explicit request/implementation intent signal.
    has_offer_match = len(offer_hits) >= 1
    has_intent = len(intent_hits) >= 1
    strong_intent_hits = [k for k in intent_hits if k in {"need", "needs", "needed", "looking for", "want", "wanted", "help me", "help with", "hire", "hiring", "freelance", "contractor", "request for proposal", "rfp", "quote", "budget", "paid"}]
    research_only = len(non_buyer_hits) >= 1 and len(strong_intent_hits) == 0

    return {
        "allowed": has_offer_match and has_intent and not research_only,
        "offer_hits": offer_hits,
        "intent_hits": intent_hits,
        "non_buyer_hits": non_buyer_hits,
    }


def build_payload(request, offers):
    return {
        "buyer_request": {
            "title": request.get("title", ""),
            "url": request.get("url", ""),
            "text": request.get("evidence", request.get("text", "")),
        },
        "offers": offers,
    }


def select_requests(report, limit):
    """Use only actionable public-business leads for the business acquisition flow."""
    if "leads" in report:
        candidates = [
            lead for lead in report.get("leads", [])
            if lead.get("status") == "QUALIFIED" and lead.get("actionable") is True
            and lead.get("contact_email") and lead.get("website")
        ]
        return candidates[:max(0, limit)]
    return report.get("buyer_requests", [])[:max(0, limit)]


def guarded_result(result, request, offers):
    offer = next((x for x in offers if x["name"] == result.get("matched_offer")), None)
    if offer is None:
        # A model cannot invent a match; let the schema/validator handle it.
        return result

    gate = buyer_gate(request, offer)
    if result.get("decision") == "QUALIFIED" and not gate["allowed"]:
        result = dict(result)
        result["decision"] = "WATCH"
        result["priority"] = min(int(result.get("priority", 0)), 59)
        result["reason"] = (
            "Deterministic sales gate downgraded the model result: "
            "the public request lacks both a concrete offer match and explicit buyer/implementation intent."
        )
        result["next_validation"] = (
            "Wait for an explicit implementation, hiring, quote, budget, or concrete automation request "
            "before outbound contact."
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--worker", default=str(ROOT / "workers" / "prospect_worker.py"))
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    requests = select_requests(report, args.limit)
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for index, request in enumerate(requests, start=1):
            payload_path = tmp_path / f"input-{index}.json"
            result_path = tmp_path / f"result-{index}.json"
            payload_path.write_text(
                json.dumps(build_payload(request, DEFAULT_OFFERS), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            proc = subprocess.run(
                ["python", args.worker, "--input", str(payload_path), "--output", str(result_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=240,
            )
            if proc.returncode == 0 and result_path.exists():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                result = guarded_result(result, request, DEFAULT_OFFERS)
                result["source_request"] = {
                    "title": request.get("title"),
                    "url": request.get("url"),
                    "updated_at": request.get("updated_at"),
                }
                results.append(result)
            else:
                results.append({
                    "decision": "REJECT",
                    "confidence": 0,
                    "problem": "",
                    "buyer_type": "",
                    "matched_offer": None,
                    "priority": 0,
                    "evidence": [],
                    "missing_information": ["Worker execution failed"],
                    "reason": (proc.stderr or proc.stdout)[-500:],
                    "next_validation": "Retry on a later worker run.",
                    "source_request": {
                        "title": request.get("title"),
                        "url": request.get("url"),
                        "updated_at": request.get("updated_at"),
                    },
                })

    results.sort(key=lambda item: item.get("priority", 0), reverse=True)
    output = {
        "method": "Qwen3-1.7B second-pass qualification with deterministic buyer-intent gate.",
        "model": "ggml-org/Qwen3-1.7B-GGUF:Q4_K_M",
        "count": len(results),
        "qualified": sum(x.get("decision") == "QUALIFIED" for x in results),
        "watch": sum(x.get("decision") == "WATCH" for x in results),
        "reject": sum(x.get("decision") == "REJECT" for x in results),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("count", "qualified", "watch", "reject")}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OFFERS = [
    {
        "name": "WooCommerce → Google Sheets Automation",
        "price_idr": 399000,
        "scope": "One WooCommerce store + one Google Sheet workflow + agreed fields.",
    },
    {
        "name": "WhatsApp → Google Sheets Mini Automation",
        "price_idr": 199000,
        "scope": "One message format + one Google Sheet workflow.",
    },
    {
        "name": "Workflow Rescue Pilot",
        "price_idr": 250000,
        "scope": "One workflow audit + implementation/prototype or documented automation path.",
    },
]


def build_payload(request, offers):
    return {"buyer_request": {
        "title": request.get("title", ""),
        "url": request.get("url", ""),
        "text": request.get("evidence", request.get("text", "")),
    }, "offers": offers}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--worker", default=str(ROOT / "workers" / "prospect_worker.py"))
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    requests = report.get("buyer_requests", [])[: max(0, args.limit)]
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
        "method": "Qwen3-1.7B second-pass qualification over deterministic public buyer-request signals.",
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

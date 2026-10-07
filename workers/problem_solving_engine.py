#!/usr/bin/env python3
"""Kikik Journey Problem-Solving Engine v1."""
import argparse
import json
import re
from datetime import datetime, timezone

SENSITIVE = (
    "password", "passwd", "otp", "one-time password", "seed phrase",
    "private key", "secret key", "api key", "access token", "mnemonic",
)
ERROR_PATTERNS = (
    "error", "exception", "failed", "failure", "timeout", "unauthorized",
    "forbidden", "not found", "invalid", "denied", "doesn't work", "not working",
    "broken", "cannot", "can't", "unable", "stuck",
)
CATEGORY_RULES = {
    "payment": ("payment", "paid", "charge", "invoice", "refund", "usdt", "transaction"),
    "access_security": ("login", "sign in", "access", "locked", "permission", "unauthorized", "2fa", "security"),
    "automation": ("automation", "automate", "workflow", "zapier", "make", "n8n", "trigger", "action"),
    "ecommerce": ("woocommerce", "shopify", "store", "order", "inventory", "stock", "checkout"),
    "spreadsheet_data": ("google sheets", "spreadsheet", "csv", "excel", "row", "column", "data entry"),
    "whatsapp": ("whatsapp", "message", "chat", "follow-up", "followup"),
    "website": ("website", "web", "landing page", "domain", "dns", "ssl", "hosting"),
    "integration": ("api", "webhook", "integration", "sync", "connect", "import", "export"),
}
PLAYBOOKS = {
    "automation": {
        "hypotheses": [
            ("trigger_not_firing", ("trigger", "not firing", "doesn't trigger", "no trigger"), 0.88),
            ("field_mapping", ("field", "column", "mapping", "wrong data", "missing data"), 0.82),
            ("authentication_or_permission", ("unauthorized", "forbidden", "permission", "token", "credential"), 0.90),
            ("duplicate_or_loop", ("duplicate", "loop", "repeating", "multiple"), 0.78),
        ],
        "actions": [
            "Reproduce one failed run with the smallest non-sensitive example.",
            "Compare trigger event, mapped fields, and destination result.",
            "Check the automation execution/history log for the first failing step.",
        ],
        "verification": [
            "One controlled test reaches the intended trigger.",
            "Expected fields arrive once and in the correct destination.",
            "No duplicate or looped execution appears in the test window.",
        ],
    },
    "ecommerce": {
        "hypotheses": [
            ("order_sync", ("order", "sync", "google sheets"), 0.84),
            ("inventory_mapping", ("inventory", "stock", "sku"), 0.84),
            ("checkout_failure", ("checkout", "payment", "cart"), 0.82),
        ],
        "actions": [
            "Trace one representative order from creation to the destination record.",
            "Compare the source order ID/SKU with the destination row and mapped fields.",
            "Check the first failing integration step before changing configuration.",
        ],
        "verification": [
            "A test order completes the complete path.",
            "The destination record is created or updated exactly once.",
            "Order totals, identifiers, and status match the source.",
        ],
    },
    "spreadsheet_data": {
        "hypotheses": [
            ("mapping_mismatch", ("column", "field", "wrong", "missing"), 0.86),
            ("duplicate_write", ("duplicate", "twice", "multiple"), 0.84),
            ("format_mismatch", ("date", "number", "format", "formula"), 0.78),
        ],
        "actions": [
            "Use one sanitized sample row to reproduce the mismatch.",
            "Compare source fields with destination columns by name and type.",
            "Inspect the first transformation/write step that diverges.",
        ],
        "verification": [
            "The sample row lands in the intended columns.",
            "No duplicate row is created.",
            "Existing formulas and formatting remain intact.",
        ],
    },
    "whatsapp": {
        "hypotheses": [
            ("message_ingestion", ("message", "incoming", "webhook"), 0.82),
            ("routing_or_parsing", ("format", "parse", "keyword", "routing"), 0.80),
            ("followup_failure", ("follow-up", "followup", "reply", "reminder"), 0.80),
        ],
        "actions": [
            "Trace one sanitized message through receipt, parsing, routing, and destination.",
            "Confirm the expected message format and required fields.",
            "Inspect the first stage where the message stops progressing.",
        ],
        "verification": [
            "A test message is received and parsed correctly.",
            "The intended destination is updated once.",
            "The follow-up condition fires only when its rule is met.",
        ],
    },
    "integration": {
        "hypotheses": [
            ("endpoint_contract", ("api", "webhook", "payload", "schema"), 0.84),
            ("authentication", ("unauthorized", "forbidden", "token", "credential"), 0.90),
            ("rate_or_timeout", ("timeout", "rate limit", "429", "too many"), 0.86),
        ],
        "actions": [
            "Capture the exact non-secret request/response status and error message.",
            "Compare sent fields with the receiving endpoint's documented contract.",
            "Classify the failure as authentication, validation, rate limiting, or timeout.",
        ],
        "verification": [
            "A non-destructive test request is accepted.",
            "The response status and payload match the expected contract.",
            "No secrets are exposed in logs or customer messages.",
        ],
    },
    "access_security": {
        "hypotheses": [
            ("permission_or_identity", ("permission", "access", "locked", "unauthorized"), 0.92),
            ("configuration", ("login", "sign in", "2fa"), 0.76),
        ],
        "actions": [
            "Do not request or transmit passwords, OTPs, private keys, seed phrases, or full API secrets.",
            "Collect only visible error text, affected service, and non-sensitive context.",
            "Escalate account recovery, identity verification, or credential-reset actions.",
        ],
        "verification": [
            "The customer confirms access is restored through their normal secure flow.",
            "No secret credential was exposed to the system.",
        ],
    },
    "payment": {
        "hypotheses": [
            ("payment_state_mismatch", ("paid", "payment", "invoice", "transaction"), 0.84),
            ("network_or_token_mismatch", ("usdt", "network", "bep-20", "erc-20"), 0.90),
        ],
        "actions": [
            "Verify payment using transaction hash, exact amount, recipient, token contract, and network.",
            "Never treat a customer claim or screenshot as payment confirmation.",
        ],
        "verification": [
            "On-chain verification confirms expected token, recipient, amount, successful receipt, and required confirmations.",
        ],
    },
    "website": {
        "hypotheses": [
            ("configuration_or_dns", ("dns", "domain", "ssl"), 0.84),
            ("application_failure", ("500", "502", "503", "error", "timeout"), 0.84),
        ],
        "actions": [
            "Identify the exact URL and visible error/status code.",
            "Check the public endpoint before proposing a configuration change.",
            "Separate DNS/TLS failures from application-level failures.",
        ],
        "verification": [
            "The affected URL returns the intended status and content.",
            "TLS and domain behavior is correct where applicable.",
        ],
    },
}

def normalize(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def urls(text):
    return re.findall(r"https?://\S+", text or "", re.I)

def detect_category(text):
    t = normalize(text)
    scores = {name: sum(t.count(term) for term in terms) for name, terms in CATEGORY_RULES.items()}
    best = max(scores, key=scores.get)
    return (best if scores[best] else "unknown"), scores

def evidence(text):
    t = normalize(text)
    found = ["error_signal:" + p for p in ERROR_PATTERNS if p in t]
    found += ["public_url:" + u.rstrip(".,);") for u in urls(text)[:5]]
    return found

def solve(subject, text):
    combined = f"{subject}\n{text}".strip()
    normalized = normalize(combined)
    category, category_scores = detect_category(combined)
    playbook = PLAYBOOKS.get(category)
    sensitive_hits = [x for x in SENSITIVE if x in normalized]
    ev = evidence(combined)
    error_signals = [x for x in ev if x.startswith("error_signal:")]

    if playbook:
        hypotheses = []
        for name, terms, confidence in playbook["hypotheses"]:
            hits = [term for term in terms if term in normalized]
            if hits:
                hypotheses.append({"id": name, "confidence": confidence, "matched_signals": hits})
        if not hypotheses:
            hypotheses = [{"id": "insufficient_specific_evidence", "confidence": 0.35, "matched_signals": []}]
        hypotheses.sort(key=lambda x: x["confidence"], reverse=True)
        actions = playbook["actions"]
        verification = playbook["verification"]
    else:
        hypotheses = [{"id": "insufficient_specific_evidence", "confidence": 0.25, "matched_signals": []}]
        actions = [
            "Reconstruct expected outcome, actual outcome, exact error/symptom, and when it started.",
            "Use the smallest reproducible example and remove all credentials/secrets.",
        ]
        verification = ["Repeat the original scenario and confirm the expected outcome with observable evidence."]

    if sensitive_hits:
        status = "ESCALATE_SAFETY"
    elif category == "payment" and ("refund" in normalized or "charge" in normalized):
        status = "ESCALATE_PAYMENT"
    elif not error_signals and not ev:
        status = "NEEDS_EVIDENCE"
    elif hypotheses and hypotheses[0]["id"] != "insufficient_specific_evidence":
        status = "DIAGNOSIS_READY"
    else:
        status = "NEEDS_EVIDENCE"

    missing = []
    if not error_signals:
        missing.append("exact visible error or observed failure")
    if category == "unknown":
        missing.append("affected service or workflow name")
    if category in {"automation", "integration", "ecommerce", "spreadsheet_data", "whatsapp"}:
        missing.append("one sanitized example of expected vs actual result")

    case_id = "KJ-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    result = {
        "engine": "Kikik Journey Problem-Solving Engine v1",
        "case_id": case_id,
        "status": status,
        "category": category,
        "category_scores": category_scores,
        "evidence": ev[:20],
        "hypotheses": hypotheses[:3],
        "actions": actions,
        "verification": verification,
        "missing_information": missing[:4],
        "safety_flags": sensitive_hits,
        "policy": {
            "no_secret_collection": True,
            "no_unverified_completion_claims": True,
            "bounded_actions_only": True,
            "escalate_when_authority_or_evidence_is_insufficient": True,
        },
    }

    result["customer_message"] = build_customer_message(result)
    return result

def build_customer_message(result):
    status = result["status"]
    if status.startswith("ESCALATE"):
        return (
            f"Case {result['case_id']} is being handled with a safety boundary. "
            "I will not ask for passwords, OTPs, seed phrases, private keys, or full API secrets. "
            "Please provide only the affected service and exact non-sensitive error/message."
        )
    if status == "DIAGNOSIS_READY":
        top = result["hypotheses"][0]["id"].replace("_", " ")
        return (
            f"I've triaged case {result['case_id']}. The strongest current failure hypothesis is {top}. "
            "I will verify it against the smallest reproducible example before calling the problem resolved."
        )
    items = "; ".join(result["missing_information"][:3]) or "the exact expected and actual result"
    return (
        f"I've opened case {result['case_id']}. I need only the minimum evidence to diagnose it: "
        f"{items}. Do not send passwords, OTPs, private keys, seed phrases, or full API secrets."
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(open(args.input, encoding="utf-8").read())
    result = solve(payload.get("subject", ""), payload.get("text", ""))
    result["customer_message"] = build_customer_message(result)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"case_id": result["case_id"], "status": result["status"], "category": result["category"]}))

if __name__ == "__main__":
    main()

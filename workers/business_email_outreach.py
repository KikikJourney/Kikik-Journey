#!/usr/bin/env python3
"""Bounded one-to-one email outreach for qualified business prospects."""
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

MAX_PER_RUN = int(os.getenv("KJ_MAX_OUTREACH_PER_RUN", "3"))
AGENTMAIL_API = "https://api.agentmail.to/v0"
INBOX = os.getenv("AGENTMAIL_INBOX_EMAIL", "kikikjourney@agentmail.to")
TOKEN = os.getenv("AGENTMAIL_API_KEY")
MARKER = "Kikik Journey — fixed-scope automation pilot"

def api(path, method="GET", payload=None, query=None):
    if not TOKEN:
        raise RuntimeError("AGENTMAIL_API_KEY is required")
    url = AGENTMAIL_API + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + TOKEN,
        "User-Agent": "KikikJourney-BusinessOutreach/1.0",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}

def normalized_email(value):
    value = (value or "").strip().lower()
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", value, re.I)
    return match.group(0).lower() if match else ""

def already_contacted(email):
    try:
        payload = api(f"/inboxes/{urllib.parse.quote(INBOX, safe='')}/messages", query={"limit": 100, "to": email})
        for message in payload.get("messages", []):
            subject = (message.get("subject") or "").lower()
            if "kikik journey" in subject or "automation pilot" in subject:
                return True
        return False
    except urllib.error.HTTPError:
        return False

def eligible(lead):
    return (
        lead.get("status") == "QUALIFIED"
        and lead.get("source") == "public_business_web_signal"
        and bool(normalized_email(lead.get("contact_email")))
        and bool(lead.get("matched_offer"))
        and bool(lead.get("checkout_path"))
        and bool(lead.get("website"))
    )

def email_body(lead):
    offer = lead["matched_offer"]
    price = f"Rp{lead['price_idr']:,}".replace(",", ".")
    return (
        f"Hi,\n\n"
        f"I came across your public note about {lead.get('title') or 'your workflow'} and noticed the automation/integration pain around it.\n\n"
        f"I run a small fixed-scope {offer} pilot for {price}. "
        f"The scope is: {lead['scope']}\n\n"
        f"If this is still a live problem, you can review the exact scope here:\n"
        f"https://kikikjourney.github.io/Kikik-Journey/{lead['checkout_path']}\n\n"
        "No call is required to start. If it is not relevant, just reply STOP and I will not follow up. "
        "Please do not send passwords, OTPs, API keys, seed phrases, or other private credentials by email.\n\n"
        "Kikik Journey"
    )

def send_one(lead):
    email = normalized_email(lead.get("contact_email"))
    if not email:
        return "ineligible"
    if already_contacted(email):
        return "already_contacted"
    payload = {
        "to": [email],
        "subject": f"{MARKER}: {lead.get('matched_offer')}",
        "text": email_body(lead),
        "labels": ["kj-outreach"],
    }
    api(f"/inboxes/{urllib.parse.quote(INBOX, safe='')}/messages/send", "POST", payload)
    return "contacted"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leads", default="customer_leads.json")
    parser.add_argument("--qwen", default="worker_prospect_queue.json")
    parser.add_argument("--report", default="outreach_report.json")
    args = parser.parse_args()

    lead_data = json.loads(open(args.leads, encoding="utf-8").read())
    qwen_data = json.loads(open(args.qwen, encoding="utf-8").read()) if os.path.exists(args.qwen) else {"results": []}
    qualified_urls = {
        ((x.get("source_request") or {}).get("url") or "").rstrip("/")
        for x in qwen_data.get("results", [])
        if x.get("decision") == "QUALIFIED"
    }

    leads = []
    for lead in lead_data.get("leads", []):
        url = (lead.get("url") or "").rstrip("/")
        if eligible(lead) and (not qualified_urls or url in qualified_urls):
            leads.append(lead)

    results = {}
    contacted = 0
    for lead in leads:
        if contacted >= MAX_PER_RUN:
            break
        try:
            status = send_one(lead)
        except urllib.error.HTTPError as exc:
            status = f"http_{exc.code}"
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
        results[status] = results.get(status, 0) + 1
        if status == "contacted":
            contacted += 1

    report = {
        "eligible_after_qwen": len(leads),
        "contacted": contacted,
        "max_per_run": MAX_PER_RUN,
        "results": results,
        "qwen_gate_enabled": bool(qwen_data.get("results")),
        "policy": "Business-first public-web prospects only; public business email; one-to-one; deduplicated by AgentMail recipient history; capped per run; STOP honored; no credential collection.",
    }
    open(args.report, "w", encoding="utf-8").write(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

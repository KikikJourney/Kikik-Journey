#!/usr/bin/env python3
"""Strict, activity-aware GitHub buyer-request outreach.

Fail-closed policy:
- only explicit buyer requests
- target repository must be active (recent push)
- opportunity + probability score must clear thresholds
- one comment per issue, deduplicated by marker
- external repositories require an explicitly supplied write token
- CTA always points to Central Checkout with source attribution
"""
import argparse
import json
import os
import re
import urllib.request
from urllib.parse import urlencode
from datetime import datetime, timezone

MAX_PER_RUN = int(os.getenv("KJ_GITHUB_MAX_OUTREACH_PER_RUN", "3"))
MIN_SCORE = float(os.getenv("KJ_GITHUB_MIN_OUTREACH_SCORE", "80"))
ACTIVE_DAYS = int(os.getenv("KJ_GITHUB_ACTIVE_DAYS", "90"))
CHECKOUT = os.getenv(
    "CHECKOUT_BASE_URL",
    "https://kikikjourney.github.io/Kikik-Journey/sales/manual_order.html",
)
TOKEN = os.getenv("AGENT_OUTREACH_API")
MARKER = "<!-- kikik-journey-github-outreach:v2 -->"
INTENT = ("need help", "need someone", "looking for", "need a developer", "hire",
          "hiring", "paid help", "who can build", "who can fix", "help me automate",
          "need this built", "need this fixed", "seeking", "can someone", "recommend a developer")
PAIN = ("bug", "broken", "error", "failing", "manual", "automation", "workflow",
        "integration", "inventory", "orders", "deployment", "ci", "api", "slow", "maintenance")

BUYER_QUERIES = (
    '"looking for" automation',
    '"need help" automation',
    '"need a developer" automation',
    '"looking for" "google sheets" integration',
    '"woocommerce" "google sheets" automation',
    '"whatsapp" automation "google sheets"',
)
MAX_DISCOVERY = int(os.getenv("KJ_GITHUB_MAX_DISCOVERY_CANDIDATES", "25"))


def api(url, method="GET", payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "KikikJourney-GitHub-Outreach/2.0",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    elif method != "GET":
        raise RuntimeError("AGENT_OUTREACH_API is required for GitHub write operations")
    data = json.dumps(payload).encode() if payload is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}



def search_buyer_requests():
    """Discover GitHub buyer requests independently of the public-web/email channel."""
    found = {}
    for query in BUYER_QUERIES:
        data = api("https://api.github.com/search/issues?" + urlencode({
            "q": query + " type:issue is:open",
            "sort": "updated",
            "order": "desc",
            "per_page": 15,
        }))
        for item in data.get("items", []):
            if item.get("pull_request"):
                continue
            url = item.get("html_url")
            if url:
                found[url] = item

    candidates = []
    for item in found.values():
        title = item.get("title") or ""
        body = item.get("body") or ""
        low = f"{title} {body}".lower()
        intent_hits = sum(x in low for x in INTENT)
        pain_hits = sum(x in low for x in PAIN)
        if intent_hits < 1 or pain_hits < 1:
            continue
        offer = match_offer(low)
        candidates.append({
            "status": "QUALIFIED",
            "source": "public_buyer_request",
            "url": item.get("html_url"),
            "title": title,
            "evidence": f"{title} {body}"[:3000],
            "matched_offer": offer,
            "checkout_path": checkout_path_for_offer(offer),
            "priority_score": min(100, 45 + intent_hits * 12 + pain_hits * 5),
            "commercial_intent": intent_hits,
            "updated_at": item.get("updated_at"),
        })
    candidates.sort(key=lambda x: x["priority_score"], reverse=True)
    return candidates[:MAX_DISCOVERY]


def match_offer(text):
    low = (text or "").lower()
    if "woocommerce" in low and "google sheets" in low:
        return "WooCommerce → Google Sheets Automation"
    if "whatsapp" in low and "google sheets" in low:
        return "WhatsApp → Google Sheets Mini Automation"
    return "Workflow Rescue Pilot"


def checkout_path_for_offer(offer):
    return {
        "WooCommerce → Google Sheets Automation": "sales/manual_order.html?offer=woocommerce",
        "WhatsApp → Google Sheets Mini Automation": "sales/manual_order.html?offer=whatsapp",
        "Workflow Rescue Pilot": "sales/manual_order.html?offer=workflow",
    }[offer]


def issue_ref(url):
    m = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)",
                     (url or "").split("#", 1)[0].rstrip("/"))
    return (m.group(1), int(m.group(2))) if m else None


def activity(repo):
    data = api(f"https://api.github.com/repos/{repo}")
    if data.get("archived") or data.get("disabled"):
        return False, 0, "archived_or_disabled"
    pushed = data.get("pushed_at")
    if not pushed:
        return False, 0, "no_recent_push_timestamp"
    pushed_at = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - pushed_at).days
    return age <= ACTIVE_DAYS, age, "active" if age <= ACTIVE_DAYS else "inactive"


def score(lead, repo_age):
    text = f"{lead.get('title','')} {lead.get('evidence','')}".lower()
    intent_hits = sum(x in text for x in INTENT)
    pain_hits = sum(x in text for x in PAIN)
    opportunity = min(100.0, float(lead.get("priority_score", lead.get("score", 0)))
                      + min(20, intent_hits * 5) + min(15, pain_hits * 3))
    probability = min(100.0, 45 + intent_hits * 12 + pain_hits * 5
                      + (10 if lead.get("matched_offer") else 0)
                      + (10 if repo_age <= 30 else 0))
    final = round(opportunity * 0.55 + probability * 0.45, 2)
    return round(opportunity, 2), round(probability, 2), final


def checkout_url(lead, repo, issue):
    path = lead.get("checkout_path") or "sales/manual_order.html"
    if path.startswith("http"):
        base = path
    else:
        base = "https://kikikjourney.github.io/Kikik-Journey/" + path
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}source=github-outreach&repo={repo}&issue={issue}"


def already_contacted(repo, number):
    comments = api(f"https://api.github.com/repos/{repo}/issues/{number}/comments?per_page=100").get("comments", [])
    return any(MARKER in (c.get("body") or "") for c in comments)


def eligible(lead):
    return (lead.get("status") == "QUALIFIED"
            and lead.get("source") == "public_buyer_request"
            and issue_ref(lead.get("url")) is not None
            and bool(lead.get("matched_offer"))
            and bool(lead.get("checkout_path")))


def comment_body(lead, checkout):
    return (f"{MARKER}\n"
            f"Your request about **{lead.get('title') or 'this project'}** appears to be a focused fit for "
            f"**{lead['matched_offer']}**.\n\n"
            f"If the issue is still active, details and the fixed-scope order path are here: {checkout}\n\n"
            "If it is no longer needed, no action is required. Please do not post passwords, API keys, "
            "tokens, OTPs, or other private credentials here.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--leads", default="customer_leads.json")
    p.add_argument("--qwen", default=None)
    p.add_argument("--report", default="github_outreach_report.json")
    args = p.parse_args()
    supplied_leads = json.load(open(args.leads, encoding="utf-8")).get("leads", []) if os.path.exists(args.leads) else []
    discovered = search_buyer_requests()
    # GitHub outreach owns GitHub discovery. Public-web/email leads are never used
    # as a substitute for GitHub buyer-request discovery.
    leads = discovered
    if supplied_leads:
        github_supplied = [x for x in supplied_leads if x.get("source") == "public_buyer_request"]
        by_url = {x.get("url", "").rstrip("/"): x for x in github_supplied if x.get("url")}
        for lead in discovered:
            by_url.setdefault(lead["url"].rstrip("/"), lead)
        leads = list(by_url.values())

    report = {"eligible": 0, "contacted": 0, "skipped": {}, "attempts": [],
              "max_per_run": MAX_PER_RUN, "min_score": MIN_SCORE,
              "active_days": ACTIVE_DAYS, "policy": "GitHub-only buyer-request discovery; strict active-repository + opportunity/probability gate; one-to-one; deduplicated; fail-closed"}
    for lead in leads:
        if report["contacted"] >= MAX_PER_RUN:
            break
        if not eligible(lead):
            report["skipped"]["ineligible"] = report["skipped"].get("ineligible", 0) + 1
            continue
        repo, issue = issue_ref(lead["url"])
        try:
            active, age, activity_status = activity(repo)
            opportunity, probability, final = score(lead, age)
            attempt = {"repo": repo, "issue": issue, "activity_days_since_push": age,
                       "activity_status": activity_status, "opportunity_score": opportunity,
                       "probability_score": probability, "final_score": final}
            if not active:
                report["skipped"]["inactive_repository"] = report["skipped"].get("inactive_repository", 0) + 1
                attempt["status"] = "skipped_inactive"
            elif final < MIN_SCORE:
                report["skipped"]["low_score"] = report["skipped"].get("low_score", 0) + 1
                attempt["status"] = "skipped_low_score"
            elif already_contacted(repo, issue):
                report["skipped"]["already_contacted"] = report["skipped"].get("already_contacted", 0) + 1
                attempt["status"] = "already_contacted"
            elif not TOKEN:
                report["skipped"]["missing_write_token"] = report["skipped"].get("missing_write_token", 0) + 1
                attempt["status"] = "skipped_missing_write_token"
            else:
                api(f"https://api.github.com/repos/{repo}/issues/{issue}/comments", "POST",
                    {"body": comment_body(lead, checkout_url(lead, repo, issue))})
                report["contacted"] += 1
                attempt["status"] = "contacted"
            report["eligible"] += 1
            report["attempts"].append(attempt)
        except Exception as exc:
            report["skipped"]["error"] = report["skipped"].get("error", 0) + 1
            report["attempts"].append({"repo": repo, "issue": issue, "status": f"error:{type(exc).__name__}"})
    with open(args.report, "w", encoding="utf-8") as h:
        json.dump(report, h, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

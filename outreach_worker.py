import base64
import json
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen

REPO = os.getenv("GITHUB_REPOSITORY", "KikikJourney/Kikik-Journey")
INPUT = "customer_leads.json"
STATE_PATH = "runtime/outreach-state.json"
STATE_BRANCH = os.getenv("STATE_BRANCH", "bot-state")
MAX_PER_DAY = int(os.getenv("MAX_PUBLIC_OUTREACH_PER_DAY", "3"))
MIN_SCORE = float(os.getenv("MIN_OUTREACH_SCORE", "70"))
MAX_AGE_DAYS = int(os.getenv("MAX_OUTREACH_AGE_DAYS", "14"))
MARKER = "<!-- kikikjourney-revenue-engine:outreach:v1 -->"
CHECKOUT_BASE = os.getenv("CHECKOUT_BASE_URL", "https://kikikjourney.github.io/Kikik-Journey/sales/checkout.html")

def gh_request(token, method, path, payload=None):
    url = f"https://api.github.com{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "KikikJourney-Revenue-Engine/1.0",
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)

def parse_issue(url):
    match = re.search(r"github\.com/([^/]+/[^/]+)/issues/(\d+)", url or "")
    return (match.group(1), int(match.group(2))) if match else (None, None)

def eligible(lead):
    if lead.get("status") != "QUALIFIED" or float(lead.get("priority_score", 0)) < MIN_SCORE:
        return False
    updated = lead.get("updated_at")
    if not updated:
        return False
    try:
        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - dt > timedelta(days=MAX_AGE_DAYS):
            return False
    except ValueError:
        return False
    text = f"{lead.get('title','')} {lead.get('evidence','')}".lower()
    blocked = ["do not contact", "no solicitation", "no sales", "don't contact", "spam"]
    return not any(x in text for x in blocked)

def build_comment(lead):
    offer = lead["matched_offer"]
    if "WooCommerce" in offer:
        offer_param = "woocommerce"
    elif "WhatsApp" in offer:
        offer_param = "whatsapp"
    else:
        offer_param = "workflow"
    checkout = f"{CHECKOUT_BASE}?offer={offer_param}"
    price = f"Rp{lead['price_idr']:,}".replace(",", ".")
    return (
        f"{MARKER}\n"
        "Hi — I found your active request and it looks directly relevant to a fixed-scope implementation I offer.\n\n"
        f"**Relevant offer:** {offer}\n"
        f"**Scope:** {lead['scope']}\n"
        f"**Pilot price:** {price}\n"
        f"**Checkout:** {checkout}\n\n"
        "If the request is still active, the page has the exact scope and direct payment options. "
        "No credentials are needed in the public thread."
    )

def main():
    token = os.environ["GITHUB_TOKEN"]
    with open(INPUT, encoding="utf-8") as handle:
        data = json.load(handle)

    state_payload = gh_request(token, "GET", f"/repos/{REPO}/contents/{STATE_PATH}?ref={STATE_BRANCH}")
    state = json.loads(base64.b64decode(state_payload["content"]).decode())
    sha = state_payload["sha"]

    today = datetime.now(timezone.utc).date().isoformat()
    sent_today = int(state.get("sent_today", 0)) if state.get("date") == today else 0
    sent = []

    for lead in sorted(data.get("leads", []), key=lambda x: float(x.get("priority_score", 0)), reverse=True):
        if sent_today >= MAX_PER_DAY or not eligible(lead):
            continue
        repo, issue_number = parse_issue(lead.get("url"))
        if not repo or not issue_number:
            continue
        comments = gh_request(token, "GET", f"/repos/{repo}/issues/{issue_number}/comments?per_page=100")
        if any(MARKER in (comment.get("body") or "") for comment in comments):
            continue
        gh_request(token, "POST", f"/repos/{repo}/issues/{issue_number}/comments", {"body": build_comment(lead)})
        sent_today += 1
        sent.append({"url": lead["url"], "offer": lead["matched_offer"], "score": lead["priority_score"]})

    state.update({
        "version": 1,
        "date": today,
        "sent_today": sent_today,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
    })
    content = base64.b64encode((json.dumps(state, indent=2) + "\n").encode()).decode()
    gh_request(token, "PUT", f"/repos/{REPO}/contents/{STATE_PATH}", {
        "message": "chore: update revenue engine outreach state",
        "content": content,
        "branch": STATE_BRANCH,
        "sha": sha,
    })
    print(json.dumps({"sent": len(sent), "sent_today": sent_today, "max_per_day": MAX_PER_DAY, "items": sent}, indent=2))

if __name__ == "__main__":
    main()

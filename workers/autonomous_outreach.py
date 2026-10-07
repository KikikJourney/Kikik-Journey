import json
import os
import re
import urllib.parse
import urllib.request

MAX_PER_RUN = int(os.getenv("KJ_MAX_OUTREACH_PER_RUN", "3"))
MARKER = "<!-- kikik-journey-autonomous-outreach:v1 -->"
CHECKOUT = os.getenv(
    "CHECKOUT_BASE_URL",
    "https://kikikjourney.github.io/Kikik-Journey/sales/checkout.html",
)
REPO = os.getenv("GITHUB_REPOSITORY", "KikikJourney/Kikik-Journey")
TOKEN = os.getenv("GITHUB_TOKEN")


def api(url, method="GET", payload=None):
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "KikikJourney-AutonomousAcquisition/1.0",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode()
        return json.loads(raw) if raw else {}


def issue_ref(url):
    match = re.fullmatch(
        r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)",
        (url or "").split("#", 1)[0].rstrip("/"),
    )
    return (match.group(1), int(match.group(2))) if match else None


def eligible(lead):
    return (
        lead.get("status") == "QUALIFIED"
        and lead.get("source") == "public_buyer_request"
        and issue_ref(lead.get("url")) is not None
        and bool(lead.get("matched_offer"))
        and bool(lead.get("checkout_path"))
    )


def comment_body(lead):
    title = lead.get("title") or "your request"
    offer = lead.get("matched_offer")
    checkout = CHECKOUT + "?" + lead["checkout_path"].split("?", 1)[1] if "?" in lead["checkout_path"] else CHECKOUT
    return (
        f"{MARKER}\n"
        f"Your request about **{title}** looks like a concrete fit for a narrow "
        f"**{offer}** implementation.\n\n"
        "If the request is still active, I can offer a fixed-scope pilot rather than a broad consulting engagement. "
        f"Details and checkout: {checkout}\n\n"
        "If it is no longer needed, no action is required. Please do not post passwords, OTPs, API keys, "
        "seed phrases, or other private credentials here."
    )


def already_contacted(repo, number):
    url = f"https://api.github.com/repos/{repo}/issues/{number}/comments?per_page=100"
    comments = api(url).get("comments", [])
    return any(MARKER in (item.get("body") or "") for item in comments)


def send_one(lead):
    parsed = issue_ref(lead.get("url"))
    if not parsed:
        return "ineligible"
    repo, number = parsed
    if repo.lower() != REPO.lower():
        return "foreign_repo"
    if already_contacted(repo, number):
        return "already_contacted"
    api(
        f"https://api.github.com/repos/{repo}/issues/{number}/comments",
        "POST",
        {"body": comment_body(lead)},
    )
    return "contacted"


def main():
    with open("customer_leads.json", encoding="utf-8") as handle:
        data = json.load(handle)
    leads = [lead for lead in data.get("leads", []) if eligible(lead)]
    results = {}
    contacted = 0
    for lead in leads:
        if contacted >= MAX_PER_RUN:
            break
        try:
            status = send_one(lead)
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
        results[status] = results.get(status, 0) + 1
        if status == "contacted":
            contacted += 1
    print(json.dumps({
        "eligible": len(leads),
        "contacted": contacted,
        "max_per_run": MAX_PER_RUN,
        "results": results,
        "policy": "Only explicit public buyer-request issues; one-to-one comments; deduplicated by marker; capped per run.",
    }, indent=2))


if __name__ == "__main__":
    main()

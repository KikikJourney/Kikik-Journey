import base64
import json
import os
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import ai_router

API = "https://api.github.com"
USER_AGENT = "KikikJourney-AI-Opportunity-Radar/1.3"
TOKEN = os.getenv("GITHUB_TOKEN")
LOOKBACK_DAYS = 45
AI_ENRICH_LIMIT = 7

QUERIES = [
    "topic:artificial-intelligence pushed:>2026-08-18 stars:>30",
    "topic:llm pushed:>2026-08-18 stars:>30",
    "topic:automation pushed:>2026-08-18 stars:>20",
    "topic:ai-agents pushed:>2026-08-18 stars:>20",
]

PAIN = {
    "difficult": 3, "hard": 3, "broken": 4, "error": 2, "issue": 2,
    "setup": 2, "install": 1, "deploy": 3, "deployment": 3,
    "integration": 2, "documentation": 2, "slow": 2,
    "expensive": 3, "alternative": 2, "feature request": 3,
    "manual": 3, "workflow": 2, "production": 2, "self-host": 2,
}

BUYER_SIGNALS = {
    "api": 2, "saas": 3, "dashboard": 2, "enterprise": 3,
    "team": 2, "business": 3, "automation": 2, "agent": 1,
    "integration": 2, "workflow": 2, "monitoring": 2,
}

def api(path, params=None, attempts=4):
    url = API + path
    if params:
        url += "?" + urlencode(params)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN

    for attempt in range(attempts):
        try:
            request = Request(url, headers=headers, method="GET")
            with urlopen(request, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in {403, 429, 500, 502, 503, 504} or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(min(delay, 30))
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)

def keyword_score(text, weights):
    text = (text or "").lower()
    return sum(weight for phrase, weight in weights.items() if phrase in text)

def license_state(repo):
    spdx = (repo.get("license") or {}).get("spdx")
    if spdx in {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}:
        return "PERMISSIVE:" + spdx
    return "REVIEW_REQUIRED:" + str(spdx or "UNKNOWN")

def fetch_readme(full_name):
    try:
        payload = api(f"/repos/{full_name}/readme")
        encoded = payload.get("content", "").replace("\n", "")
        return base64.b64decode(encoded).decode("utf-8", "ignore")[:16000]
    except Exception as exc:
        print(f"README unavailable for {full_name}: {type(exc).__name__}")
        return ""

def fetch_issues(full_name):
    try:
        return api(
            f"/repos/{full_name}/issues",
            {"state": "open", "per_page": 10, "sort": "updated", "direction": "desc"},
        )
    except Exception as exc:
        print(f"Issues unavailable for {full_name}: {type(exc).__name__}")
        return []

def build_candidate(repo, readme, issues):
    issue_text = "\n".join(
        f"{item.get('title', '')} {item.get('body') or ''}" for item in issues
        if "pull_request" not in item
    )
    evidence_text = (readme + "\n" + issue_text).lower()

    pain = min(25, keyword_score(evidence_text, PAIN) + min(10, len(issues)))
    buyer = min(15, keyword_score(evidence_text, BUYER_SIGNALS))
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    interest = min(28, (stars ** 0.5) * 1.7 + (forks ** 0.5) * 1.1)
    packaging = 14 if not repo.get("homepage") else 7
    activity = 8
    license_bonus = 8 if license_state(repo).startswith("PERMISSIVE:") else 0
    score = round(min(100, interest + pain + buyer + packaging + activity + license_bonus), 2)

    offer = (
        "Implementation + integration service"
        if buyer >= 5
        else "Setup/production-readiness audit"
        if pain >= 8
        else "Narrow convenience layer or workflow tool"
    )
    validation = (
        "Build a one-page offer around the top 3 recurring pain signals and test with targeted outreach."
        if pain >= 8
        else "Inspect issues/docs for one concrete friction point before building."
    )

    return {
        "full_name": repo["full_name"],
        "url": repo.get("html_url"),
        "description": repo.get("description"),
        "stars": stars,
        "forks": forks,
        "open_issues": repo.get("open_issues_count", 0),
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "updated_at": repo.get("pushed_at"),
        "license": license_state(repo),
        "homepage": repo.get("homepage"),
        "score": score,
        "evidence": {
            "interest": round(interest, 2),
            "pain": pain,
            "buyer_intent": buyer,
            "packaging_gap": packaging,
            "activity": activity,
            "license": license_state(repo),
            "recent_issue_samples": [
                {
                    "title": i.get("title"),
                    "url": i.get("html_url"),
                }
                for i in issues[:5] if "pull_request" not in i
            ],
        },
        "monetizable_offer": offer,
        "validation_action": validation,
        "business_hypotheses": [
            "Paid implementation/integration",
            "Audit/diagnostic service",
            "Hosted convenience layer where licensing permits",
        ],
    }

def enrich_with_ai(candidates):
    """Optionally enrich top candidates through 9Router; never blocks deterministic radar."""
    if not ai_router.configured():
        return {
            "status": "not_configured",
            "model": None,
            "enriched_count": 0,
            "items": [],
        }

    items = []
    failures = []
    for candidate in candidates[:AI_ENRICH_LIMIT]:
        prompt = {
            "repository": candidate["full_name"],
            "description": candidate.get("description"),
            "score": candidate["score"],
            "offer": candidate["monetizable_offer"],
            "validation_action": candidate["validation_action"],
            "evidence": candidate["evidence"],
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a commercial opportunity analyst. Enrich evidence; do not invent demand, "
                    "customers, revenue, or facts. Return ONLY valid JSON with keys: likely_buyer, "
                    "painful_workflow, paid_offer, validation_hypothesis, next_action, confidence. "
                    "Keep each string concise. confidence must be one of: low, medium, high."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False),
            },
        ]
        try:
            raw = ai_router.chat(messages, temperature=0.1, timeout=45)
            parsed = json.loads(raw)
            required = {
                "likely_buyer", "painful_workflow", "paid_offer",
                "validation_hypothesis", "next_action", "confidence",
            }
            if not required.issubset(parsed):
                raise ValueError("AI response missing required keys")
            parsed["repository"] = candidate["full_name"]
            items.append(parsed)
        except Exception as exc:
            failures.append({
                "repository": candidate["full_name"],
                "error": type(exc).__name__,
            })

    status = "enriched" if items else "configured_but_unavailable"
    return {
        "status": status,
        "model": os.getenv("AI_ROUTER_MODEL") or os.getenv("9ROUTER_MODEL") or "default",
        "enriched_count": len(items),
        "failed_count": len(failures),
        "items": items,
        "failures": failures,
    }

def main():
    repos = {}
    failures = []

    for query in QUERIES:
        try:
            payload = api("/search/repositories", {
                "q": query, "sort": "updated", "order": "desc", "per_page": 20
            })
            for repo in payload.get("items", []):
                repos[repo["full_name"]] = repo
        except Exception as exc:
            failures.append({"stage": "search", "query": query, "error": f"{type(exc).__name__}: {exc}"})
            print(f"Search failed: {query}: {exc}")

    if not repos:
        raise RuntimeError("GitHub repository search returned no candidates")

    candidates = []
    for name, repo in repos.items():
        readme = fetch_readme(name)
        issues = fetch_issues(name)
        candidates.append(build_candidate(repo, readme, issues))
        time.sleep(0.05)

    candidates.sort(key=lambda item: item["score"], reverse=True)
    top = candidates[:20]
    ai_enrichment = enrich_with_ai(top)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "GitHub metadata + README + recent issue evidence + deterministic monetization heuristics",
        "lookback_days": LOOKBACK_DAYS,
        "warning": "Prioritization and validation hypotheses only; not proof of demand or revenue.",
        "search_failures": failures,
        "candidate_count": len(candidates),
        "candidates": top,
        "ai_enrichment": ai_enrichment,
        "next_action": "Validate the top candidates with a concrete offer before building a larger product.",
    }
    with open("opportunity_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(json.dumps({
        "candidates": len(candidates),
        "search_failures": len(failures),
        "ai_enrichment": {
            "status": ai_enrichment["status"],
            "enriched_count": ai_enrichment["enriched_count"],
        },
        "top": [
            {
                "repo": item["full_name"],
                "score": item["score"],
                "offer": item["monetizable_offer"],
                "pain": item["evidence"]["pain"],
                "buyer_intent": item["evidence"]["buyer_intent"],
            }
            for item in top[:10]
        ],
    }, indent=2))

if __name__ == "__main__":
    main()

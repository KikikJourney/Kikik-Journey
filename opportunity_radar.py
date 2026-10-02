import base64
import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.github.com"
USER_AGENT = "KikikJourney-AI-Opportunity-Radar/1.1"
TOKEN = os.getenv("GITHUB_TOKEN")

QUERIES = [
    "topic:artificial-intelligence pushed:>2026-09-01 stars:>50",
    "topic:llm pushed:>2026-09-01 stars:>50",
    "topic:automation pushed:>2026-09-01 stars:>50",
    "topic:ai-agents pushed:>2026-09-01 stars:>30",
]

PAIN = {
    "difficult": 3, "hard": 3, "broken": 4, "error": 2,
    "setup": 2, "install": 1, "deploy": 3, "deployment": 3,
    "integration": 2, "documentation": 2, "slow": 2,
    "expensive": 3, "alternative": 2, "feature request": 3,
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
            retryable = exc.code in {403, 429, 500, 502, 503, 504}
            if not retryable or attempt == attempts - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            time.sleep(min(delay, 30))
        except (URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def pain_score(text):
    text = (text or "").lower()
    return sum(weight for phrase, weight in PAIN.items() if phrase in text)


def license_state(repo):
    spdx = (repo.get("license") or {}).get("spdx")
    if spdx in {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"}:
        return "PERMISSIVE:" + spdx
    return "REVIEW_REQUIRED:" + str(spdx or "UNKNOWN")


def score(repo, readme):
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    issues = repo.get("open_issues_count", 0)
    interest = min(30, (stars ** 0.5) * 1.8) + min(12, (forks ** 0.5) * 1.2)
    return round(min(
        100,
        interest
        + min(25, issues * 0.7 + pain_score(readme))
        + (15 if not repo.get("homepage") else 7)
        + 10
        + (8 if license_state(repo).startswith("PERMISSIVE:") else 0),
    ), 2)


def fetch_readme(full_name):
    try:
        payload = api(f"/repos/{full_name}/readme")
        encoded = payload.get("content", "").replace("\n", "")
        return base64.b64decode(encoded).decode("utf-8", "ignore")[:12000]
    except Exception as exc:
        print(f"README unavailable for {full_name}: {type(exc).__name__}")
        return ""


def main():
    repos = {}
    failures = []

    for query in QUERIES:
        try:
            payload = api(
                "/search/repositories",
                {"q": query, "sort": "updated", "order": "desc", "per_page": 20},
            )
            for repo in payload.get("items", []):
                repos[repo["full_name"]] = repo
        except Exception as exc:
            failures.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})
            print(f"Search failed: {query}: {exc}")

    if not repos:
        raise RuntimeError("GitHub repository search returned no candidates")

    candidates = []
    for name, repo in repos.items():
        readme = fetch_readme(name)
        candidates.append({
            "full_name": name,
            "url": repo.get("html_url"),
            "description": repo.get("description"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "language": repo.get("language"),
            "topics": repo.get("topics", []),
            "updated_at": repo.get("pushed_at"),
            "license": license_state(repo),
            "homepage": repo.get("homepage"),
            "score": score(repo, readme),
            "evidence": {
                "interest": "stars/forks",
                "pain": "README keyword signals + open issues",
                "packaging_gap": "homepage presence/absence heuristic",
                "activity": "recent pushed_at from GitHub search",
                "license": "repository license metadata",
            },
            "business_hypotheses": [
                "Paid implementation/integration service",
                "Audit or diagnostic around setup/workflow pain",
                "Hosted convenience layer where licensing permits",
            ],
        })
        time.sleep(0.05)

    candidates.sort(key=lambda item: item["score"], reverse=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "public GitHub metadata + README heuristics",
        "lookback_anchor": (datetime.now(timezone.utc) - timedelta(days=31)).date().isoformat(),
        "warning": "Prioritization only; not proof of demand or revenue.",
        "search_failures": failures,
        "candidate_count": len(candidates),
        "candidates": candidates[:30],
    }
    with open("opportunity_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(json.dumps({
        "candidates": len(candidates),
        "search_failures": len(failures),
        "top": [(item["full_name"], item["score"]) for item in candidates[:10]],
    }, indent=2))


if __name__ == "__main__":
    main()

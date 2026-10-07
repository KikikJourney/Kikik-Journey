#!/usr/bin/env python3
"""Business-buyer discovery from public request signals plus public business pages."""
import html
import json
import os
import re
import time
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LIMIT = int(os.getenv("KJ_BUSINESS_DISCOVERY_LIMIT", "12"))
SEARCH_TIMEOUT = int(os.getenv("KJ_DISCOVERY_TIMEOUT_SECONDS", "8"))
UA = "KikikJourney-BusinessProspector/2.1"

QUERIES = [
    '"need help" automation "google sheets" ecommerce -github -fiverr -upwork',
    '"looking for" automation "google sheets" business -github -fiverr',
    '"need a developer" woocommerce automation -github -fiverr',
    '"looking for" "whatsapp automation" business -github -fiverr',
    '"need help" "zapier" automation business -github -fiverr',
    '"help me automate" business workflow -github -fiverr',
    'site:community.make.com/t/ "I need help" "Google Sheets" automation',
    'site:community.make.com/t/ "looking for" automation "Google Sheets"',
    'site:community.n8n.io/t/ "help needed" automation WhatsApp',
    'site:community.n8n.io/t/ "looking for" automation workflow',
    'site:community.zapier.com "looking to use" automation Sheets',
    'site:forum.pabbly.com "need assistance" automation "Google Sheets"',
]

SEARCH_ENGINE_DOMAINS = ("google.com", "bing.com", "duckduckgo.com", "r.jina.ai")
BLOCKED = (
    "github.com", "reddit.com", "linkedin.com", "facebook.com",
    "instagram.com", "x.com", "twitter.com", "youtube.com",
    "tiktok.com", "upwork.com", "fiverr.com", "freelancer.com",
    "indeed.com", "glassdoor.com", "quora.com",
)
WEBMAIL = (
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com",
    "hotmail.com", "live.com", "icloud.com", "proton.me",
    "protonmail.com",
)
BUSINESS = (
    "our business", "my business", "our store", "my store", "ecommerce",
    "e-commerce", "customers", "orders", "inventory", "appointments",
    "bookings", "clients", "leads", "sales", "shop", "store", "agency",
    "restaurant", "clinic", "company", "business",
)
PAIN = (
    "manual", "manually", "tedious", "time-consuming", "hours every",
    "copying", "spreadsheet", "google sheets", "workflow", "repetitive",
    "bottleneck", "integration", "automation", "automate", "slow",
    "error-prone", "data entry", "copy paste",
)
INTENT = (
    "need help", "looking for", "need a developer", "need someone",
    "hire", "hiring", "paid help", "who can build", "who can fix",
    "help me automate", "looking to automate", "want to automate",
    "need this built", "need this fixed", "seeking", "can someone",
    "anyone able", "recommend a developer",
)
OFFERS = {
    "WooCommerce → Google Sheets Automation": (
        "woocommerce", "google sheets", "orders", "inventory", "stock",
    ),
    "WhatsApp → Google Sheets Mini Automation": (
        "whatsapp", "google sheets", "message", "attendance", "expense",
        "stock", "follow-up",
    ),
    "Workflow Rescue Pilot": (
        "automation", "automate", "workflow", "manual", "integration",
        "zapier", "make", "n8n",
    ),
}


def get(url, timeout=SEARCH_TIMEOUT):
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/plain,text/html"})
    with urlopen(req, timeout=timeout) as response:
        return (
            response.read(1200000).decode(
                response.headers.get_content_charset() or "utf-8", "ignore"
            ),
            response.geturl(),
        )


def read(url):
    for attempt in range(2):
        try:
            body, _ = get("https://r.jina.ai/" + url)
            return body, url
        except (HTTPError, URLError, TimeoutError, UnicodeError, ValueError):
            if attempt == 0:
                time.sleep(0.3)
    return "", url


def search(query):
    found = []
    seen = set()
    q = quote_plus(query.replace("site:community.make.com/t/", "").replace("site:community.n8n.io/t/", "").replace("site:community.zapier.com", "").replace("site:forum.pabbly.com", ""))
    targets = []
    if "make.com" in query:
        targets.append("https://community.make.com/search?q=" + q)
    if "n8n.io" in query:
        targets.append("https://community.n8n.io/search?q=" + q)
    if "zapier.com" in query:
        targets.append("https://community.zapier.com/search?q=" + q)
    if "pabbly.com" in query:
        targets.append("https://forum.pabbly.com/search/?q=" + q)
    targets.extend([
        "https://www.google.com/search?q=" + quote_plus(query) + "&num=10&hl=en",
        "https://www.bing.com/search?q=" + quote_plus(query) + "&count=10",
    ])
    for target in targets:
        body, _ = read(target)
        links = re.findall(r'\[([^\]]+)\]\((https?://[^\s\)"]+)', body)
        links += [(u, u) for u in re.findall(r'https?://[^\s<>\]\)"']+', body)]
        for title, url in links:
            clean_url = html.unescape(url).rstrip(".,);")
            parsed = urlparse(clean_url)
            domain = parsed.netloc.lower().removeprefix("www.")
            path = parsed.path.lower()
            if (
                not domain
                or domain in SEARCH_ENGINE_DOMAINS
                or path.startswith("/search")
                or "skip to" in (title or "").lower()
                or any(
                domain == blocked or domain.endswith("." + blocked)
                for blocked in BLOCKED
            )
            ):
                continue
            if clean_url in seen:
                continue
            seen.add(clean_url)
            found.append({"title": html.unescape(title), "url": clean_url})
            if len(found) >= 8:
                return found
    return found


def emails(text):
    return sorted(set(re.findall(
        r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
        text or "",
    )))


def is_business_email(email, site):
    domain = email.rsplit("@", 1)[-1].lower()
    site_domain = urlparse(site).netloc.lower().removeprefix("www.")
    return domain not in WEBMAIL and (
        domain == site_domain
        or site_domain.endswith("." + domain)
        or domain.endswith("." + site_domain)
    )


def classify(item, body):
    title = (item.get("title") or "").lower()
    context = (body + " " + title).lower()
    business_hits = sum(k in context for k in BUSINESS)
    pain_hits = sum(k in context for k in PAIN)
    intent_hits = sum(k in context for k in INTENT)
    ranked = sorted(
        (sum(k in context for k in keywords), name)
        for name, keywords in OFFERS.items()
    )
    offer_hits, offer = ranked[-1]
    windows = [
        part.strip().lower()
        for part in re.split(r"[\n.!?]+", body + " " + item.get("title", ""))
        if part.strip()
    ]
    request_context = any(
        any(term in window for term in INTENT)
        and (
            any(term in window for term in PAIN)
            or any(term in window for term in OFFERS[offer])
        )
        for window in windows
    )
    return context, business_hits, pain_hits, intent_hits, offer_hits, offer, request_context


def inspect(item, query):
    body, final = read(item["url"])
    if not body:
        return None

    _, business_hits, pain_hits, intent_hits, offer_hits, offer, request_context = classify(item, body)
    if (
        not request_context
        or intent_hits < 1
        or pain_hits < 1
        or offer_hits < 1
        or business_hits < 1
    ):
        return None

    found = [e for e in emails(body) if is_business_email(e, final)]
    contact_url = ""
    contact_links = re.findall(
        r"\[[^\]]*(?:contact|about|support|sales)[^\]]*\]\((https?://[^)]+)\)",
        body,
        re.I,
    )
    for candidate in contact_links[:2]:
        candidate_url = urljoin(final, candidate)
        contact_url = contact_url or candidate_url
        contact_body, contact_final = read(candidate_url)
        found.extend(
            e for e in emails(contact_body) if is_business_email(e, contact_final)
        )

    found = sorted(set(found))
    return {
        "source": "public_business_buyer_signal",
        "source_type": "public_business_buyer_signal",
        "title": item.get("title") or urlparse(final).netloc,
        "website": final,
        "contact_email": found[0] if found else "",
        "contact_url": contact_url,
        "score": min(
            100,
            24 + business_hits * 7 + pain_hits * 8 + intent_hits * 16
            + offer_hits * 8 + (18 if found else 0),
        ),
        "matched_offer": offer,
        "commercial_intent": intent_hits,
        "business_signal": business_hits,
        "pain_signal": pain_hits,
        "evidence": re.sub(r"\s+", " ", body).strip()[:2200],
        "contact_channel": "public_business_email" if found else (
            "public_contact_page" if contact_url else "unresolved"
        ),
        "reachability": "direct_email" if found else (
            "contact_form_or_contact_page" if contact_url else "unresolved"
        ),
        "discovery_query": query,
    }


def main():
    prospects = []
    domains = set()
    for query in QUERIES:
        for item in search(query):
            domain = urlparse(item["url"]).netloc.lower().removeprefix("www.")
            if domain in domains:
                continue
            domains.add(domain)
            hit = inspect(item, query)
            if hit:
                prospects.append(hit)
            if len(prospects) >= LIMIT:
                break
        if len(prospects) >= LIMIT:
            break

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "Public buyer/request signals via Jina Reader plus public business contact enrichment; no credentials.",
        "count": len(prospects),
        "prospects": prospects[:LIMIT],
        "warning": "Public business signals are lead signals, not consent or sales. Outreach remains one-to-one, bounded and opt-out aware.",
    }
    with open("business_prospects.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"business_prospects": len(prospects)}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Business-buyer discovery from public request signals plus public business pages.

The discovery layer deliberately separates:
1) buyer/request evidence (a person or business explicitly seeking help), and
2) reachability enrichment (public business website/email/contact page).

A normal business website is not treated as a buyer merely because it mentions
automation. GitHub is not used as the primary market source.
"""
import html
import json
import os
import re
import time
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LIMIT = int(os.getenv("KJ_BUSINESS_DISCOVERY_LIMIT", "12"))
SEARCH_TIMEOUT = int(os.getenv("KJ_DISCOVERY_TIMEOUT_SECONDS", "12"))
UA = "KikikJourney-BusinessProspector/2.0"

# Queries intentionally target explicit commercial/request language. The query
# itself is never counted as evidence; only the returned page/title is scored.
QUERIES = [
    '"need help" automation "google sheets" -github -fiverr -upwork',
    '"looking for" automation "google sheets" ecommerce -github -fiverr',
    '"need a developer" woocommerce automation -github -fiverr',
    '"looking for" "whatsapp automation" business -github -fiverr',
    '"need help" "zapier" "small business" -github -fiverr',
    '"need help" "make.com" automation business -github -fiverr',
    '"seeking" automation workflow ecommerce -github -fiverr',
    '"hire" automation "google sheets" business -github -fiverr',
    '"help me automate" business workflow -github -fiverr',
    '"manual process" "need help" automation business -github -fiverr',
]

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
            return get("https://r.jina.ai/" + url)
        except (HTTPError, URLError, TimeoutError, UnicodeError):
            if attempt == 0:
                time.sleep(0.4)
    return "", url


def search(q):
    found, seen = [], set()
    targets = [
        "https://www.google.com/search?q=" + quote_plus(q) + "&num=10&hl=en",
        "https://www.bing.com/search?q=" + quote_plus(q) + "&count=10",
        "https://html.duckduckgo.com/html/?q=" + quote_plus(q),
    ]
    for target in targets:
        body, _ = read(target)
        links = re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", body)
        links += [(u, u) for u in re.findall(r'https?://[^\s<>\]\)"]+', body)]
        for title, url in links:
            u = html.unescape(url).rstrip(".,);")
            domain = urlparse(u).netloc.lower().removeprefix("www.")
            if not domain or any(
                domain == blocked or domain.endswith("." + blocked)
                for blocked in BLOCKED
            ):
                continue
            if u in seen:
                continue
            seen.add(u)
            found.append({"title": html.unescape(title), "url": u})
            if len(found) >= 8:
                return found
    return found


def emails(text):
    return sorted(
        set(
            re.findall(
                r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
                text or "",
            )
        )
    )


def is_business_email(email, site):
    domain = email.rsplit("@", 1)[-1].lower()
    site_domain = urlparse(site).netloc.lower().removeprefix("www.")
    return domain not in WEBMAIL and (
        domain == site_domain
        or site_domain.endswith("." + domain)
        or domain.endswith("." + site_domain)
    )


def classify(item, body):
    context = (body + " " + item.get("title", "")).lower()
    business_hits = sum(k in context for k in BUSINESS)
    pain_hits = sum(k in context for k in PAIN)
    intent_hits = sum(k in context for k in INTENT)
    ranked = sorted(
        (sum(k in context for k in keywords), name)
        for name, keywords in OFFERS.items()
    )
    offer_hits, offer = ranked[-1]
    return context, business_hits, pain_hits, intent_hits, offer_hits, offer


def inspect(item, query):
    body, final = read(item["url"])
    if not body:
        return None

    context, business_hits, pain_hits, intent_hits, offer_hits, offer = classify(
        item, body
    )

    # A buyer/request signal requires explicit intent in returned content/title.
    # Search-query language is deliberately excluded to prevent false positives.
    if intent_hits < 1 or pain_hits < 1 or offer_hits < 1:
        return None
    if business_hits < 1:
        return None

    found = [email for email in emails(body) if is_business_email(email, final)]
    contact_url = ""
    contact_links = re.findall(
        r"\[[^\]]*(?:contact|about|support|sales)[^\]]*\]\((https?://[^)]+)\)",
        body,
        re.I,
    )
    for candidate in contact_links[:3]:
        candidate_url = urljoin(final, candidate)
        contact_url = contact_url or candidate_url
        contact_body, contact_final = read(candidate_url)
        found.extend(
            email
            for email in emails(contact_body)
            if is_business_email(email, contact_final)
        )

    found = sorted(set(found))
    score = min(
        100,
        24
        + business_hits * 7
        + pain_hits * 8
        + intent_hits * 16
        + offer_hits * 8
        + (18 if found else 0),
    )
    evidence = re.sub(r"\s+", " ", body).strip()[:2200]

    return {
        "source": "public_business_buyer_signal",
        "source_type": "public_business_buyer_signal",
        "title": item.get("title") or urlparse(final).netloc,
        "website": final,
        "contact_email": found[0] if found else "",
        "contact_url": contact_url,
        "score": score,
        "matched_offer": offer,
        "commercial_intent": intent_hits,
        "business_signal": business_hits,
        "pain_signal": pain_hits,
        "evidence": evidence,
        "contact_channel": "public_business_email" if found else (
            "public_contact_page" if contact_url else "unresolved"
        ),
        "reachability": "direct_email" if found else (
            "contact_form_or_contact_page" if contact_url else "unresolved"
        ),
        "discovery_query": query,
    }


def main():
    prospects, domains = [], set()
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
        "method": (
            "Public buyer/request signals via Jina Reader, followed by public "
            "business contact enrichment; no credentials."
        ),
        "count": len(prospects),
        "prospects": prospects[:LIMIT],
        "warning": (
            "Public business signals are lead signals, not consent or sales. "
            "Outreach remains one-to-one, bounded and opt-out aware."
        ),
    }
    with open("business_prospects.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"business_prospects": len(prospects)}))


if __name__ == "__main__":
    main()

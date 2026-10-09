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
from http.client import InvalidURL

LIMIT = int(os.getenv("KJ_BUSINESS_DISCOVERY_LIMIT", "12"))
SEARCH_TIMEOUT = int(os.getenv("KJ_DISCOVERY_TIMEOUT_SECONDS", "8"))
UA = "KikikJourney-BusinessProspector/2.2"
MAX_PER_DOMAIN = int(os.getenv("KJ_MAX_PROSPECTS_PER_DOMAIN", "4"))
MAX_CANDIDATES_PER_QUERY = int(os.getenv("KJ_MAX_CANDIDATES_PER_QUERY", "24"))

DIAGNOSTICS = {
    "queries_attempted": 0,
    "search_targets_attempted": 0,
    "search_targets_with_content": 0,
    "search_targets_failed_or_empty": 0,
    "links_seen": 0,
    "content_pages_read": 0,
    "content_pages_empty": 0,
    "pages_rejected_no_buyer_evidence": 0,
    "reject_no_request_context": 0,
    "reject_no_intent": 0,
    "reject_no_pain": 0,
    "reject_no_offer_fit": 0,
    "reject_no_business_context": 0,
    "pages_with_buyer_evidence": 0,
    "pages_with_relevance_evidence": 0,
    "pages_watch_only": 0,
    "direct_business_emails_found": 0,
    "per_query": [],
}

QUERIES = [
    # Local business pain hypotheses; search public web sources, not only GitHub.
    '"UMKM" "pencatatan stok" manual WhatsApp usaha',
    '"usaha kecil" "Google Sheets" pesanan otomatis',
    '"toko online" "rekap pesanan" manual WhatsApp',
    '"UMKM" "pembukuan" "input data" otomatis',
    'site:community.make.com/t/ "WhatsApp Cloud API" "Google Sheets" "Hire Help"',
    'site:community.make.com/t/ "Make freelancer needed for project" "happy to pay"',
    'site:community.make.com/t/ "PDF invoice" "Google Sheets" "Gmail" "Make.com"',
    'site:community.make.com/t/ "WordPress" "Brevo" "Make.com" "Hire Help"',
    '"need help" automation "google sheets" ecommerce -github -fiverr -upwork',
    '"looking for" automation "google sheets" business -github -fiverr',
    '"need a developer" woocommerce automation -github -fiverr',
    'site:community.make.com/t/ "I need help" "Google Sheets" automation',
    'site:community.n8n.io/t/ "help needed" automation WhatsApp',
    'site:community.zapier.com "looking to use" automation Sheets',
    '"looking for" "whatsapp automation" business -github -fiverr',
    '"help me automate" business workflow -github -fiverr',
    'site:community.make.com/t/ "looking for" automation "Google Sheets"',
    'site:community.n8n.io/t/ "looking for" automation workflow',
    'site:forum.pabbly.com "need assistance" automation "Google Sheets"',
    '"need help" WooCommerce orders inventory "contact us" -plugin -agency -zapier -n8n',
    '"looking for" WooCommerce automation store orders -plugin -agency -fiverr -upwork',
    '"need someone" "Google Sheets" ecommerce "contact" -zapier -n8n -fiverr',
    '"looking for" workflow automation small business "contact us" -zapier -n8n',
    '"need help" WhatsApp automation business "contact us" -agency -fiverr',
    '"manual" orders inventory WooCommerce "contact us" -plugin -agency',
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
    "restaurant", "clinic", "company", "business", "usaha", "toko", "pesanan", "stok", "pelanggan", "penjualan", "pembukuan", "umkm",
)
PAIN = (
    "manual", "manually", "tedious", "time-consuming", "hours every",
    "copying", "spreadsheet", "google sheets", "workflow", "repetitive",
    "bottleneck", "integration", "automation", "automate", "slow",
    "error-prone", "data entry", "copy paste",
)
# Strong buyer-request phrases only. Generic words such as "hire", "help",
# "looking for", and "seeking" also occur in forum rules and navigation copy.
INTENT = (
    "need help", "looking for a developer", "looking for a freelancer",
    "looking for someone to", "need a developer", "need someone to",
    "hire a developer", "hiring a developer", "looking to hire",
    "freelancer wanted", "contractor wanted", "paid help", "paid project",
    "who can build", "who can fix", "help me automate",
    "looking to automate", "want to automate", "need this built",
    "need this fixed", "seeking a freelancer", "seeking a contractor",
    "recommend a developer", "request a quote", "pay someone to",
    "willing to pay",
    "butuh bantuan", "perlu bantuan", "mencari developer", "mencari freelancer",
    "membutuhkan developer", "membutuhkan freelancer", "sedang mencari",
    "tolong buat", "tolong bantu", "ada yang bisa", "ingin mengotomatisasi",
    "ingin otomatisasi", "jasa otomatisasi", "minta bantuan", "mencari jasa",
)

GENERIC_TITLES = {
    "log in", "login", "sign in", "sign up", "how do i...?",
    "how do i", "get help", "get support", "contact us", "contact",
    "support", "help center", "community", "home", "search",
    "topics", "categories", "latest", "popular",
}
GENERIC_PATH_PARTS = (
    "/login", "/ssoproxy/", "/search", "/categories", "/category/",
    "/tags/", "/tag/", "/latest", "/popular", "/contact-us", "/contact",
)


def is_candidate_page(item):
    """Reject navigation/category pages before expensive content inspection."""
    title = re.sub(r"\s+", " ", (item.get("title") or "").lower()).strip(" .")
    if title in GENERIC_TITLES or any(title.startswith(x + " |") for x in GENERIC_TITLES):
        return False
    url = normalize_url(item.get("url"))
    if not url:
        return False
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.lower().rstrip("/")
    if not path or any(part in path for part in GENERIC_PATH_PARTS):
        return False

    # Community home/category URLs often contain generic help/navigation text.
    # Only inspect individual, identifiable discussion topics from these hosts.
    if domain == "community.zapier.com":
        sections = {"how-do-i-3", "troubleshooting-99", "code-webhooks-52"}
        segments = [part for part in path.split("/") if part]
        return bool(
            len(segments) == 2
            and segments[0] in sections
            and re.fullmatch(r"[^/]+-\d+", segments[1])
        )
    if domain in {"community.make.com", "community.n8n.io"}:
        return bool(re.fullmatch(r"/t/[^/]+/\d+", path))
    if domain == "forum.pabbly.com":
        return bool(re.fullmatch(r"/threads/[^/]+\.\d+", path))
    return True
OFFERS = {
    "WooCommerce → Google Sheets Automation": (
        "woocommerce", "google sheets", "orders", "inventory", "stock", "pesanan", "rekap pesanan", "pencatatan stok",
    ),
    "WhatsApp → Google Sheets Mini Automation": (
        "whatsapp", "google sheets", "message", "attendance", "expense",
        "stock", "follow-up", "pesanan", "rekap", "pencatatan",
    ),
    "Workflow Rescue Pilot": (
        "automation", "automate", "workflow", "manual", "integration",
        "zapier", "make", "n8n", "otomatisasi", "input data", "pencatatan", "rekap",
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


def normalize_url(url):
    clean = html.unescape(str(url or "")).strip()
    if not clean:
        return ""
    # Markdown search results may include a quoted link title after the URL.
    match = re.match(r'^(https?://\S+)', clean)
    if not match:
        return ""
    clean = match.group(1)
    parsed = urlparse(clean)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return parsed._replace(fragment="").geturl().rstrip(".,);")


def read(url):
    clean_url = normalize_url(url)
    if not clean_url:
        return "", url
    for attempt in range(2):
        try:
            domain = urlparse(clean_url).netloc.lower().removeprefix("www.")
            if domain in {"google.com", "bing.com", "html.duckduckgo.com"}:
                body, final = get(clean_url)
            else:
                body, final = get("https://r.jina.ai/" + clean_url)
            return body, clean_url
        except (HTTPError, URLError, TimeoutError, UnicodeError, ValueError, InvalidURL):
            if attempt == 0:
                time.sleep(0.3)
    return "", url


def search(query):
    found = []
    seen = set()
    q = quote_plus(query)
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
        DIAGNOSTICS["search_targets_attempted"] += 1
        body, _ = read(target)
        if body:
            DIAGNOSTICS["search_targets_with_content"] += 1
        else:
            DIAGNOSTICS["search_targets_failed_or_empty"] += 1
        links = re.findall(r'\[([^\]]+)\]\((https?://[^\s\)"]+)', body)
        links += [(u, u) for u in re.findall(r"https?://[^\s<>\]\)\"']+", body)]
        DIAGNOSTICS["links_seen"] += len(links)
        for title, url in links:
            clean_url = normalize_url(url)
            if not clean_url:
                continue
            parsed = urlparse(clean_url)
            domain = parsed.netloc.lower().removeprefix("www.")
            path = parsed.path.lower()
            if (
                not domain
                or domain == "r.jina.ai"
                or domain in SEARCH_ENGINE_DOMAINS
                or path.startswith("/search")
                or (
                    domain in {"zapier.com", "make.com", "n8n.io", "pabbly.com"}
                    and not domain.startswith("community.")
                    and not domain.startswith("forum.")
                )
                or (
                    domain in {
                        "community.zapier.com",
                        "community.make.com",
                        "community.n8n.io",
                        "forum.pabbly.com",
                    }
                    and path in {"", "/"}
                )
                or "skip to" in (title or "").lower()
                or any(
                domain == blocked or domain.endswith("." + blocked)
                for blocked in BLOCKED
            )
            ):
                continue
            parsed_url = urlparse(clean_url)
            canonical = parsed_url._replace(query="", fragment="").geturl().rstrip("/")
            candidate = {"title": html.unescape(title), "url": canonical}
            if not is_candidate_page(candidate):
                continue
            if canonical.lower() in seen:
                continue
            seen.add(canonical.lower())
            found.append(candidate)
            if len(found) >= MAX_CANDIDATES_PER_QUERY:
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
    # Score only the original post's opening, not the entire thread. Replies can
    # contain other people's sales pitches and must not manufacture buyer intent.
    primary_context = (title + " " + (body or "")[:1800]).lower()
    business_hits = sum(k in primary_context for k in BUSINESS)
    pain_hits = sum(k in primary_context for k in PAIN)
    intent_hits = sum(k in primary_context for k in INTENT)
    ranked = sorted(
        (sum(k in primary_context for k in keywords), name)
        for name, keywords in OFFERS.items()
    )
    offer_hits, offer = ranked[-1]
    windows = [
        part.strip().lower()
        for part in re.split(r"[\\n.!?]+", (body or "")[:1800] + " " + item.get("title", ""))
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
    return primary_context, business_hits, pain_hits, intent_hits, offer_hits, offer, request_context

def inspect(item, query):
    if not is_candidate_page(item):
        return None
    body, final = read(item["url"])
    DIAGNOSTICS["content_pages_read"] += 1
    if not body:
        DIAGNOSTICS["content_pages_empty"] += 1
        return None

    _, business_hits, pain_hits, intent_hits, offer_hits, offer, request_context = classify(item, body)
    rejection_reasons = {
        "reject_no_request_context": not request_context,
        "reject_no_intent": intent_hits < 1,
        "reject_no_pain": pain_hits < 2,
        "reject_no_offer_fit": offer_hits < 1,
        "reject_no_business_context": business_hits < 1,
    }
    # Keep strongly relevant pages in a WATCH queue even when explicit purchase
    # intent is absent. WATCH records must never enter autonomous outreach.
    relevance_gate = (business_hits >= 1 and pain_hits >= 2 and offer_hits >= 1) or (intent_hits >= 1 and request_context and pain_hits >= 1 and offer_hits >= 1)
    if not relevance_gate:
        DIAGNOSTICS["pages_rejected_no_buyer_evidence"] += 1
        for key, rejected in rejection_reasons.items():
            if rejected:
                DIAGNOSTICS[key] += 1
        return None
    DIAGNOSTICS["pages_with_relevance_evidence"] += 1
    qualified = intent_hits >= 1 and request_context
    if qualified:
        DIAGNOSTICS["pages_with_buyer_evidence"] += 1
    else:
        DIAGNOSTICS["pages_watch_only"] += 1

    found = [e for e in emails(body) if is_business_email(e, final)]
    contact_url = ""
    contact_links = re.findall(
        r"\[[^\]]*(?:contact|about|support|sales)[^\]]*\]\((https?://[^)]+)\)",
        body,
        re.I,
    )
    for candidate in contact_links[:2]:
        candidate_url = normalize_url(urljoin(final, candidate))
        if not candidate_url:
            continue
        contact_url = contact_url or candidate_url
        contact_body, contact_final = read(candidate_url)
        found.extend(
            e for e in emails(contact_body) if is_business_email(e, contact_final)
        )

    found = sorted(set(found))
    if found:
        DIAGNOSTICS["direct_business_emails_found"] += 1
    return {
        "source": "public_business_web_signal",
        "source_type": "public_business_web_signal",
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
        "status": "QUALIFIED" if qualified else "WATCH",
        "actionable": bool(found) and qualified and pain_hits >= 2 and offer_hits >= 1,
        "actionability_reason": (
            "direct public business email + explicit intent + pain + offer fit"
            if found and qualified and pain_hits >= 2 and offer_hits >= 1
            else "watch-only or missing direct email / explicit intent / pain / offer evidence"
        ),
        "discovery_query": query,
    }


def main():
    prospects = []
    seen_urls = set()
    # MAX_PER_DOMAIN limits accepted prospects, not pages inspected. Previously,
    # rejected pages consumed the domain quota and could hide later valid requests
    # from the same community or business site.
    domain_counts = {}
    inspected_domain_counts = {}
    max_inspections_per_domain = int(os.getenv("KJ_MAX_INSPECTIONS_PER_DOMAIN", "36"))
    max_queries = int(os.getenv("KJ_MAX_DISCOVERY_QUERIES", "10"))
    for query in QUERIES[:max_queries]:
        DIAGNOSTICS["queries_attempted"] += 1
        candidates = search(query)
        inspected = 0
        matched = 0
        skipped_duplicate_or_capped = 0
        for item in candidates:
            domain = urlparse(item["url"]).netloc.lower().removeprefix("www.")
            url_key = item["url"].rstrip("/").lower()
            if (
                url_key in seen_urls
                or domain_counts.get(domain, 0) >= MAX_PER_DOMAIN
                or inspected_domain_counts.get(domain, 0) >= max_inspections_per_domain
            ):
                skipped_duplicate_or_capped += 1
                continue
            seen_urls.add(url_key)
            inspected_domain_counts[domain] = inspected_domain_counts.get(domain, 0) + 1
            inspected += 1
            hit = inspect(item, query)
            if hit:
                prospects.append(hit)
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                matched += 1
            if len(prospects) >= LIMIT:
                break
        DIAGNOSTICS["per_query"].append({
            "query": query,
            "search_candidates": len(candidates),
            "unique_pages_inspected": inspected,
            "skipped_duplicate_or_domain_capped": skipped_duplicate_or_capped,
            "matching_prospects": matched,
        })
        if len(prospects) >= LIMIT:
            break

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "Public business/request signals via Jina Reader plus public contact enrichment; strong pain-fit pages enter WATCH, and only explicit-intent pages can become actionable.",
        "count": len(prospects),
        "actionable_count": sum(bool(x.get("actionable")) for x in prospects[:LIMIT]),
        "direct_email_count": sum(bool(x.get("contact_email")) for x in prospects[:LIMIT]),
        "prospects": prospects[:LIMIT],
        "diagnostics": DIAGNOSTICS,
        "warning": "Public business signals are lead signals, not consent or sales. Outreach remains one-to-one, bounded and opt-out aware.",
    }
    with open("business_prospects.json", "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(json.dumps({
        "business_prospects": len(prospects),
        "actionable_count": payload["actionable_count"],
        "diagnostics": DIAGNOSTICS,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

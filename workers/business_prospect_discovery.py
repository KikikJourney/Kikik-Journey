#!/usr/bin/env python3
"""Discover public business pain signals and reachable business contact emails.

This module intentionally uses public web search only. It does not scrape social
profiles or gated marketplaces, and it only returns prospects when a public
business website exposes a contact email plus a concrete automation pain signal.
"""
import html
import json
import os
import re
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

USER_AGENT = "KikikJourney-BusinessProspector/1.0 (+public-business-research)"
LIMIT = int(os.getenv("KJ_BUSINESS_DISCOVERY_LIMIT", "12"))
TIMEOUT = 15

QUERIES = [
    '"need help" automation "google sheets" business',
    '"looking for" automation "google sheets" ecommerce',
    '"need a developer" woocommerce "google sheets"',
    '"looking for" whatsapp automation business',
    '"manual process" automation ecommerce business',
    '"workflow automation" "small business" "contact us"',
]

BLOCKED_DOMAINS = {
    "github.com", "reddit.com", "linkedin.com", "facebook.com", "instagram.com",
    "x.com", "twitter.com", "youtube.com", "tiktok.com", "upwork.com",
    "fiverr.com", "freelancer.com", "indeed.com", "glassdoor.com", "quora.com",
    "medium.com", "substack.com",
}

WEBMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "live.com", "icloud.com", "proton.me", "protonmail.com",
}

BUSINESS_TERMS = (
    "our business", "my business", "our store", "my store", "ecommerce", "e-commerce",
    "customers", "orders", "inventory", "appointments", "bookings", "clients",
    "leads", "sales", "shop", "store", "agency", "restaurant", "clinic", "service business",
)
PAIN_TERMS = (
    "manual", "manually", "tedious", "time-consuming", "hours every", "copying",
    "spreadsheet", "google sheets", "workflow", "repetitive", "bottleneck",
    "integration", "automation", "automate", "slow", "error-prone",
)
INTENT_TERMS = (
    "need help", "looking for", "need a developer", "need someone", "hire",
    "hiring", "paid help", "who can build", "who can fix", "help me automate",
    "looking to automate", "want to automate", "need this built", "need this fixed",
)
OFFER_KEYWORDS = {
    "WooCommerce → Google Sheets Automation": ("woocommerce", "google sheets", "orders", "inventory", "stock"),
    "WhatsApp → Google Sheets Mini Automation": ("whatsapp", "google sheets", "message", "attendance", "expense", "stock", "follow-up"),
    "Workflow Rescue Pilot": ("automation", "automate", "workflow", "manual", "integration", "zapier", "make", "n8n"),
}

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.links = []
        self._href = None
        self._link_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._href = attrs["href"]
            self._link_parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)
            if self._href is not None:
                self._link_parts.append(text)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._link_parts)))
            self._href = None
            self._link_parts = []

def fetch(url, accept="text/html,application/xhtml+xml", timeout=TIMEOUT):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(1_500_000)
        return response.geturl(), raw, response.headers.get_content_charset() or "utf-8"

def allowed_by_robots(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        _, raw, charset = fetch(robots_url, accept="text/plain", timeout=8)
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(raw.decode(charset, "ignore").splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        # If robots.txt is unavailable, do not treat that as permission to bypass
        # access controls. Public HTML remains eligible, but we skip the page.
        return False

def clean_text(value):
    value = html.unescape(value or "")
    return re.sub(r"\s+", " ", value).strip()

def extract_emails(text):
    found = set(re.findall(r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", text or ""))
    return sorted(found)

def email_is_business(email, website):
    domain = email.rsplit("@", 1)[-1].lower()
    site_domain = urlparse(website).netloc.lower().removeprefix("www.")
    return domain not in WEBMAIL_DOMAINS and (domain == site_domain or site_domain.endswith("." + domain) or domain.endswith("." + site_domain))

def unwrap_result(url):
    url = html.unescape(unquote(url))
    parsed = urlparse(url)
    if parsed.netloc.endswith("google.com") and parsed.path == "/url":
        target = parse_qs(parsed.query).get("q", [None])[0]
        if target:
            return target
    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/a"):
        return None
    return url if parsed.scheme in {"http", "https"} else None

def search_engine(url):
    try:
        _, raw, charset = fetch(url, accept="text/html")
        parser = TextParser()
        parser.feed(raw.decode(charset, "ignore"))
        results = []
        for href, label in parser.links:
            target = unwrap_result(href)
            if not target:
                continue
            parsed = urlparse(target)
            domain = parsed.netloc.lower().removeprefix("www.")
            if not domain or any(domain == d or domain.endswith("." + d) for d in BLOCKED_DOMAINS):
                continue
            if target not in {x["url"] for x in results}:
                results.append({"url": target, "title": clean_text(label)})
            if len(results) >= 20:
                break
        return results
    except (HTTPError, URLError, TimeoutError, ValueError):
        return []

def search(query):
    engines = [
        "https://www.google.com/search?q=" + quote_plus(query) + "&num=10&hl=en",
        "https://www.bing.com/search?q=" + quote_plus(query) + "&count=10&setlang=en",
        "https://html.duckduckgo.com/html/?q=" + quote_plus(query),
    ]
    seen = set()
    results = []
    for endpoint in engines:
        for item in search_engine(endpoint):
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            results.append(item)
        if len(results) >= 12:
            break
    return results

def match_offer(text):
    normalized = clean_text(text).lower()
    ranked = []
    for name, keywords in OFFER_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in normalized)
        ranked.append((hits, name))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] else None

def score_page(text, emails):
    normalized = clean_text(text).lower()
    business = sum(1 for term in BUSINESS_TERMS if term in normalized)
    pain = sum(1 for term in PAIN_TERMS if term in normalized)
    intent = sum(1 for term in INTENT_TERMS if term in normalized)
    score = min(100, business * 6 + pain * 7 + intent * 14 + (18 if emails else 0))
    return score, business, pain, intent

def inspect_business(url, title):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if not allowed_by_robots(url):
        return None
    try:
        final_url, raw, charset = fetch(url)
        parser = TextParser()
        parser.feed(raw.decode(charset, "ignore"))
        text = clean_text(" ".join(parser.parts))[:12000]
        emails = [e for e in extract_emails(raw.decode(charset, "ignore")) if email_is_business(e, final_url)]
        score, business, pain, intent = score_page(text, emails)
        offer = match_offer(text)
        if business < 2 or pain < 1 or intent < 1 or not offer or not emails:
            return None
        return {
            "source": "public_business_web_signal",
            "source_type": "public_business_web_signal",
            "title": title or parser.parts[0] if parser.parts else parsed.netloc,
            "website": final_url,
            "contact_email": emails[0],
            "score": score,
            "matched_offer": offer,
            "commercial_intent": intent,
            "business_signal": business,
            "pain_signal": pain,
            "evidence": text[:1600],
            "contact_channel": "public_business_email",
            "reachability": "direct_email",
        }
    except (HTTPError, URLError, TimeoutError, UnicodeError, ValueError):
        return None

def discover():
    candidates = []
    seen = set()
    for query in QUERIES:
        for result in search(query):
            domain = urlparse(result["url"]).netloc.lower().removeprefix("www.")
            if domain in seen:
                continue
            seen.add(domain)
            item = inspect_business(result["url"], result.get("title", ""))
            if item:
                item["discovery_query"] = query
                candidates.append(item)
            if len(candidates) >= LIMIT:
                break
        if len(candidates) >= LIMIT:
            break
        time.sleep(0.2)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:LIMIT]

def main():
    output_path = os.getenv("KJ_BUSINESS_DISCOVERY_OUTPUT", "business_prospects.json")
    prospects = discover()
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "Public search + public business website evidence + public business email; no authenticated scraping.",
        "count": len(prospects),
        "prospects": prospects,
        "warning": "A public business signal is a lead signal, not consent or proof of purchase. Outreach must remain relevant, one-to-one, low-rate, and honor opt-out requests.",
    }
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps({"business_prospects": len(prospects)}, indent=2))

if __name__ == "__main__":
    main()

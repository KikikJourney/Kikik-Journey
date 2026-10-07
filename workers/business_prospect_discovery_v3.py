#!/usr/bin/env python3
"""Business discovery via public search pages read through Jina Reader.

Jina Reader is used as a no-signup fallback because direct search-engine HTML
returned zero usable prospects from GitHub Actions. No credentials are sent.
"""
import html,json,os,re,time
from urllib.parse import quote_plus,urljoin,urlparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

LIMIT=int(os.getenv("KJ_BUSINESS_DISCOVERY_LIMIT","8"))
UA="KikikJourney-BusinessProspector/1.2"
QUERIES=[
 '"need help" automation "google sheets" business',
 '"looking for" automation "google sheets" ecommerce',
 '"need a developer" woocommerce "google sheets"',
 '"looking for" whatsapp automation business',
 '"manual process" automation ecommerce business',
 '"workflow automation" "small business"',
]
BLOCKED=("github.com","reddit.com","linkedin.com","facebook.com","instagram.com","x.com","twitter.com","youtube.com","tiktok.com","upwork.com","fiverr.com","freelancer.com","indeed.com","glassdoor.com","quora.com")
WEBMAIL=("gmail.com","googlemail.com","yahoo.com","outlook.com","hotmail.com","live.com","icloud.com","proton.me","protonmail.com")
BUSINESS=("our business","my business","our store","my store","ecommerce","e-commerce","customers","orders","inventory","appointments","bookings","clients","leads","sales","shop","store","agency","restaurant","clinic")
PAIN=("manual","manually","tedious","time-consuming","hours every","copying","spreadsheet","google sheets","workflow","repetitive","bottleneck","integration","automation","automate","slow","error-prone")
INTENT=("need help","looking for","need a developer","need someone","hire","hiring","paid help","who can build","who can fix","help me automate","looking to automate","want to automate","need this built","need this fixed")
OFFERS={
 "WooCommerce → Google Sheets Automation":("woocommerce","google sheets","orders","inventory","stock"),
 "WhatsApp → Google Sheets Mini Automation":("whatsapp","google sheets","message","attendance","expense","stock","follow-up"),
 "Workflow Rescue Pilot":("automation","automate","workflow","manual","integration","zapier","make","n8n"),
}

def get(url,timeout=20):
 req=Request(url,headers={"User-Agent":UA,"Accept":"text/plain,text/html"})
 with urlopen(req,timeout=timeout) as r:
  return r.read(1500000).decode(r.headers.get_content_charset() or "utf-8","ignore"),r.geturl()

def read(url):
 try:
  text,final=get("https://r.jina.ai/"+url)
  return text,final
 except (HTTPError,URLError,TimeoutError,UnicodeError): return "",url

def search(q):
 found=[]
 seen=set()
 targets=[
  "https://www.google.com/search?q="+quote_plus(q)+"&num=10&hl=en",
  "https://www.bing.com/search?q="+quote_plus(q)+"&count=10",
  "https://html.duckduckgo.com/html/?q="+quote_plus(q),
 ]
 for target in targets:
  body,_=read(target)
  links = re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", body)
  links += [(u, u) for u in re.findall(r"https?://[^\s<>\)\]\"]+", body)]
  for title,url in links:
   u=html.unescape(url).rstrip(".,);")
   d=urlparse(u).netloc.lower().removeprefix("www.")
   if not d or any(d==x or d.endswith("."+x) for x in BLOCKED): continue
   if u in seen: continue
   seen.add(u); found.append({"title":html.unescape(title),"url":u})
   if len(found)>=6: return found[:6]
 return found
def emails(text):
 return sorted(set(re.findall(r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",text or "")))

def is_business_email(e,site):
 d=e.rsplit("@",1)[-1].lower(); s=urlparse(site).netloc.lower().removeprefix("www.")
 return d not in WEBMAIL and (d==s or s.endswith("."+d) or d.endswith("."+s))

def inspect(item,q):
 body,final=read(item["url"])
 if not body: return None
 page_context=(body+" "+item.get("title","")).lower()
 b=sum(k in page_context for k in BUSINESS); pain=sum(k in page_context for k in PAIN); intent=sum(k in page_context for k in INTENT)
 ranked=sorted((sum(k in page_context for k in ks),name) for name,ks in OFFERS.items())
 hits,offer=ranked[-1]
 found=[e for e in emails(body) if is_business_email(e,final)]
 contact_url=""
 contact_links=re.findall(r"\[[^\]]*(?:contact|about|support|sales)[^\]]*\]\((https?://[^)]+)\)",body,re.I)
 if contact_links:
  contact_url=urljoin(final,contact_links[0])
  for u in contact_links[:3]:
   ct,cf=read(u); found += [e for e in emails(ct) if is_business_email(e,cf)]
 found=sorted(set(found))
 if b<2 or pain<1 or intent<1 or hits<1: return None
 if not found and not contact_url: return None
 reachability="direct_email" if found else "contact_form_or_contact_page"
 return {
  "source":"public_business_web_signal","source_type":"public_business_web_signal",
  "title":item.get("title") or urlparse(final).netloc,"website":final,
  "contact_email":found[0] if found else "","contact_url":contact_url,
  "score":min(100,b*6+pain*7+intent*14+18+(12 if found else 0)),
  "matched_offer":offer,"commercial_intent":intent,"business_signal":b,
  "pain_signal":pain,"evidence":re.sub(r"\s+"," ",body)[:1600],
  "contact_channel":"public_business_email" if found else "public_contact_page",
  "reachability":reachability,"discovery_query":q
 }
def main():
 prospects=[]; domains=set()
 for q in QUERIES:
  for item in search(q):
   d=urlparse(item["url"]).netloc.lower().removeprefix("www.")
   if d in domains: continue
   domains.add(d); hit=inspect(item,q)
   if hit: prospects.append(hit)
   if len(prospects)>=LIMIT: break
  if len(prospects)>=LIMIT: break
  time.sleep(.2)
 payload={"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"method":"Public search pages via Jina Reader plus public business pages/contact details; no credentials.","count":len(prospects),"prospects":prospects[:LIMIT],"warning":"Public business signals are lead signals, not consent or sales. Outreach remains one-to-one, bounded and opt-out aware."}
 open("business_prospects.json","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({"business_prospects":len(prospects)}))

if __name__=="__main__": main()

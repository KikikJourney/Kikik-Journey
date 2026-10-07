#!/usr/bin/env python3
import html,json,os,re,time
from html.parser import HTMLParser
from urllib.error import HTTPError,URLError
from urllib.parse import quote_plus,urljoin,urlparse
from urllib.request import Request,urlopen

UA="KikikJourney-BusinessProspector/1.1"
LIMIT=int(os.getenv("KJ_BUSINESS_DISCOVERY_LIMIT","12"))
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

class P(HTMLParser):
 def __init__(self):
  super().__init__(); self.parts=[]; self.links=[]; self.href=None; self.link=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="a" and a.get("href"): self.href=a["href"]; self.link=[]
 def handle_data(self,data):
  t=data.strip()
  if t:
   self.parts.append(t)
   if self.href is not None: self.link.append(t)
 def handle_endtag(self,tag):
  if tag=="a" and self.href is not None:
   self.links.append((self.href," ".join(self.link))); self.href=None; self.link=[]

def get(url,timeout=12):
 req=Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,text/plain"})
 with urlopen(req,timeout=timeout) as r:
  raw=r.read(1200000); return r.geturl(),raw,r.headers.get_content_charset() or "utf-8"

def text(v): return re.sub(r"\s+"," ",html.unescape(v or "")).strip()

def emails(v):
 return sorted(set(re.findall(r"(?i)(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",v or "")))

def business_email(e,site):
 d=e.rsplit("@",1)[-1].lower(); s=urlparse(site).netloc.lower().removeprefix("www.")
 return d not in WEBMAIL and (d==s or s.endswith("."+d) or d.endswith("."+s))

def search(q):
 out=[]; seen=set()
 endpoints=[
  "https://www.google.com/search?q="+quote_plus(q)+"&num=10&hl=en",
  "https://html.duckduckgo.com/html/?q="+quote_plus(q),
 ]
 for endpoint in endpoints:
  try:
   _,raw,enc=get(endpoint); p=P(); p.feed(raw.decode(enc,"ignore"))
   for href,label in p.links:
    target=href
    if target.startswith("/url?q="):
     target=target.split("/url?q=",1)[1].split("&",1)[0]
    if not target.startswith(("http://","https://")): continue
    d=urlparse(target).netloc.lower().removeprefix("www.")
    if not d or any(d==x or d.endswith("."+x) for x in BLOCKED): continue
    if target not in seen:
     seen.add(target); out.append({"url":target,"title":text(label)})
    if len(out)>=15: return out
  except (HTTPError,URLError,TimeoutError,ValueError): pass
 return out

def inspect(item,q):
 try:
  final,raw,enc=get(item["url"]); decoded=raw.decode(enc,"ignore")
  p=P(); p.feed(decoded)
  body=text(" ".join(p.parts))[:14000]
  found=[e for e in emails(decoded) if business_email(e,final)]
  if not found:
   links=[]
   for href,label in p.links:
    u=urljoin(final,href); pu=urlparse(u)
    if pu.netloc!=urlparse(final).netloc: continue
    marker=(label+" "+pu.path).lower()
    if any(k in marker for k in ("contact","about","support","sales")): links.append(u)
   for u in links[:3]:
    try:
     cf,cr,ce=get(u); ct=cr.decode(ce,"ignore"); found += [e for e in emails(ct) if business_email(e,cf)]
     body += " "+text(ct)[:4000]
    except (HTTPError,URLError,TimeoutError,UnicodeError,ValueError): pass
    if found: break
  context=(body+" "+item.get("title","")+" "+q).lower()
  b=sum(k in context for k in BUSINESS); pain=sum(k in context for k in PAIN); intent=sum(k in context for k in INTENT)
  ranked=sorted((sum(k in context for k in ks),name) for name,ks in OFFERS.items())
  hits,offer=ranked[-1]
  if b<2 or pain<1 or intent<1 or hits<1 or not found: return None
  return {"source":"public_business_web_signal","source_type":"public_business_web_signal","title":item.get("title") or urlparse(final).netloc,"website":final,"contact_email":found[0],"score":min(100,b*6+pain*7+intent*14+18),"matched_offer":offer,"commercial_intent":intent,"business_signal":b,"pain_signal":pain,"evidence":body[:1600],"contact_channel":"public_business_email","reachability":"direct_email","discovery_query":q}
 except (HTTPError,URLError,TimeoutError,UnicodeError,ValueError): return None

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
 payload={"generated_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"method":"Public search plus public business website/contact pages; no authenticated scraping.","count":len(prospects),"prospects":prospects[:LIMIT],"warning":"Public business signals are lead signals, not consent or sales. Outreach remains one-to-one, bounded and opt-out aware."}
 open("business_prospects.json","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({"business_prospects":len(prospects)}))

if __name__=="__main__": main()

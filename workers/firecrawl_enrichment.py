#!/usr/bin/env python3
"""Optional Firecrawl evidence enrichment for public business prospects."""
import ipaddress, json, os, socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API=os.getenv("FIRECRAWL_API_URL","https://api.firecrawl.dev/v2/scrape").rstrip("/")
KEY=os.getenv("FIRECRAWL_API_KEY","").strip()
LIMIT=max(0,int(os.getenv("KJ_FIRECRAWL_LIMIT","6")))
TIMEOUT=max(5,int(os.getenv("KJ_FIRECRAWL_TIMEOUT_SECONDS","30")))
INPUT=os.getenv("KJ_FIRECRAWL_INPUT","business_prospects.json")
OUTPUT=os.getenv("KJ_FIRECRAWL_OUTPUT","business_prospects.json")
REPORT=os.getenv("KJ_FIRECRAWL_REPORT","firecrawl_report.json")

def _public_url(url):
    p=urlparse(str(url or "").strip())
    if p.scheme not in {"http","https"} or not p.hostname: return False
    host=p.hostname.lower()
    if host in {"localhost","localhost.localdomain"} or host.endswith(".local"): return False
    try:
        ip=ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)
    except ValueError: pass
    try:
        for entry in socket.getaddrinfo(host,None):
            ip=ipaddress.ip_address(entry[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: return False
    except (OSError,ValueError): return False
    return True

def scrape(url):
    if not _public_url(url): raise ValueError("URL is not an eligible public HTTP(S) destination")
    req=Request(API,data=json.dumps({"url":url,"formats":["markdown"]}).encode(),headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json","Accept":"application/json","User-Agent":"KikikJourney-Firecrawl-Enrichment/1.0"},method="POST")
    with urlopen(req,timeout=TIMEOUT) as response: payload=json.load(response)
    if not payload.get("success",False): raise RuntimeError("Firecrawl returned success=false")
    data=payload.get("data") or {}; meta=data.get("metadata") or {}
    return {"title":meta.get("title",""),"description":meta.get("description",""),"source_url":meta.get("sourceURL") or url,"markdown_excerpt":(data.get("markdown") or "")[:3500]}

def main():
    with open(INPUT,encoding="utf-8") as h: payload=json.load(h)
    prospects=payload.get("prospects",[])
    report={"enabled":bool(KEY),"requested":0,"enriched":0,"failed":0,"skipped":0,"failures":[],"contract":"evidence-only; no score/qualification mutation"}
    if not KEY:
        report["status"]="disabled_missing_secret"
        with open(REPORT,"w",encoding="utf-8") as h: json.dump(report,h,indent=2)
        print(json.dumps(report)); return
    selected=[x for x in prospects if x.get("actionable") and x.get("contact_email") and x.get("website")][:LIMIT]
    report["requested"]=len(selected)
    for item in selected:
        try:
            evidence=scrape(item["website"])
            item["firecrawl_evidence"]={"status":"enriched",**evidence}
            base=item.get("evidence","").strip(); excerpt=evidence.get("markdown_excerpt","").strip()
            if excerpt and excerpt not in base: item["evidence"]=(base+"\n\nFirecrawl website evidence:\n"+excerpt)[:5000]
            report["enriched"]+=1
        except Exception as exc:
            item["firecrawl_evidence"]={"status":"failed","error_type":type(exc).__name__}
            report["failed"]+=1; report["failures"].append({"website":item.get("website"),"error_type":type(exc).__name__})
    report["skipped"]=max(0,len(prospects)-len(selected)); report["status"]="completed"
    with open(OUTPUT,"w",encoding="utf-8") as h: json.dump(payload,h,indent=2,ensure_ascii=False)
    with open(REPORT,"w",encoding="utf-8") as h: json.dump(report,h,indent=2,ensure_ascii=False)
    print(json.dumps(report))
if __name__=="__main__": main()

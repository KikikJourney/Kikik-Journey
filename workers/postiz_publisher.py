#!/usr/bin/env python3
"""Bounded Postiz publisher for evergreen Kikik Journey sales content."""
import hashlib,json,os
from datetime import datetime,timedelta,timezone
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

BASE=os.getenv("POSTIZ_API_URL","https://api.postiz.com").rstrip("/")
KEY=os.getenv("POSTIZ_API_KEY","").strip()
INTEGRATIONS=[x.strip() for x in os.getenv("POSTIZ_INTEGRATION_IDS","").split(",") if x.strip()]
CHECKOUT=os.getenv("CHECKOUT_BASE_URL","https://kikikjourney.github.io/Kikik-Journey/sales/manual-order.html?source=postiz")
TIMEOUT=max(5,int(os.getenv("POSTIZ_TIMEOUT_SECONDS","25")))
LOOKBACK_DAYS=max(1,int(os.getenv("POSTIZ_LOOKBACK_DAYS","14")))
REPORT=os.getenv("POSTIZ_REPORT","postiz_report.json")

CONTENT=[
("Workflow Rescue","Still copying data between tools by hand?\n\nKikik Journey fixes one repetitive workflow with a narrow, testable automation path.\n\n"+CHECKOUT+"&offer=workflow"),
("WooCommerce to Sheets","If WooCommerce orders are being copied into Google Sheets manually, that is a small workflow worth fixing.\n\nKikik Journey offers a fixed-scope WooCommerce → Google Sheets automation pilot.\n\n"+CHECKOUT+"&offer=woocommerce"),
("WhatsApp to Sheets","Manual WhatsApp-to-spreadsheet work creates repetitive data entry and avoidable errors.\n\nKikik Journey can scope one WhatsApp → Google Sheets workflow as a small automation pilot.\n\n"+CHECKOUT+"&offer=whatsapp"),
("Validate Before Building","Before spending time on a larger AI or automation build, validate the buyer, pain, evidence, scope and commercial path.\n\n"+CHECKOUT+"&offer=validation"),
("One Workflow, One Outcome","Automation does not need to start as a giant system. Pick one repetitive workflow, define the inputs and output, automate the narrow path, then measure the result.\n\n"+CHECKOUT+"&offer=workflow"),
("AI Opportunity Lab","Kikik Journey researches public problem signals, qualifies evidence, packages narrow offers and routes interested buyers to one central checkout.\n\nNo guaranteed outcomes, no fake sales claims.\n\n"+CHECKOUT)
]

def api(path,method="GET",body=None):
    data=json.dumps(body).encode() if body is not None else None
    headers={"Authorization":KEY,"Accept":"application/json","User-Agent":"KikikJourney-Postiz-Publisher/1.0"}
    if body is not None: headers["Content-Type"]="application/json"
    with urlopen(Request(BASE+path,data=data,headers=headers,method=method),timeout=TIMEOUT) as response: return json.load(response)

def fingerprint(content): return hashlib.sha256(" ".join(content.split()).encode()).hexdigest()

def collect_text(value):
    if isinstance(value,str): return [value]
    if isinstance(value,dict):
        out=[]
        for v in value.values(): out.extend(collect_text(v))
        return out
    if isinstance(value,list):
        out=[]
        for v in value: out.extend(collect_text(v))
        return out
    return []

def recent_posts():
    now=datetime.now(timezone.utc); start=(now-timedelta(days=LOOKBACK_DAYS)).isoformat().replace("+00:00","Z"); end=(now+timedelta(minutes=5)).isoformat().replace("+00:00","Z")
    return "\n".join(collect_text(api("/public/v1/posts?"+urlencode({"startDate":start,"endDate":end}))))

def schedule(content):
    when=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat().replace("+00:00","Z")
    body={"type":"schedule","date":when,"shortLink":False,"tags":[],"posts":[{"integration":{"id":i},"value":[{"content":content}],"settings":{}} for i in INTEGRATIONS]}
    return api("/public/v1/posts","POST",body)

def main():
    report={"enabled":bool(KEY and INTEGRATIONS),"status":"","integration_count":len(INTEGRATIONS),"candidates":len(CONTENT),"scheduled":0,"skipped_duplicate":0,"failures":[]}
    if not KEY or not INTEGRATIONS:
        report["status"]="disabled_missing_postiz_configuration"
        with open(REPORT,"w") as h: json.dump(report,h,indent=2)
        print(json.dumps(report)); return
    try:
        integrations=api("/public/v1/integrations")
        rows=integrations.get("integrations",integrations if isinstance(integrations,list) else [])
        known={str(x["id"]) for x in rows if isinstance(x,dict) and x.get("id")}
        missing=sorted(set(INTEGRATIONS)-known)
        if missing: raise RuntimeError("Configured Postiz integration IDs not found: "+",".join(missing))
        recent=recent_posts()
    except Exception as exc:
        report["status"]="provider_check_failed"; report["failures"].append({"stage":"preflight","error_type":type(exc).__name__})
        with open(REPORT,"w") as h: json.dump(report,h,indent=2)
        raise SystemExit(1)
    for title,content in CONTENT:
        if fingerprint(content) in recent or content in recent:
            report["skipped_duplicate"]+=1; continue
        try:
            schedule(content); report["scheduled"]+=1; recent+="\n"+content
        except (HTTPError,URLError,TimeoutError,ValueError) as exc:
            report["failures"].append({"title":title,"error_type":type(exc).__name__}); break
    report["status"]="completed" if not report["failures"] else "partial_failure"
    with open(REPORT,"w") as h: json.dump(report,h,indent=2)
    if report["failures"]: raise SystemExit(1)
    print(json.dumps(report))
if __name__=="__main__": main()

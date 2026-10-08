import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

try:
    from workers.revenue_event_ledger import append_events
except ModuleNotFoundError:
    from revenue_event_ledger import append_events
try:
    from workers.verify_usdt_payment import verify_payment
except ModuleNotFoundError:
    from verify_usdt_payment import verify_payment

API="https://api.agentmail.to/v0"
INBOX=os.getenv("AGENTMAIL_INBOX_EMAIL","kikikjourney@agentmail.to")
GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")
GITHUB_REPO=os.getenv("GITHUB_REPOSITORY","KikikJourney/Kikik-Journey")
PAYMENT_RECIPIENT=os.getenv("PAYMENT_RECIPIENT","0x4ce7004e7127f8b2386eb355e088f127c24b3fac")
VALIDATION_KIT_URL="https://github.com/KikikJourney/Kikik-Journey/tree/main/products/ai-opportunity-validation-kit"
OFFERS={"woocommerce":("WooCommerce → Google Sheets pilot",Decimal("5"),399000),"whatsapp":("WhatsApp → Google Sheets mini automation",Decimal("2.5"),199000),"workflow":("Workflow Rescue Pilot",Decimal("3"),250000),"validation":("AI Opportunity Validation Kit",Decimal("0.25"),19000)}
EMAIL_RE=re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",re.I)

def api(path,method="GET",payload=None,query=None):
    headers={"Accept":"application/json","Authorization":"Bearer "+os.environ["AGENTMAIL_API_KEY"],"User-Agent":"KikikJourney-ManualOrder/1.0"}
    url=API+path
    if query: url+="?"+urllib.parse.urlencode(query,doseq=True)
    data=json.dumps(payload).encode() if payload is not None else None
    if data: headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read().decode()
        return json.loads(raw) if raw else {}

def qpath(inbox,message_id=None):
    p="/inboxes/"+urllib.parse.quote(inbox,safe="")+"/messages"
    return p+("/"+urllib.parse.quote(message_id,safe="") if message_id else "")

def sender(value):
    m=re.search(r"<([^>]+)>",value or "")
    return (m.group(1) if m else (value or "")).strip().lower()

def field(text,name):
    m=re.search(rf"^\s*{re.escape(name)}\s*:\s*(.+?)\s*$",text or "",re.I|re.M)
    return m.group(1).strip() if m else ""

def email(value):
    m=EMAIL_RE.search(value or "")
    return m.group(0).lower() if m else ""

def ref(text):
    m=re.search(r"\bKJ-MANUAL-[A-Z0-9-]{4,40}\b",text or "",re.I)
    return m.group(0).upper() if m else ""

def tx_hash(text):
    m=re.search(r"\b0x[a-fA-F0-9]{64}\b",text or "")
    return m.group(0) if m else ""

def offer_from(text):
    key=(field(text,"Offer") or "").lower()
    if key in OFFERS:return key
    t=(text or "").lower()
    for k in OFFERS:
        if k in t:return k
    return ""

def parse(text):
    source=re.sub(r"[^a-z0-9._-]","",(field(text,"Source") or "direct").lower())[:40] or "direct"
    return {"ref":ref(text),"contact_email":email(field(text,"Contact email")),"offer":offer_from(text),"source":source,"payment":field(text,"Payment method") or "USDT"}

def github_issue(title,body):
    if not GITHUB_TOKEN:return None
    req=urllib.request.Request("https://api.github.com/repos/"+GITHUB_REPO+"/issues",data=json.dumps({"title":title,"body":body}).encode(),headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+GITHUB_TOKEN,"X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def github_find(ref_value):
    if not GITHUB_TOKEN:return None
    q=urllib.parse.quote(f"repo:{GITHUB_REPO} is:issue {ref_value}")
    req=urllib.request.Request("https://api.github.com/search/issues?q="+q,headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+GITHUB_TOKEN,"X-GitHub-Api-Version":"2022-11-28"})
    with urllib.request.urlopen(req,timeout=30) as r:
        items=json.loads(r.read().decode()).get("items",[])
    return items[0] if items else None

def github_update(number,title,body):
    if not GITHUB_TOKEN:return
    req=urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/issues/{number}",data=json.dumps({"title":title,"body":body}).encode(),headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+GITHUB_TOKEN,"X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json"},method="PATCH")
    urllib.request.urlopen(req,timeout=30).read()

def send(to,subject,text,labels):
    return api(qpath(INBOX)+"/send","POST",{"to":[to],"subject":subject,"text":text,"labels":labels})

def load_detail(mid):
    return api(qpath(INBOX,mid))

def manual_messages(limit=100):
    return api(qpath(INBOX),query={"limit":limit,"ascending":False}).get("messages",[])

def find_order(ref_value):
    for item in manual_messages():
        if ref_value not in (item.get("subject") or "").upper():continue
        mid=item.get("message_id")
        if not mid:continue
        d=load_detail(mid)
        text="\n".join(str(d.get(k,"")) for k in ("subject","extracted_text","text"))
        if "MANUAL ORDER" in text.upper():
            p=parse(text)
            if p["contact_email"] and p["offer"]:return p
    return None

def mark(mid,kind):
    return api(qpath(INBOX,mid),"PATCH",{"add_labels":["kj-processed","kj-manual",kind]})

def process_order(mid,text):
    p=parse(text)
    if not p["ref"] or not p["contact_email"] or p["offer"] not in OFFERS:
        return {"status":"invalid_manual_order"}
    title=OFFERS[p["offer"]][0]
    contact_hash=hashlib.sha256(p["contact_email"].encode()).hexdigest()[:16]
    existing=github_find(p["ref"])
    if not existing:
        github_issue(f"[MANUAL ORDER PENDING] {p['ref']} — {title}",f"Order reference: {p['ref']}\nStatus: PENDING_PAYMENT\nOffer key: {p['offer']}\nSource: {p['source']}\nPayment method: {p['payment']}\nContact hash: {contact_hash}\nContact email is intentionally not stored in the public GitHub record.")
    msg=(f"Manual order {p['ref']} received.\n\nOffer: {title}\nPayment method: {p['payment']}\nSource: {p['source']}\n\nUSDT: {OFFERS[p['offer']][1]} USDT on BNB Smart Chain (BEP-20). Reply with the transaction hash and order reference after payment.\n\nPayment is independently verified before PAID. Delivery is sent to {p['contact_email']}.")
    send(p["contact_email"],f"Order {p['ref']} received — Kikik Journey",msg,["kj-order"])
    append_events([{"event_id":"order-"+p["ref"].lower(),"event_type":"order_created","source":p["source"],"offer":p["offer"],"order_ref":p["ref"],"amount_idr":OFFERS[p["offer"]][2],"cost_idr":0}])
    return {"status":"order_created","ref":p["ref"]}

def process_payment(mid,text):
    p_ref=ref(text)
    if not p_ref:return {"status":"not_manual_payment"}
    order=find_order(p_ref)
    if not order:return {"status":"manual_order_not_found","ref":p_ref}
    h=tx_hash(text); amount=OFFERS[order["offer"]][1]
    if not h:return {"status":"payment_missing_tx","ref":p_ref}
    result=verify_payment(h,amount,PAYMENT_RECIPIENT)
    if not result.get("ok"):
        send(order["contact_email"],f"Order {p_ref} — payment pending",f"Payment was detected but not accepted as PAID. Verification status: {result.get('status')}. The system will not mark the order paid until independent on-chain verification succeeds.",["kj-payment-pending"])
        return {"status":"payment_rejected","ref":p_ref}
    existing=github_find(p_ref)
    body=f"Order reference: {p_ref}\nStatus: PAID\nOffer: {order['offer']}\nSource: {order['source']}\nTX hash: {h}\nAmount: {amount} USDT\nRecipient: {PAYMENT_RECIPIENT}\nVerification: {json.dumps(result,sort_keys=True)}"
    if existing:github_update(existing["number"],f"[ORDER PAID] {p_ref} — {OFFERS[order['offer']][0]}",body)
    else:github_issue(f"[ORDER PAID] {p_ref} — {OFFERS[order['offer']][0]}",body)
    append_events([{"event_id":"paid-"+h.lower(),"event_type":"paid","source":order["source"],"offer":order["offer"],"order_ref":p_ref,"currency":"USDT","amount":str(amount),"amount_idr":OFFERS[order["offer"]][2],"tx_hash":h.lower(),"cost_idr":0}])
    if order["offer"]=="validation":
        delivery=f"Payment verified on BNB Smart Chain (BEP-20). Order {p_ref} is PAID.\n\nAI Opportunity Validation Kit: {VALIDATION_KIT_URL}\n\nThe digital delivery is ready immediately."
        append_events([{"event_id":"delivered-"+p_ref,"event_type":"delivered","source":order["source"],"offer":order["offer"],"order_ref":p_ref,"amount_idr":0,"cost_idr":0}])
    else:
        delivery=f"Payment verified on BNB Smart Chain (BEP-20). Order {p_ref} is PAID.\n\nAutomated delivery/intake is now active. Reply to this email with the non-sensitive project requirements for {OFFERS[order['offer']][0]}. Never send passwords, OTPs, seed phrases, private keys, or full API secrets."
    send(order["contact_email"],f"Order {p_ref} — PAYMENT VERIFIED",delivery,["kj-paid","kj-delivery"])
    return {"status":"paid_and_delivered","ref":p_ref}

def main():
    results={}
    for item in manual_messages():
        mid=item.get("message_id")
        if not mid or "kj-processed" in set(item.get("labels",[])):continue
        try:
            subject=(item.get("subject") or "").upper()\n            if "MANUAL ORDER" not in subject and "KJ-MANUAL-" not in subject:\n                continue\n            d=load_detail(mid); text="\n".join(str(d.get(k,"")) for k in ("subject","extracted_text","text"))
            kind="manual_order" if "manual order" in text.lower() else ("payment" if ref(text) else "")
            if kind=="manual_order":status=process_order(mid,text); mark(mid,"manual-order")
            elif kind=="payment":status=process_payment(mid,text); mark(mid,"manual-payment")
            else:continue
            results[status["status"]]=results.get(status["status"],0)+1
        except Exception as exc:
            key="error:"+type(exc).__name__;results[key]=results.get(key,0)+1
    print(json.dumps({"results":results},indent=2))

if __name__=="__main__":main()

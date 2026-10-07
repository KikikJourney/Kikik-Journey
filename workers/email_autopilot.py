import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.agentmail.to/v0"
INBOX = os.getenv("AGENTMAIL_INBOX_EMAIL", "kikikjourney@agentmail.to")
STATE = "runtime/email_state.json"
CHECKOUT = os.getenv("CHECKOUT_BASE_URL", "https://kikikjourney.github.io/Kikik-Journey/sales/checkout.html")

def api(path, method="GET", payload=None):
    headers = {"Accept":"application/json","Authorization":f"Bearer {os.environ['AGENTMAIL_API_KEY']}","User-Agent":"KikikJourney-AutonomousSales/1.0"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}

def inbox_id():
    data = api("/inboxes?limit=100")
    for item in data.get("inboxes", []):
        if item.get("email","").lower() == INBOX.lower():
            return item["inbox_id"]
    raise RuntimeError(f"Inbox not found: {INBOX}")

def load_state():
    try:
        with open(STATE, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError: return {"processed": {}, "updated_at": None}

def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE,"w",encoding="utf-8") as f: json.dump(state,f,indent=2,ensure_ascii=False)

def sender(value):
    m = re.search(r"<([^>]+)>", value or "")
    return (m.group(1) if m else (value or "")).strip().lower()

def classify(text):
    t = (text or "").lower()
    if any(x in t for x in ("paid","payment","transfer","tx hash","transaction","sent usdt")): return "payment"
    if any(x in t for x in ("price","pricing","cost","how much","quote")): return "pricing"
    if any(x in t for x in ("interested","let's do it","lets do it","start","proceed","buy")): return "purchase_intent"
    if any(x in t for x in ("woocommerce","google sheets","whatsapp","automation","workflow")): return "offer_interest"
    return "general"

def reply(inbox,message_id,body):
    path="/inboxes/"+urllib.parse.quote(inbox,safe="")+"/messages/"+urllib.parse.quote(message_id,safe="")+"/reply"
    return api(path,"POST",{"text":body})

def label(inbox,message_id,labels):
    path="/inboxes/"+urllib.parse.quote(inbox,safe="")+"/messages/"+urllib.parse.quote(message_id,safe="")
    return api(path,"PATCH",{"add_labels":labels})

def process(inbox,state,message):
    mid=message["message_id"]
    if "kj-processed" in set(message.get("labels", [])): return "already_processed"
    detail=api("/inboxes/"+urllib.parse.quote(inbox,safe="")+"/messages/"+urllib.parse.quote(mid,safe=""))
    text="\n".join(str(detail.get(k,"")) for k in ("subject","extracted_text","text"))
    kind=classify(text)
    to=sender(detail.get("from"))
    if not to or to==INBOX.lower():
        state["processed"][mid]={"status":"ignored"}; return "ignored"
    subject=detail.get("subject") or "Kikik Journey"
    if kind=="pricing":
        body=("Thanks for reaching out. Current fixed-scope offers are:\n"
              "- WooCommerce → Google Sheets pilot: Rp399.000\n"
              "- WhatsApp → Google Sheets mini automation: Rp199.000\n"
              "- Workflow Rescue Pilot: Rp250.000\n"
              "- AI Opportunity Validation Kit: Rp19.000\n\n"
              "Checkout and scope: "+CHECKOUT+"\n\n"
              "For crypto payment, use USDT on BNB Smart Chain (BEP-20). Do not send passwords, OTPs, seed phrases, or private keys.")
    elif kind in ("purchase_intent","offer_interest"):
        body=("Thanks — we can proceed with the fixed-scope pilot.\n\nCheckout: "+CHECKOUT+
              "\n\nAfter payment, reply with the order reference and minimum project details. Do not send passwords, OTPs, seed phrases, or private keys.")
    elif kind=="payment":
        body=("Payment notice received. We only mark an order paid after independent verification of amount, token contract, destination wallet, transaction status and confirmations. Include the order reference and transaction hash if available. Never send private keys or seed phrases.")
    else:
        state["processed"][mid]={"status":"no_auto_reply","at":datetime.now(timezone.utc).isoformat()}; return "no_auto_reply"
    reply(inbox,mid,body)
    label(inbox,mid,["kj-processed","kj-replied",kind])
    state["processed"][mid]={"status":"replied","kind":kind,"at":datetime.now(timezone.utc).isoformat()}
    return "replied"

def main():
    inbox=inbox_id(); state=load_state()
    data=api("/inboxes/"+urllib.parse.quote(inbox,safe="")+"/messages?limit=100&ascending=false")
    results={}
    for message in data.get("messages",[]):
        try: status=process(inbox,state,message)
        except Exception as exc: status="error:"+type(exc).__name__
        results[status]=results.get(status,0)+1
    save_state(state)
    print(json.dumps({"results":results,"processed_total":len(state["processed"])},indent=2))

if __name__=="__main__": main()

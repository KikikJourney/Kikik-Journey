import json
import os
import re
import urllib.parse
import urllib.request
from workers.verify_usdt_payment import verify_payment
from datetime import datetime, timezone
from decimal import Decimal

API = "https://api.agentmail.to/v0"
INBOX = os.getenv("AGENTMAIL_INBOX_EMAIL", "kikikjourney@agentmail.to")
STATE = "runtime/email_state.json"
CHECKOUT = os.getenv("CHECKOUT_BASE_URL", "https://kikikjourney.github.io/Kikik-Journey/sales/checkout.html")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY", "KikikJourney/Kikik-Journey")
PAYMENT_RECIPIENT = os.getenv("PAYMENT_RECIPIENT", "0x4ce7004e7127f8b2386eb355e088f127c24b3fac")
VALIDATION_KIT_URL = "https://github.com/KikikJourney/Kikik-Journey/tree/main/products/ai-opportunity-validation-kit"
OFFERS = {
    "woocommerce": ("WooCommerce → Google Sheets pilot", Decimal("399000")),
    "whatsapp": ("WhatsApp → Google Sheets mini automation", Decimal("199000")),
    "workflow": ("Workflow Rescue Pilot", Decimal("250000")),
    "validation": ("AI Opportunity Validation Kit", Decimal("19000")),
}

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


def order_ref(message_id):
    return "KJ-" + re.sub(r"[^A-Z0-9]", "", str(message_id).upper())[-10:]


def tx_hash(text):
    m = re.search(r"\b0x[a-fA-F0-9]{64}\b", text or "")
    return m.group(0) if m else None


def detect_offer(text):
    t = (text or "").lower()
    if "woocommerce" in t: return "woocommerce"
    if "whatsapp" in t: return "whatsapp"
    if "workflow rescue" in t or "workflow" in t: return "workflow"
    if "validation kit" in t or "opportunity validation" in t: return "validation"
    return None


def payment_amount(text, offer):
    if offer in OFFERS:
        return OFFERS[offer][1]
    m = re.search(r"(?:rp|idr)\s*([0-9][0-9.,]*)", (text or "").lower())
    if not m: return None
    raw = re.sub(r"[^0-9]", "", m.group(1))
    return Decimal(raw) if raw else None


def github_issue(title, body):
    if not GITHUB_TOKEN: return None
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/issues"
    payload = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Accept":"application/vnd.github+json",
        "Authorization":f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version":"2022-11-28",
        "Content-Type":"application/json",
    }, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def create_order(mid, detail, status):
    body = "\n".join(str(detail.get(k,"")) for k in ("subject","extracted_text","text"))
    ref = order_ref(mid)
    offer = detect_offer(body)
    title = OFFERS[offer][0] if offer in OFFERS else "Kikik Journey order"
    github_issue(
        f"[ORDER {status.upper()}] {ref} — {title}",
        f"Order reference: {ref}\nStatus: {status.upper()}\nCustomer: {sender(detail.get('from'))}\n"
        f"Message ID: {mid}\nOffer key: {offer or 'unknown'}\nSource subject: {detail.get('subject','')}\n\n"
        f"Original customer message:\n{body[:6000]}"
    )
    return ref, offer

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
        ref, offer = create_order(mid, detail, "pending_payment")
        suffix = ("?offer=" + offer) if offer else ""
        body=(f"Thanks — automated order intake is open.\\n\\nOrder reference: {ref}\\n"
              f"Checkout: {CHECKOUT}{suffix}\\n\\n"
              "After USDT payment, reply in this thread with the transaction hash. "
              "The system will independently verify the BNB Smart Chain (BEP-20) payment. "
              "For service offers, this thread becomes the intake channel. "
              "Do not send passwords, OTPs, seed phrases, or private keys.")
    elif kind=="payment":
        ref = order_ref(mid)
        offer = detect_offer(text)
        h = tx_hash(text)
        amount = payment_amount(text, offer)
        if h and amount:
            result = verify_payment(h, amount, PAYMENT_RECIPIENT)
            if result.get("ok"):
                github_issue(
                    f"[ORDER PAID] {ref} — {OFFERS.get(offer, ('Kikik Journey', amount))[0]}",
                    f"Order reference: {ref}\\nStatus: PAID\\nTX hash: {h}\\nAmount: {amount} USDT\\n"
                    f"Recipient: {PAYMENT_RECIPIENT}\\nCustomer: {sender(detail.get('from'))}\\n"
                    f"Verification: {json.dumps(result, sort_keys=True)}"
                )
                if offer == "validation":
                    body=(f"Payment verified on BNB Smart Chain (BEP-20). Order {ref} is PAID.\\n\\n"
                          f"Your AI Opportunity Validation Kit: {VALIDATION_KIT_URL}\\n"
                          "The kit is ready immediately; no credentials are required.")
                else:
                    body=(f"Payment verified on BNB Smart Chain (BEP-20). Order {ref} is PAID.\\n\\n"
                          "Your order is now in the automated intake queue. Reply with the non-sensitive "
                          "project requirements for the selected scope. Never send passwords, OTPs, seed phrases, or private keys.")
            else:
                body=(f"Order {ref}: payment detected but not accepted as paid.\\n\\n"
                      f"Verification status: {result.get('status')}\\n"
                      "Check network, recipient, token, amount, and transaction hash. The system will not mark the order paid until verification succeeds.")
        else:
            body=(f"Payment notice received for order {ref}.\\n\\n"
                  "Reply with the transaction hash and exact offer/order reference. "
                  "USDT must be sent on BNB Smart Chain (BEP-20). The system will not mark an order paid without independent on-chain verification.")
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

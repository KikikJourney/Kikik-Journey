#!/usr/bin/env python3
"""Read-only verifier for exact USDT transfers on BNB Smart Chain."""
import argparse, json, os, re, urllib.request
from decimal import Decimal, InvalidOperation

DEFAULT_RPC = "https://bsc-dataseed.bnbchain.org"
DEFAULT_USDT = "0x55d398326f99059fF775485246999027B3197955"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def norm_address(value):
    value=(value or "").strip().lower()
    if not re.fullmatch(r"0x[a-f0-9]{40}", value): raise ValueError("invalid EVM address")
    return value

def norm_tx(value):
    value=(value or "").strip().lower()
    if not re.fullmatch(r"0x[a-f0-9]{64}", value): raise ValueError("invalid transaction hash")
    return value

def rpc(url, method, params):
    payload=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(url,data=payload,headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=30) as response: data=json.loads(response.read().decode())
    if data.get("error"): raise RuntimeError(data["error"].get("message","RPC error"))
    return data.get("result")

def topic_address(topic): return "0x"+topic[-40:].lower()

def verify_payment(tx_hash, expected_amount, recipient, rpc_url=DEFAULT_RPC, token_contract=DEFAULT_USDT, min_confirmations=12, expected_decimals=18):
    tx_hash=norm_tx(tx_hash); recipient=norm_address(recipient); token_contract=norm_address(token_contract)
    chain_id=int(rpc(rpc_url,"eth_chainId",[]),16)
    if chain_id != 56: return {"ok":False,"status":"wrong_chain","chain_id":chain_id}
    decimals=int(rpc(rpc_url,"eth_call",[{"to":token_contract,"data":"0x313ce567"},"latest"]),16)
    if decimals != expected_decimals: return {"ok":False,"status":"unexpected_token_decimals","decimals":decimals}
    try: expected=Decimal(str(expected_amount))
    except InvalidOperation as exc: raise ValueError("invalid expected amount") from exc
    if expected <= 0: raise ValueError("expected amount must be positive")
    expected_units=int(expected*(Decimal(10)**decimals))
    if Decimal(expected_units) != expected*(Decimal(10)**decimals): raise ValueError("expected amount precision exceeds token decimals")
    receipt=rpc(rpc_url,"eth_getTransactionReceipt",[tx_hash]); tx=rpc(rpc_url,"eth_getTransactionByHash",[tx_hash])
    if not receipt or not tx: return {"ok":False,"status":"not_found","tx_hash":tx_hash}
    if receipt.get("status") != "0x1": return {"ok":False,"status":"reverted","tx_hash":tx_hash}
    if norm_address(tx.get("to","")) != token_contract: return {"ok":False,"status":"wrong_contract","tx_to":tx.get("to"),"token_contract":token_contract}
    latest=int(rpc(rpc_url,"eth_blockNumber",[]),16); block_number=int(receipt["blockNumber"],16)
    confirmations=max(0,latest-block_number+1)
    matches=[]
    for log in receipt.get("logs",[]):
        if norm_address(log.get("address","")) != token_contract: continue
        topics=log.get("topics",[])
        if len(topics)<3 or topics[0].lower()!=TRANSFER_TOPIC: continue
        to_addr=topic_address(topics[2]); value=int(log.get("data","0x0"),16)
        if to_addr==recipient:
            matches.append({"from":topic_address(topics[1]),"to":to_addr,"value_units":value,"log_index":int(log.get("logIndex","0x0"),16)})
    exact=[m for m in matches if m["value_units"]==expected_units]
    if not exact:
        return {"ok":False,"status":"amount_or_recipient_mismatch","tx_hash":tx_hash,"expected_amount":str(expected_amount),"recipient":recipient,"observed_transfers_to_recipient":matches,"confirmations":confirmations}
    if confirmations < min_confirmations:
        return {"ok":False,"status":"insufficient_confirmations","tx_hash":tx_hash,"confirmations":confirmations,"required_confirmations":min_confirmations,"transfer":exact[0]}
    return {"ok":True,"status":"confirmed","tx_hash":tx_hash,"chain_id":chain_id,"token_contract":token_contract,"recipient":recipient,"amount":str(expected_amount),"decimals":decimals,"confirmations":confirmations,"transfer":exact[0]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--tx-hash",required=True); p.add_argument("--expected-amount",required=True)
    p.add_argument("--recipient",default=os.getenv("PAYMENT_RECIPIENT")); p.add_argument("--rpc-url",default=os.getenv("BSC_RPC_URL",DEFAULT_RPC))
    p.add_argument("--token-contract",default=os.getenv("USDT_BSC_CONTRACT",DEFAULT_USDT)); p.add_argument("--min-confirmations",type=int,default=int(os.getenv("BSC_MIN_CONFIRMATIONS","12")))
    a=p.parse_args()
    if not a.recipient: p.error("--recipient or PAYMENT_RECIPIENT is required")
    result=verify_payment(a.tx_hash,a.expected_amount,a.recipient,a.rpc_url,a.token_contract,a.min_confirmations)
    print(json.dumps(result,indent=2,sort_keys=True)); raise SystemExit(0 if result["ok"] else 2)

if __name__=="__main__": main()

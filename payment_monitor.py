import base64
import json
import os
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = os.getenv("GITHUB_REPOSITORY", "KikikJourney/Kikik-Journey")
STATE_PATH = "runtime/payment-state.json"
STATE_BRANCH = os.getenv("STATE_BRANCH", "bot-state")
WALLET = os.getenv("USDT_BEP20_WALLET", "0x4ce7004e7127f8b2386eb355e088f127c24b3fac").lower()
USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955".lower()
USDT_DECIMALS = 18
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a2b4f0a4c3"
INITIAL_LOOKBACK_BLOCKS = int(os.getenv("INITIAL_LOOKBACK_BLOCKS", "2500"))
MAX_BLOCK_RANGE = int(os.getenv("MAX_BLOCK_RANGE", "1800"))
RPC_URLS = [x.strip() for x in os.getenv(
    "BSC_RPC_URLS",
    "https://bsc-dataseed.binance.org,https://bsc-dataseed1.defibit.io,https://bsc-dataseed1.ninicoin.io"
).split(",") if x.strip()]

def rpc_call(url, method, params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "KikikJourney-Revenue-Engine/1.0"})
    with urlopen(request, timeout=20) as response:
        data = json.load(response)
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")

def rpc(method, params):
    last_error = None
    for url in RPC_URLS:
        for attempt in range(2):
            try:
                return rpc_call(url, method, params)
            except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
                last_error = exc
                time.sleep(1 + attempt)
    raise RuntimeError(f"All configured BSC RPC endpoints failed: {last_error}")

def hex_int(value):
    return int(value, 16) if isinstance(value, str) else int(value)

def wallet_topic(address):
    return "0x" + address.lower().removeprefix("0x").rjust(64, "0")

def decode_transfer(log):
    topics = log.get("topics") or []
    if len(topics) < 3 or topics[0].lower() != TRANSFER_TOPIC:
        return None
    recipient = "0x" + topics[2][-40:].lower()
    if recipient != WALLET:
        return None
    amount = hex_int(log.get("data", "0x0")) / (10 ** USDT_DECIMALS)
    sender = "0x" + topics[1][-40:].lower()
    return {
        "transaction_hash": log.get("transactionHash"),
        "block_number": hex_int(log.get("blockNumber", "0x0")),
        "sender": sender,
        "recipient": WALLET,
        "amount_usdt": amount,
    }

def load_state(token):
    url = f"https://api.github.com/repos/{REPO}/contents/{STATE_PATH}?ref={STATE_BRANCH}"
    request = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "KikikJourney-Revenue-Engine/1.0",
    })
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    content = base64.b64decode(payload["content"]).decode()
    return json.loads(content), payload["sha"]

def save_state(token, state, sha):
    content = base64.b64encode((json.dumps(state, indent=2, ensure_ascii=False) + "\n").encode()).decode()
    url = f"https://api.github.com/repos/{REPO}/contents/{STATE_PATH}"
    payload = json.dumps({
        "message": "chore: update revenue engine payment state",
        "content": content,
        "branch": STATE_BRANCH,
        "sha": sha,
    }).encode()
    request = Request(url, data=payload, method="PUT", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "KikikJourney-Revenue-Engine/1.0",
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)

def create_payment_issue(token, transfers, balance):
    if not transfers:
        return None
    lines = [
        "<!-- kikikjourney-revenue-engine:payment -->",
        "# Verified USDT payment received",
        "",
        f"Wallet: {WALLET}",
        f"Current USDT balance: {balance:.6f} USDT",
        "",
        "New incoming transfers:",
    ]
    for item in transfers:
        lines += [
            f"- {item['amount_usdt']:.6f} USDT — {item['transaction_hash']}",
            f"  - block: {item['block_number']}",
            f"  - sender: {item['sender']}",
        ]
    lines += [
        "",
        "Verified from an on-chain BEP-20 Transfer event to the configured receiving wallet.",
    ]
    url = f"https://api.github.com/repos/{REPO}/issues"
    payload = json.dumps({
        "title": f"Payment received — {sum(x['amount_usdt'] for x in transfers):.6f} USDT",
        "body": "\n".join(lines),
        "labels": ["payment", "revenue"],
    }).encode()
    request = Request(url, data=payload, method="POST", headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "KikikJourney-Revenue-Engine/1.0",
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)

def get_balance():
    data = rpc("eth_call", [{"to": USDT_CONTRACT, "data": "0x70a08231" + WALLET.removeprefix("0x").rjust(64, "0")}, "latest"])
    return hex_int(data) / (10 ** USDT_DECIMALS)

def main():
    token = os.environ["GITHUB_TOKEN"]
    state, sha = load_state(token)
    latest = hex_int(rpc("eth_blockNumber", []))
    start = int(state.get("last_scanned_block", 0))
    if start <= 0:
        start = max(0, latest - INITIAL_LOOKBACK_BLOCKS)
    start += 1

    transfers = []
    seen = set(state.get("seen_transaction_hashes", []))
    cursor = start
    while cursor <= latest:
        end = min(cursor + MAX_BLOCK_RANGE - 1, latest)
        logs = rpc("eth_getLogs", [{
            "fromBlock": hex(cursor),
            "toBlock": hex(end),
            "address": USDT_CONTRACT,
            "topics": [TRANSFER_TOPIC, None, wallet_topic(WALLET)],
        }])
        for log in logs or []:
            item = decode_transfer(log)
            tx = item and item.get("transaction_hash")
            if item and tx and tx not in seen:
                transfers.append(item)
                seen.add(tx)
        cursor = end + 1

    balance = get_balance()
    state.update({
        "version": 1,
        "last_scanned_block": latest,
        "seen_transaction_hashes": list(seen)[-500:],
        "total_verified_usdt": round(float(state.get("total_verified_usdt", 0)) + sum(x["amount_usdt"] for x in transfers), 6),
        "last_verified_at": datetime.now(timezone.utc).isoformat() if transfers else state.get("last_verified_at"),
        "last_balance_usdt": round(balance, 6),
    })
    save_state(token, state, sha)

    if transfers:
        create_payment_issue(token, transfers, balance)

    print(json.dumps({
        "latest_block": latest,
        "new_payments": len(transfers),
        "new_usdt": round(sum(x["amount_usdt"] for x in transfers), 6),
        "wallet_balance_usdt": round(balance, 6),
    }, indent=2))

if __name__ == "__main__":
    main()

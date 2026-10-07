#!/usr/bin/env python3
"""Kikik Journey autonomous resolution engine.

The engine separates planning, bounded execution, verification, recovery, and
escalation. It never treats an LLM/customer statement as proof of resolution.
External write actions require an explicitly registered adapter; unsupported or
unauthorized writes fail closed.
"""
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse


class ResolutionError(Exception):
    pass


@dataclass(frozen=True)
class ActionResult:
    action_id: str
    status: str
    evidence: Dict[str, Any]
    retryable: bool = False
    message: str = ""


def _safe_public_url(url: str) -> str:
    value = (url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ResolutionError("only public http/https URLs are allowed")
    if parsed.port not in (None, 80, 443):
        raise ResolutionError("non-standard ports are not allowed")
    host = parsed.hostname
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ResolutionError("hostname cannot be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ResolutionError("private, loopback, link-local, reserved, or non-public address blocked")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect blocked", headers, fp)


def public_url_probe(url: str, timeout: int = 10) -> ActionResult:
    safe_url = _safe_public_url(url)
    request = urllib.request.Request(
        safe_url,
        headers={"User-Agent": "KikikJourney-ResolutionVerifier/1.0", "Accept": "text/html,application/json,*/*"},
        method="GET",
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return ActionResult(
                "public_url_probe",
                "EXECUTED",
                {
                    "url": safe_url,
                    "status_code": response.status,
                    "content_sample_length": len(body),
                    "content_type": response.headers.get("Content-Type", ""),
                },
                message="public endpoint reached",
            )
    except urllib.error.HTTPError as exc:
        return ActionResult(
            "public_url_probe",
            "EXECUTED",
            {"url": safe_url, "status_code": exc.code},
            retryable=exc.code in {408, 429, 500, 502, 503, 504},
            message=f"HTTP {exc.code}",
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return ActionResult(
            "public_url_probe",
            "FAILED",
            {"url": safe_url, "error_type": type(exc).__name__},
            retryable=True,
            message="public endpoint could not be reached",
        )


class ActionRegistry:
    def __init__(self):
        self._actions: Dict[str, Callable[..., ActionResult]] = {
            "public_url_probe": public_url_probe,
        }

    def register(self, action_id: str, handler: Callable[..., ActionResult]) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", action_id):
            raise ValueError("invalid action id")
        self._actions[action_id] = handler

    def execute(self, action_id: str, **kwargs: Any) -> ActionResult:
        handler = self._actions.get(action_id)
        if handler is None:
            return ActionResult(action_id, "BLOCKED", {}, False, "no registered adapter")
        return handler(**kwargs)


def _extract_urls(text: str):
    return re.findall(r"https?://\S+", text or "", re.I)


def build_plan(problem: Dict[str, Any]) -> Dict[str, Any]:
    category = problem.get("category", "unknown")
    evidence = problem.get("evidence", [])
    urls = [u.rstrip(".,);") for u in _extract_urls(" ".join(map(str, evidence)))]
    actions = []
    if category == "payment":
        actions.append({"id": "payment_verify", "mode": "existing_verified_adapter", "requires": ["tx_hash", "amount"]})
    elif urls:
        actions.append({"id": "public_url_probe", "mode": "read_only", "url": urls[0]})
    elif category in {"automation", "ecommerce", "spreadsheet_data", "whatsapp", "integration"}:
        actions.append({"id": "customer_connector_execution", "mode": "blocked_until_authorized_adapter"})
    else:
        actions.append({"id": "evidence_collection", "mode": "read_only"})
    return {
        "plan_version": "2",
        "category": category,
        "actions": actions,
        "execution_policy": {
            "fail_closed": True,
            "no_secret_collection": True,
            "no_unverified_completion": True,
            "writes_require_registered_adapter": True,
        },
    }


def verify_action(result: ActionResult) -> Dict[str, Any]:
    if result.status == "EXECUTED" and result.action_id == "public_url_probe":
        code = int(result.evidence.get("status_code", 0))
        ok = 200 <= code < 400
        return {"verified": ok, "reason": "public endpoint healthy" if ok else f"HTTP status {code}"}
    if result.status == "EXECUTED":
        return {"verified": False, "reason": "no independent verifier registered"}
    return {"verified": False, "reason": result.message or result.status.lower()}


def resolve(problem: Dict[str, Any], registry: Optional[ActionRegistry] = None, max_retries: int = 1) -> Dict[str, Any]:
    registry = registry or ActionRegistry()
    plan = build_plan(problem)
    attempts = []
    final_status = "BLOCKED"
    verification = {"verified": False, "reason": "no action executed"}
    for action in plan["actions"]:
        action_id = action["id"]
        if action_id != "public_url_probe":
            attempts.append({
                "action_id": action_id,
                "status": "BLOCKED",
                "attempt": 1,
                "message": "No customer-system write adapter is registered; execution fails closed.",
            })
            final_status = "ESCALATED"
            continue
        for attempt in range(1, max_retries + 2):
            result = registry.execute(action_id, url=action["url"])
            attempts.append({
                "action_id": result.action_id,
                "status": result.status,
                "attempt": attempt,
                "evidence": result.evidence,
                "message": result.message,
            })
            verification = verify_action(result)
            if verification["verified"]:
                final_status = "RESOLVED"
                break
            if not result.retryable or attempt > max_retries:
                final_status = "RECOVERY_REQUIRED"
                break
        if final_status == "RESOLVED":
            break
    return {
        "engine": "Kikik Journey Autonomous Resolution Engine v2",
        "status": final_status,
        "plan": plan,
        "attempts": attempts,
        "verification": verification,
        "recovery": {
            "required": final_status in {"RECOVERY_REQUIRED", "ESCALATED"},
            "next_step": "retry_with_new_evidence_or_escalate_with_full_case_context"
            if final_status != "RESOLVED" else None,
        },
        "policy": plan["execution_policy"],
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as handle:
        problem = json.load(handle)
    result = resolve(problem)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "verified": result["verification"]["verified"]}))


if __name__ == "__main__":
    main()

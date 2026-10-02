"""Minimal OpenAI-compatible client for optional 9Router integration.

The application remains fully functional without 9Router. Set AI_ROUTER_BASE_URL
(or 9ROUTER_BASE_URL) to an OpenAI-compatible /v1 endpoint when a running
9Router instance is available.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def base_url():
    value = os.getenv("AI_ROUTER_BASE_URL") or os.getenv("9ROUTER_BASE_URL")
    if not value:
        return None
    return value.rstrip("/") + "/chat/completions"


def configured():
    return base_url() is not None


def chat(messages, model=None, temperature=0.2, timeout=60):
    """Send one chat-completions request through 9Router/OpenAI-compatible API."""
    endpoint = base_url()
    if not endpoint:
        raise RuntimeError("9Router is not configured: set AI_ROUTER_BASE_URL or 9ROUTER_BASE_URL")

    payload = {
        "model": model or os.getenv("AI_ROUTER_MODEL", "kr/claude-sonnet-4.5"),
        "messages": messages,
        "temperature": temperature,
    }
    api_key = os.getenv("AI_ROUTER_API_KEY") or os.getenv("9ROUTER_API_KEY") or "9router"
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key,
            "User-Agent": "KikikJourney-AI-Opportunity-Lab/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AI router request failed: {exc}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("AI router returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("AI router response has no text content")
    return content


if __name__ == "__main__":
    print("9Router configured:", configured())
    print("Endpoint:", base_url() or "(not configured)")

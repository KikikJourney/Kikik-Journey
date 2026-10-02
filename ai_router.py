"""Minimal OpenAI-compatible client for optional 9Router integration.

The application remains fully functional without 9Router. The router can be
configured with either NINEROUTER_* (9Router-native) or AI_ROUTER_* variables.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _raw_base_url():
    return (
        os.getenv("AI_ROUTER_BASE_URL")
        or os.getenv("9ROUTER_BASE_URL")
        or os.getenv("NINEROUTER_URL")
    )


def base_url():
    value = _raw_base_url()
    if not value:
        return None
    value = value.rstrip("/")
    if value.endswith("/chat/completions"):
        return value
    if value.endswith("/v1"):
        return value + "/chat/completions"
    return value + "/v1/chat/completions"


def configured():
    return base_url() is not None


def model():
    return (
        os.getenv("AI_ROUTER_MODEL")
        or os.getenv("9ROUTER_MODEL")
        or os.getenv("NINEROUTER_MODEL")
        or "kr/claude-sonnet-4.5"
    )


def api_key():
    return (
        os.getenv("AI_ROUTER_API_KEY")
        or os.getenv("9ROUTER_API_KEY")
        or os.getenv("NINEROUTER_KEY")
        or "9router"
    )


def models(timeout=20):
    """Return OpenAI-compatible models exposed by the configured router."""
    root = base_url()
    if not root:
        raise RuntimeError(
            "9Router is not configured: set AI_ROUTER_BASE_URL or NINEROUTER_URL"
        )
    endpoint = root.rsplit("/chat/completions", 1)[0].rsplit("/v1", 1)[0] + "/v1/models"
    request = Request(
        endpoint,
        headers={
            "Authorization": "Bearer " + api_key(),
            "User-Agent": "KikikJourney-AI-Opportunity-Lab/1.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AI router model discovery failed: {exc}") from exc
    return data.get("data") or []


def chat(messages, model_name=None, temperature=0.2, timeout=60):
    """Send one chat-completions request through 9Router/OpenAI-compatible API."""
    endpoint = base_url()
    if not endpoint:
        raise RuntimeError(
            "9Router is not configured: set AI_ROUTER_BASE_URL or NINEROUTER_URL"
        )

    payload = {
        "model": model_name or model(),
        "messages": messages,
        "temperature": temperature,
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key(),
            "User-Agent": "KikikJourney-AI-Opportunity-Lab/1.1",
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
    print("Model:", model())

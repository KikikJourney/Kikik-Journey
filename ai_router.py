"""Small OpenAI-compatible AI client with optional 9Router or hosted OpenRouter.

9Router remains supported for self-hosted deployments. OpenRouter can be used
directly from GitHub Actions with one API key, so no computer or VPS is needed.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _raw_base_url():
    return (
        os.getenv("AI_ROUTER_BASE_URL")
        or os.getenv("9ROUTER_BASE_URL")
        or os.getenv("NINEROUTER_URL")
        or (OPENROUTER_BASE if os.getenv("OPENROUTER_API_KEY") else None)
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
        or os.getenv("OPENROUTER_MODEL")
        or ("openrouter/free" if os.getenv("OPENROUTER_API_KEY") else "kr/claude-sonnet-4.5")
    )


def api_key():
    return (
        os.getenv("AI_ROUTER_API_KEY")
        or os.getenv("9ROUTER_API_KEY")
        or os.getenv("NINEROUTER_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or "9router"
    )


def _models_endpoint():
    root = base_url()
    if not root:
        return None
    return root.rsplit("/chat/completions", 1)[0].rsplit("/v1", 1)[0] + "/v1/models"


def models(timeout=20):
    """Return OpenAI-compatible models exposed by the configured provider."""
    endpoint = _models_endpoint()
    if not endpoint:
        raise RuntimeError("AI provider is not configured")
    request = Request(
        endpoint,
        headers={
            "Authorization": "Bearer " + api_key(),
            "User-Agent": "KikikJourney-AI-Opportunity-Lab/1.2",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AI provider model discovery failed: {exc}") from exc
    return data.get("data") or []


def chat(messages, model_name=None, temperature=0.2, timeout=60):
    """Send one OpenAI-compatible chat-completions request."""
    endpoint = base_url()
    if not endpoint:
        raise RuntimeError(
            "AI provider is not configured: set OPENROUTER_API_KEY, "
            "AI_ROUTER_BASE_URL, or NINEROUTER_URL"
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
            "User-Agent": "KikikJourney-AI-Opportunity-Lab/1.2",
            "HTTP-Referer": "https://github.com/KikikJourney/Kikik-Journey",
            "X-Title": "KikikJourney AI Opportunity Lab",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AI provider request failed: {exc}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("AI provider returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise RuntimeError("AI provider response has no text content")
    return content


if __name__ == "__main__":
    print("AI provider configured:", configured())
    print("Endpoint:", base_url() or "(not configured)")
    print("Model:", model())

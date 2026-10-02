# 9Router integration

AI Opportunity Lab supports an optional OpenAI-compatible AI router. The
recommended local router is [9Router](https://github.com/decolua/9router).

## Architecture

```
AI Opportunity Lab
        |
        v
  OpenAI-compatible client
        |
        v
9Router /v1/chat/completions
        |
        +--> subscription provider
        +--> cheap provider
        +--> free provider
```

9Router's documented default API endpoint is `http://localhost:20128/v1`.
The application does **not** hard-code localhost, because GitHub Actions cannot
reach a router running on your phone or PC.

## Configuration

For a local 9Router instance:

```text
AI_ROUTER_BASE_URL=http://localhost:20128/v1
AI_ROUTER_MODEL=kr/claude-sonnet-4.5
AI_ROUTER_API_KEY=<key shown by 9Router dashboard>
```

Equivalent `9ROUTER_BASE_URL` and `9ROUTER_API_KEY` variables are accepted.

For GitHub Actions, use a reachable 9Router deployment URL and store the URL
and key as GitHub Actions secrets. Never commit the key.

## Important

This is an **optional AI layer**. The Opportunity Radar continues to work
without 9Router. 9Router is not required for the public sales site and is not
exposed to customers.

Source/reference: https://github.com/decolua/9router

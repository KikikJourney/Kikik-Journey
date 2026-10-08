# External web evidence and social distribution

## Firecrawl
Firecrawl is an optional evidence-enrichment layer for the business prospect pipeline.
- Secret: `FIRECRAWL_API_KEY`
- Optional endpoint: `FIRECRAWL_API_URL`
- Enriches only actionable prospects with a public business email.
- Evidence only: it never changes deterministic score or qualification gates.
- Missing credentials disable enrichment cleanly; per-prospect provider failures are recorded.
- Public HTTP(S) destinations only; localhost/private IP destinations are rejected.


No provider SDK is added to the Python runtime; the integration surface remains stdlib-only.

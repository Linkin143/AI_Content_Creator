# Skill: social_publishing

## Purpose
Publish an APPROVED draft to X or LinkedIn through official APIs, or fall back to
a fully usable manual workflow when API access is unavailable.

## Required inputs
- An approved draft id + version with a valid approval record.
- A valid, active social connection (encrypted tokens).

## Available tools
- `publish_to_x(draft)` / `publish_to_linkedin(draft)` - official API calls.
- `manual_fallback(draft)` - save + copyable text + official compose link.
- `record_result(...)` - persist publish_post_id / status / response.

## Operational constraints
- Only publish drafts that are APPROVED for the exact version being published.
- Idempotent: never publish the same draft+version twice; check first.
- Never retry a potentially-successful request blindly (unknown outcome -> stop
  and ask a human).
- Handle 401/403/429/timeouts/expired credentials explicitly.
- If the API plan does not permit posting, use manual fallback - do NOT attempt
  browser automation or undocumented endpoints.

## Error conditions
- Unauthorized/permission denied: preserve draft, notify owner, offer manual.
- Unknown result: mark as needs-human-check; do not mark PUBLISHED.

## When to run
- Only inside the authorization-controlled publishing workflow, after approval
  (immediate "Publish Now" or a due scheduled job).

## When NOT to run
- Never from the research graph. Never without human authorization.

## Rules preventing unsupported claims
- Never report success unless the API confirmed it. Store the real response.

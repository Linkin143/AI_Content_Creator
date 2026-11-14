# Skill: performance_analysis

## Purpose
Collect available engagement statistics for published posts and generate daily
and weekly summaries of activity.

## Required inputs
- Published posts (ids, platform, timestamps).
- Engagement metrics where the platform/API exposes them.

## Available tools
- `fetch_engagement_metrics(post)` - pull likes/comments/shares/impressions if
  the connected API permits.
- `generate_summary(period)` - daily/weekly rollup.

## Operational constraints
- Do not assume unrestricted analytics access (especially LinkedIn personal
  profiles). Missing metrics stay empty, not fabricated.
- Report real numbers only.

## Error conditions
- Metrics unavailable: record zero/empty with a note; never invent values.

## When to run
- On a schedule after posts are live, and for digest generation.

## When NOT to run
- Never to estimate or fabricate engagement that the API did not return.

## Rules preventing unsupported claims
- Never invent billing, impressions or reach figures.

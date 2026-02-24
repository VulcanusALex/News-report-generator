---
name: milan-news-briefing
description: Generate a mature daily Milan news brief in Chinese using Python with weather, 20-day strike check, Italian media headlines, world news, AI news, and Milan events; persist daily outputs with dedup so next-day reports avoid repeats; manage RSS/API source pipelines. Use when the user asks to create, run, debug, or extend the Milan briefing workflow, especially for OpenClaw skill-style automation.
---

Run the briefing pipeline and manage sources with deterministic scripts.

## Execute Daily Brief

1. Ensure dependencies are installed:
`python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2. Generate report:
`python -m src.news_briefing.main`
3. Use dry run for debugging:
`python -m src.news_briefing.main --dry-run`
4. Default report date follows config timezone (`Europe/Rome`) when `--date` is omitted.
5. Agent can choose layout/order at call time:
`python skills/milan-news-briefing/scripts/run_briefing.py --layout editorial --section-order weather,strikes,ai_news,world_news,italian_news,milan_events`
6. Agent can request JSON output for post-processing:
`python skills/milan-news-briefing/scripts/run_briefing.py --output-format json`

## Manage Source Pipelines

Use `scripts/manage_sources.py` in this skill folder.

1. List configured sources:
`python skills/milan-news-briefing/scripts/manage_sources.py list`
`python skills/milan-news-briefing/scripts/manage_sources.py --json list`
2. Add RSS source:
`python skills/milan-news-briefing/scripts/manage_sources.py add --section ai_news --name "Example AI" --type rss --url "https://example.com/rss.xml"`
3. Add JSON API source with parser:
`python skills/milan-news-briefing/scripts/manage_sources.py add --section strikes --name "Strike API" --type json --url "https://example.com/strikes" --parser italy_transport_strikes_v1`
4. Add HTML source (for parser using webpage table):
`python skills/milan-news-briefing/scripts/manage_sources.py add --section strikes --name "Strike HTML" --type html --url "https://example.com/strikes-page" --parser italy_mit_strikes_html_v1`
4. Remove source by exact name:
`python skills/milan-news-briefing/scripts/manage_sources.py remove --section world_news --name "BBC World"`

## Daily Ops

Use `scripts/daily_ops.py` for daily automation.

1. Run once with precheck + auto degrade + retry:
`python skills/milan-news-briefing/scripts/daily_ops.py --auto-degrade --max-retries 2 --retry-delay 120`
2. Run once and send fail alert:
`python skills/milan-news-briefing/scripts/daily_ops.py --auto-degrade --alert-webhook "https://example.com/webhook"`
3. Print cron line (7:00 daily):
`python skills/milan-news-briefing/scripts/daily_ops.py --print-cron --cron-hour 7 --cron-minute 0`
4. Optional success alert:
`python skills/milan-news-briefing/scripts/daily_ops.py --alert-webhook "https://example.com/webhook" --alert-success`
5. Skip precheck explicitly (not recommended):
`python skills/milan-news-briefing/scripts/daily_ops.py --skip-precheck`

## Cron Scheduling

Use `scripts/manage_cron.py` to manage one tagged cron entry.

1. Install/replace 07:00 daily run:
`python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0`
`python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0 --timezone Europe/Rome`
`python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0 --timezone Europe/Rome --layout editorial --output-format markdown`
2. Install with webhook:
`python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0 --webhook "https://example.com/webhook"`
3. Show current managed entry:
`python skills/milan-news-briefing/scripts/manage_cron.py show`
`python skills/milan-news-briefing/scripts/manage_cron.py --json show`
4. Remove managed entry:
`python skills/milan-news-briefing/scripts/manage_cron.py remove`

## Health Check And Validation

1. Check all configured sources:
`python skills/milan-news-briefing/scripts/check_feeds.py --timeout 12 --write-report output/logs/feed-health.json`
2. Validate full stack locally:
`python skills/milan-news-briefing/scripts/validate_stack.py --skip-network`
3. Validate with network checks:
`python skills/milan-news-briefing/scripts/validate_stack.py`

## Operate Safely

1. Keep configuration in `config/sources.yaml` as source-of-truth.
2. Keep strike source URL non-empty if real strike monitoring is required.
3. Keep per-section `count` at 5 for stable daily format unless user asks otherwise.
4. Preserve SQLite database `data/briefing.db`; do not clear it unless user asks to reset dedup history.
5. Check `output/logs/` after failures and use webhook payload `tail` for quick triage.
6. Use `--auto-degrade` in production cron to bypass temporary source outages.
7. Prefer `--json` flags on management scripts when an agent needs machine-readable state.

## Extend Parsers

1. Add parser logic in `src/news_briefing/parse.py`.
2. Register parser in `src/news_briefing/pipeline.py` parser maps.
3. Reference parser key in `config/sources.yaml` source item.

Read `references/source_schema.md` before adding JSON-based sources.

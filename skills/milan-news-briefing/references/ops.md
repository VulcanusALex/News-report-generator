# Ops Quick Reference

## Log path

- Per run log: `output/logs/daily-ops-YYYYmmdd-HHMMSS.log`
- Cron merged log (if using printed cron line): `output/logs/cron.log`
- Feed health report (optional): `output/logs/feed-health.json`
- Auto-degraded runtime config: `output/runtime_configs/degraded-*.yaml`

## Alert payload

`daily_ops.py` sends JSON to webhook URL.

Success payload fields:
- `status`
- `attempt`
- `attempts_total`
- `log_file`
- `date`

Failure payload fields:
- `status`
- `attempt`
- `attempts_total`
- `log_file`
- `date`
- `tail` (last 1500 chars of process logs)

## Typical production command

```bash
python skills/milan-news-briefing/scripts/daily_ops.py \
  --auto-degrade \
  --max-retries 2 \
  --retry-delay 180 \
  --alert-webhook "https://example.com/webhook"
```

## Cron install/remove

```bash
python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0 --timezone Europe/Rome
python skills/milan-news-briefing/scripts/manage_cron.py show
python skills/milan-news-briefing/scripts/manage_cron.py --json show
python skills/milan-news-briefing/scripts/manage_cron.py remove
```

`manage_cron.py` writes a tagged `CRON_TZ=Europe/Rome` line so schedule time is interpreted in Milan timezone.
`manage_cron.py install` also supports `--layout`, `--section-order`, and `--output-format` for agent-controlled rendering.

## Preflight check command

```bash
python skills/milan-news-briefing/scripts/check_feeds.py \
  --timeout 12 \
  --write-report output/logs/feed-health.json
```

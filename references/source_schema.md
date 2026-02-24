# Source Schema

Use `config/sources.yaml` as canonical source registry.

## Render config

```yaml
render:
  default_layout: classic|editorial|brief
  section_order:
    - weather
    - strikes
    - italian_news
    - world_news
    - ai_news
    - milan_events
```

## Section shape

Each news section (`italian_news`, `world_news`, `ai_news`, `milan_events`) uses:

```yaml
<section>:
  count: 5
  only_today: true|false
  fallback_days: 2
  sources:
    - name: string
      type: rss|json|html
      url: https://...
      parser: optional-parser-key
```

## Supported parser keys

- News JSON: `generic_json_news_v1`
- Strike RSS: `italy_mit_strikes_rss_v1`
- Strike HTML: `italy_mit_strikes_html_v1`
- Strike JSON: `italy_transport_strikes_v1`

## Strike JSON expected fields

```json
{
  "title": "National rail strike",
  "start": "2026-02-24T09:00:00+01:00",
  "end": "2026-02-24T17:00:00+01:00",
  "impact_window": "09:00-17:00",
  "city": "Milan"
}
```

Only strikes relevant to Milan (Milan/Milano, Lombardia, Italia/Tutte, or empty city) inside next 20 days are included.

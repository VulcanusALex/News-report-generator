# Milan Daily News Brief (Python)

一个纯 Python 的每日新闻简报生成器，默认输出中文 Markdown，覆盖：

1. 米兰天气（当天）
2. 未来 20 天米兰相关罢工（无则明确显示无）
3. 意大利传统媒体当日新闻（5 条）
4. 国际知名媒体世界新闻（5 条）
5. AI 相关新闻（5 条）
6. 米兰近期有意思活动（5 条）

系统特性：

- `config/sources.yaml` 中集中管理新闻/API/RSS 源
- 支持新增/替换源，不改业务代码
- SQLite 去重：昨天出现过的新闻，今天默认不会重复
- 结果按天落盘，便于审计与二次处理
- 结构适合 AI agent（如 OpenClaw）接管和扩展

## 2026-02-24 更新

### 米兰活动数据源改进
- 新增 web_search 支持，不再依赖失效的 RSS 源
- 新增 fetch_web_search() 和 _fetch_ddg_search() 函数（src/news_briefing/fetch.py）
- 新增 parse_web_search_results() 解析器（src/news_briefing/parse.py）
- pipeline.py 新增 "search" 类型支持
- config/sources.yaml 中 milan_events 改为使用 web search
- 搜索关键词示例: "Milano mostre arte febbraio marzo 2026"

### AI 新闻标题优化
- AI 新闻板块标题改为 "🤖 AI 研究动态"

## OpenClaw Skill

已提供可直接给 agent 使用的 skill 目录：

- `skills/milan-news-briefing/SKILL.md`
- `skills/milan-news-briefing/scripts/run_briefing.py`
- `skills/milan-news-briefing/scripts/manage_sources.py`

常用调用：

```bash
python skills/milan-news-briefing/scripts/run_briefing.py
python skills/milan-news-briefing/scripts/run_briefing.py --dry-run
python skills/milan-news-briefing/scripts/run_briefing.py --layout editorial --section-order weather,strikes,ai_news,world_news,italian_news,milan_events
python skills/milan-news-briefing/scripts/run_briefing.py --output-format json
python skills/milan-news-briefing/scripts/manage_sources.py list
python skills/milan-news-briefing/scripts/manage_sources.py --json list
python skills/milan-news-briefing/scripts/check_feeds.py --timeout 12 --write-report output/logs/feed-health.json
python skills/milan-news-briefing/scripts/daily_ops.py --auto-degrade --max-retries 2 --retry-delay 180
python skills/milan-news-briefing/scripts/daily_ops.py --auto-degrade --alert-webhook "https://example.com/webhook"
python skills/milan-news-briefing/scripts/daily_ops.py --print-cron --cron-hour 7 --cron-minute 0
python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0 --timezone Europe/Rome
python skills/milan-news-briefing/scripts/manage_cron.py install --hour 7 --minute 0 --timezone Europe/Rome --layout editorial
python skills/milan-news-briefing/scripts/manage_cron.py show
python skills/milan-news-briefing/scripts/manage_cron.py --json show
python skills/milan-news-briefing/scripts/manage_cron.py remove
python skills/milan-news-briefing/scripts/validate_stack.py --skip-network
```

## 1. 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 使用

```bash
python -m src.news_briefing.main
```

不传 `--date` 时，系统默认按 `config/sources.yaml` 的 `timezone`（默认 `Europe/Rome`）计算“今天”。

可选排版风格：`classic`、`editorial`、`brief`。可通过 `--layout` 和 `--section-order` 让 Agent 动态决定版式。

默认输出到：

- `output/YYYY-MM-DD.md`：日报正文
- `output/runs/YYYY-MM-DD.json`：结构化结果
- `data/briefing.db`：去重与运行记录数据库

常用参数：

```bash
python -m src.news_briefing.main --date 2026-02-23
python -m src.news_briefing.main --dry-run
python -m src.news_briefing.main --config config/sources.yaml
```

## 3. 配置说明

配置文件：`config/sources.yaml`

- `weather`：天气 provider（当前为 Open-Meteo）
- `strikes`：罢工源（支持 JSON/API；可继续加 RSS/HTML parser）
- `italian_news` / `world_news` / `ai_news` / `milan_events`：各自新闻源与条数

默认 `world_news` 推荐源（已预置）：

- BBC World
- The Guardian World
- New York Times World
- NPR World
- Al Jazeera

### 添加新源（RSS）

在对应 section 的 `sources` 增加：

```yaml
- name: Example Feed
  type: rss
  url: https://example.com/rss.xml
```

### 添加新源（JSON API）

```yaml
- name: Example API
  type: json
  url: https://example.com/api/news
  parser: generic_json_news_v1
```

如果是自定义字段结构，新增 parser 函数并在 `PARSERS` 注册即可。

## 4. 罢工数据源说明

默认配置已接入意大利官方交通罢工源（MIT）：

- RSS: `https://scioperi.mit.gov.it/mit2/public/scioperi/rss`
- 网页兜底: `https://scioperi.mit.gov.it/mit2/public/scioperi`

默认 parser：

- `italy_mit_strikes_rss_v1`
- `italy_mit_strikes_html_v1`
- `italy_transport_strikes_v1`（自定义 JSON API 兼容）

JSON 字段期望（可通过 parser 适配）：

- `title`
- `start`（ISO 日期/时间）
- `end`（ISO 日期/时间，可选）
- `impact_window`（可选）
- `city`（可选，用于筛选 Milan）

如果当天无法抓到有效罢工条目，将显示“未来 20 天暂无已确认罢工”。

## 5. 每日调度（macOS/Linux）

```bash
0 7 * * * cd "/path/to/project" && /path/to/project/.venv/bin/python -m src.news_briefing.main
```

## 6. 项目结构

```text
.
├── config/
│   └── sources.yaml
├── data/
├── output/
├── requirements.txt
└── src/news_briefing/
    ├── main.py
    ├── models.py
    ├── config.py
    ├── storage.py
    ├── fetch.py
    ├── parse.py
    ├── pipeline.py
    └── render.py
```

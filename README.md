# Milan Daily News Brief (Python)

米兰每日新闻简报生成器（Python）。默认输出中文 Markdown，覆盖天气、罢工、意大利/世界新闻、AI 新闻与米兰活动。

## 本次已同步改动

1. 米兰活动源新增 `web search` 支持（不再依赖失效 RSS）
- 新增 `fetch_web_search()` 与 `_fetch_ddg_search()`（`src/news_briefing/fetch.py`）
- 新增 `parse_web_search_results()`（`src/news_briefing/parse.py`）
- `pipeline.py` 新增 `type: search` 处理分支（`src/news_briefing/pipeline.py`）

2. `config/sources.yaml` 更新
- `milan_events` 改为搜索源
- 关键词示例：`Milano mostre arte febbraio marzo 2026`

3. AI 板块标题更新
- `src/news_briefing/render.py` 中 `ai_news` 标题改为：`🤖 AI 研究动态`

## 目录

```text
.
├── config/
│   └── sources.yaml
└── src/news_briefing/
    ├── fetch.py
    ├── parse.py
    ├── pipeline.py
    └── render.py
```

## 运行提示

当前仓库已同步上述改动文件；若要完整运行系统，还需要其余模块（如 `main.py`、`models.py`、`storage.py` 等）与依赖环境。

"""FastAPI 应用入口。

Phase 0：提供健康检查与一个 Model Router 演示端点，验证 Harness 装配。
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from shanhai_market_data import (
    AShareCompanySyncService,
    CompanyIntelligenceAPI,
    DEFAULT_A_SHARE_TARGETS,
)
from shanhai_market_data.factory import default_market_store, default_tushare_provider
from shanhai_model_router import ModelRegistry, ModelRouter
from shanhai_schemas import Message, Role, TaskType

app = FastAPI(title="ShanHai API", version="0.1.0")


def _build_router() -> ModelRouter:
    cfg = os.getenv(
        "MODEL_ROUTER_CONFIG",
        str(Path(__file__).resolve().parents[3] / "services" / "model-router" / "models.yaml"),
    )
    return ModelRouter(ModelRegistry.from_yaml(cfg))


router = _build_router()
market_store = default_market_store()
company_api = CompanyIntelligenceAPI(market_store)


class CompleteRequest(BaseModel):
    task: TaskType = TaskType.GENERAL
    prompt: str
    model: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "shanhai-api"}


@app.get("/models")
def models() -> dict:
    return {"models": router._registry.names(), "default": router._registry.default}


@app.post("/complete")
def complete(req: CompleteRequest) -> dict:
    result = router.complete(
        task=req.task,
        messages=[Message(role=Role.USER, content=req.prompt)],
        model=req.model,
    )
    return result.model_dump()


@app.get("/companies")
def list_companies(limit: int = 50) -> dict:
    return {"companies": list(company_api.list_companies(limit=limit))}


@app.get("/companies/search")
def search_companies(q: str, limit: int = 50) -> dict:
    return {"companies": list(company_api.search_companies(text=q, limit=limit))}


@app.get("/companies/{ts_code}")
def get_company(ts_code: str) -> dict:
    payload = company_api.get_company(ts_code)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"company not found: {ts_code}")
    return payload


@app.get("/companies/{ts_code}/timeline")
def get_company_timeline(
    ts_code: str,
    time_basis: str = "published_at",
    latest_first: bool = True,
) -> dict:
    payload = company_api.get_company_timeline(
        ts_code, time_basis=time_basis, latest_first=latest_first
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"company not found: {ts_code}")
    return payload


@app.post("/market/ingestion/tushare/run")
def run_tushare_ingestion() -> dict:
    service = AShareCompanySyncService(default_tushare_provider(), market_store)
    report = service.sync_companies(DEFAULT_A_SHARE_TARGETS)
    return report.model_dump(mode="json")


@app.get("/company/{ts_code}", response_class=HTMLResponse)
def company_detail_console(ts_code: str) -> str:
    """Console Alpha — a data-model validation page, not a product dashboard.

    It renders one company's identity (Company/ListedEntity/Security/Listing),
    industry, financial facts, announcements and the unified MarketFact timeline.
    If a section cannot be expressed naturally here, the model is wrong.
    """
    return _COMPANY_DETAIL_HTML.replace("__TS_CODE__", ts_code)


_COMPANY_DETAIL_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>ShanHai Company Detail Alpha</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1a1a1a; }
    h1 { margin-bottom: 2px; }
    h2 { margin-top: 28px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
    .muted { color: #888; }
    .grid { display: grid; grid-template-columns: 180px 1fr; gap: 6px 16px; }
    code { background: #f6f6f6; padding: 2px 4px; border-radius: 4px; }
    table { border-collapse: collapse; width: 100%; margin-top: 8px; }
    th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #eee; font-size: 14px; }
    th { color: #555; font-weight: 600; }
    .pill { display: inline-block; padding: 1px 8px; border-radius: 10px; background: #eef; font-size: 12px; color: #335; }
    .empty { color: #aaa; font-style: italic; }
    .basis { font-size: 12px; color: #888; }
  </style>
</head>
<body>
  <h1 id="title">加载中…</h1>
  <p class="muted" id="subtitle"></p>

  <h2>基本信息</h2>
  <div class="grid" id="basic"></div>

  <h2>证券关系 (Company → ListedEntity → Security → Listing)</h2>
  <div class="grid" id="identity"></div>

  <h2>行业</h2>
  <div class="grid" id="industry"></div>

  <h2>财务事实 (FinancialFact)</h2>
  <div id="financial"></div>

  <h2>公告时间线 (AnnouncementFact)</h2>
  <div id="announcements"></div>

  <h2>新闻时间线 (NewsFact)</h2>
  <div id="news"></div>

  <h2>MarketFact Timeline</h2>
  <div class="basis">排序基准: <span id="basis">published_at</span></div>
  <div id="timeline"></div>

  <script>
    const tsCode = "__TS_CODE__";

    function row(grid, label, value) {
      const k = document.createElement('div');
      k.textContent = label;
      const v = document.createElement('div');
      v.innerHTML = value;
      grid.appendChild(k);
      grid.appendChild(v);
    }

    function empty(el, text) {
      el.innerHTML = '<p class="empty">' + text + '</p>';
    }

    async function load() {
      const res = await fetch('/companies/' + encodeURIComponent(tsCode));
      if (!res.ok) {
        document.getElementById('title').textContent = '未找到公司: ' + tsCode;
        document.getElementById('subtitle').textContent = '请先运行 Tushare ingestion。';
        return;
      }
      const data = await res.json();
      renderBasic(data);
      renderIdentity(data);
      renderIndustry(data);
      renderFinancial(data.financial_facts || []);
      renderAnnouncements(data.announcement_facts || []);
      renderNews((data.facts || []).filter(f => f.fact_type === 'news'));
      await loadTimeline();
    }

    function renderBasic(d) {
      document.getElementById('title').innerHTML =
        d.company.name + ' <code>' + d.security.ts_code + '</code>';
      document.getElementById('subtitle').textContent =
        '只读公司认知视图 · 数据模型验证 (Console Alpha)';
      const g = document.getElementById('basic');
      g.innerHTML = '';
      row(g, '名称', d.company.name);
      row(g, '别名', (d.company.aliases || []).join(' / ') || '-');
      row(g, '地区', d.company.region || '-');
      row(g, '外部标识', (d.company.external_ids || []).map(x => '<code>' + x + '</code>').join(' ') || '-');
      const q = d.latest_quote || {};
      row(g, '最新收盘', q.close != null ? q.close + ' (' + (q.trade_date || '') + ')' : '-');
      row(g, '来源', (d.source_refs || []).map(s => s.source_name).join(', ') || '-');
    }

    function renderIdentity(d) {
      const g = document.getElementById('identity');
      g.innerHTML = '';
      row(g, 'Company', '<code>' + d.company.company_id + '</code>');
      row(g, 'ListedEntity', '<code>' + d.listed_entity.listed_entity_id + '</code>');
      row(g, 'Security', '<code>' + d.security.security_id + '</code> · ts_code <code>' + d.security.ts_code + '</code>');
      row(g, 'Listing', '<code>' + d.listing.listing_id + '</code> · ' + d.listing.exchange + ' / ' + d.listing.board);
      row(g, '上市状态', d.listing.status);
    }

    function renderIndustry(d) {
      const g = document.getElementById('industry');
      g.innerHTML = '';
      if (!d.industry) { empty(g, '无行业事实'); return; }
      row(g, '行业', d.industry.name);
      row(g, '分类体系', d.industry.taxonomy);
      row(g, 'Industry ID', '<code>' + d.industry.industry_id + '</code>');
    }

    function renderFinancial(facts) {
      const el = document.getElementById('financial');
      if (!facts.length) { empty(el, '暂无财务事实 (需 fina_indicator 数据源)'); return; }
      let html = '<table><tr><th>报告期</th><th>指标</th><th>数值</th><th>同比</th><th>来源</th><th>置信度</th></tr>';
      for (const f of facts) {
        html += '<tr><td>' + f.report_period + '</td><td>' + f.metric_name +
          '</td><td>' + (f.metric_value != null ? f.metric_value + ' ' + (f.unit || '') : '-') +
          '</td><td>' + (f.yoy != null ? f.yoy : '-') +
          '</td><td>' + (f.source_ref ? f.source_ref.source_name : '-') +
          '</td><td>' + f.confidence + '</td></tr>';
      }
      html += '</table>';
      el.innerHTML = html;
    }

    function renderAnnouncements(facts) {
      const el = document.getElementById('announcements');
      if (!facts.length) { empty(el, '暂无公告事实 (需 anns_d 数据源)'); return; }
      let html = '<table><tr><th>披露日期</th><th>类型</th><th>标题</th><th>链接</th></tr>';
      for (const f of facts) {
        const date = (f.published_at || '').slice(0, 10);
        const link = f.document_url ? '<a href="' + f.document_url + '" target="_blank">原文</a>' : '-';
        html += '<tr><td>' + date + '</td><td><span class="pill">' + f.announcement_type +
          '</span></td><td>' + (f.title || '-') + '</td><td>' + link + '</td></tr>';
      }
      html += '</table>';
      el.innerHTML = html;
    }

    function renderNews(facts) {
      const el = document.getElementById('news');
      if (!facts.length) { empty(el, '暂无新闻事实 (NewsFact 数据源尚未接入)'); return; }
      let html = '<table><tr><th>时间</th><th>标题</th><th>来源</th></tr>';
      for (const f of facts) {
        const date = (f.published_at || f.occurred_at || '').slice(0, 10);
        html += '<tr><td>' + date + '</td><td>' + f.object_value +
          '</td><td>' + (f.source_ref ? f.source_ref.source_name : '-') + '</td></tr>';
      }
      html += '</table>';
      el.innerHTML = html;
    }

    async function loadTimeline() {
      const res = await fetch('/companies/' + encodeURIComponent(tsCode) + '/timeline');
      const el = document.getElementById('timeline');
      if (!res.ok) { empty(el, '无时间线'); return; }
      const data = await res.json();
      document.getElementById('basis').textContent = data.time_basis;
      const events = data.events || [];
      if (!events.length) { empty(el, '时间线为空'); return; }
      let html = '<table><tr><th>时间</th><th>基准</th><th>类型</th><th>标题</th><th>摘要</th></tr>';
      for (const e of events) {
        const t = (e.event_time || '').slice(0, 10);
        html += '<tr><td>' + t + '</td><td class="basis">' + e.event_time_basis +
          '</td><td><span class="pill">' + e.event_type + '</span></td><td>' + e.title +
          '</td><td>' + (e.summary || '') + '</td></tr>';
      }
      html += '</table>';
      el.innerHTML = html;
    }

    load();
  </script>
</body>
</html>
"""


@app.get("/console/companies", response_class=HTMLResponse)
def company_console() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>ShanHai Company Intelligence Alpha</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; }
    h1 { margin-bottom: 4px; }
    .muted { color: #666; }
    input { padding: 8px; width: 260px; }
    button { padding: 8px 12px; margin-left: 8px; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-top: 16px; }
    .grid { display: grid; grid-template-columns: 160px 1fr; gap: 6px 12px; }
    code { background: #f6f6f6; padding: 2px 4px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Company Intelligence Alpha</h1>
  <p class="muted">只读公司认知视图：公司身份、证券、行业、最新日线事实与来源。</p>
  <div>
    <input id="query" value="贵州" />
    <button onclick="search()">搜索</button>
    <button onclick="loadAll()">全部</button>
  </div>
  <div id="results"></div>
  <script>
    async function loadAll() {
      const res = await fetch('/companies?limit=50');
      render((await res.json()).companies || []);
    }
    async function search() {
      const q = document.getElementById('query').value;
      const res = await fetch('/companies/search?q=' + encodeURIComponent(q));
      render((await res.json()).companies || []);
    }
    function render(items) {
      const root = document.getElementById('results');
      root.innerHTML = '';
      if (!items.length) {
        root.innerHTML = '<p class="muted">暂无数据，请先运行 Tushare ingestion。</p>';
        return;
      }
      for (const item of items) {
        const quote = item.latest_quote || {};
        const industry = item.industry || {};
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
          <h2>${item.company.name} <code>${item.security.ts_code}</code></h2>
          <div class="grid">
            <div>Company ID</div><div>${item.company.company_id}</div>
            <div>Security ID</div><div>${item.security.security_id}</div>
            <div>Exchange</div><div>${item.security.exchange}</div>
            <div>Industry</div><div>${industry.name || '-'}</div>
            <div>Latest Close</div><div>${quote.close ?? '-'}</div>
            <div>Trade Date</div><div>${quote.trade_date || '-'}</div>
            <div>Sources</div><div>${(item.source_refs || []).map(s => s.source_name).join(', ')}</div>
          </div>
        `;
        root.appendChild(card);
      }
    }
    loadAll();
  </script>
</body>
</html>
"""

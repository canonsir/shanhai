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


@app.post("/market/ingestion/tushare/run")
def run_tushare_ingestion() -> dict:
    service = AShareCompanySyncService(default_tushare_provider(), market_store)
    report = service.sync_companies(DEFAULT_A_SHARE_TARGETS)
    return report.model_dump(mode="json")


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

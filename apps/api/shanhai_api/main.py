"""FastAPI 应用入口。

Phase 0：提供健康检查与一个 Model Router 演示端点，验证 Harness 装配。
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel
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

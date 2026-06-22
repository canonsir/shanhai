"""Evaluation 数据模型（见 ADR 0010）。

跨三层通用的最小契约：Metric（指标）+ EvaluationResult（一次评估产出）。
本阶段仅服务 Layer 1 Runtime Evaluation，字段设计保持向 Layer 2/3 扩展的余地。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Metric(BaseModel):
    """一项可度量的原子评价结果。"""

    name: str
    value: Any
    # 所属评估层：runtime（Layer 1）/ output（Layer 2）/ investment（Layer 3）
    layer: str = "runtime"
    unit: str | None = None


class EvaluationResult(BaseModel):
    """对某一被评运行的一次评估产出。"""

    run_id: str = ""
    evaluator: str = ""
    metrics: list[Metric] = Field(default_factory=list)
    # 可选总判定；闭环语义下允许「只度量不判定」（None）
    passed: bool | None = None
    detail: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def value(self, name: str) -> Any:
        """按名取指标值；不存在返回 None。"""
        for m in self.metrics:
            if m.name == name:
                return m.value
        return None

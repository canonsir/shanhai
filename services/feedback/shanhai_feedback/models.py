"""Feedback 数据契约（见 ADR 0013，Stage 1：FailurePattern → Candidate → Lesson）。

Feedback 的产物是 ExperienceCandidate——一条**尚未持久化**的候选经验，由确定性规则
从 EvaluationResult（+ 只读 RunRecord 上下文）派生。经去重/合并/阈值晋升后，才以
type=lesson 的 ExperienceEvent 落入 ExperienceStore（事实基座，ADR 0014）。

边界（ADR 0013 §6 / Addendum）：候选只**引用** run_id / evaluator，不内嵌原始 metrics；
原始度量仍归 evaluation 所有，杜绝双写漂移。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CandidateKind(str, Enum):
    """候选经验类型（Stage 1 仅 failure_pattern，可扩展）。"""

    # 失败模式：某 Agent 反复以某类错误失败（ADR 0013 §4 规则 1）
    FAILURE_PATTERN = "failure_pattern"


class ExperienceCandidate(BaseModel):
    """一条尚未持久化的候选经验（ADR 0013 §4）。

    经 CandidateRegistry 去重/合并计数，达到晋升阈值后晋升为 lesson 事件。
    只持有来源引用与精简触发信号，不复制原始度量。
    """

    kind: CandidateKind
    agent: str
    # 提炼后的结论文本（确定性模板生成，人/Agent 可读）
    summary: str
    # 去重键：相同键合并而非重复存（如 agent + failure + error_type）
    dedup_key: str
    # 来源引用（不内嵌原始 metrics）
    source_run_ids: list[str] = Field(default_factory=list)
    source_evaluator: str = ""
    # 触发本候选的关键度量快照（精简，用于解释「为什么生成」）
    signals: dict = Field(default_factory=dict)
    # 合并出现次数；晋升阈值据此判定
    occurrences: int = 1
    # 置信/重要度（Stage 1 = occurrences）
    score: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

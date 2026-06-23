"""候选经验验证接口（见 ADR 0017 修正 4，Stage 2-b）。

Validator 是 Evolution Layer 的**架构接口**，不是智能系统：把 Candidate + 只读经验证据
归约为一个 ValidationVerdict（models.py 跨模块契约），交由 CandidateService.apply_validation
落地。Stage 2-b 只提供 NoopValidator 占位实现。

边界冻结（ADR 0017 修正 4 / Commit 3 Review）：
- 只读：经 ValidationContext 的 ExperienceReader / EvaluationReader 读 Event / Outcome /
  Evaluation；这些 Protocol **只有读方法**，结构上无 append/update（事实层 append-only）。
- 不依赖 feedback（依赖方向 feedback → evolution → experience）。
- 不引入模型推理：无 LLM / summary / embedding / similarity search。
- 不编排：Validator 只产 Verdict，不调用 CandidateService / PromotionGate。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from shanhai_experience_evolution.candidate import ExperienceCandidate
from shanhai_experience_evolution.models import ValidationVerdict


@runtime_checkable
class ExperienceReader(Protocol):
    """只读经验事实视图（结构子集，无写方法）。

    供 Validator 按引用回查事实层（ExperienceEvent / outcome）。只声明读方法，
    使 Validator 无法经此 append/update——事实层 append-only 不变量由类型保证。
    """

    def get(self, event_id: str): ...

    def list(self, **filters): ...


@runtime_checkable
class EvaluationReader(Protocol):
    """只读评估视图（结构子集，无写方法）。

    供 Validator 回查 EvaluationResult 作为验证证据。同样只读。
    """

    def get(self, run_id: str, evaluator: str | None = None): ...


@dataclass(frozen=True)
class ValidationContext:
    """验证只读上下文（ADR 0017 修正 4）。

    把证据准备收口于 Context，避免散落到调用方；只持只读 reader，
    Validator 不拥有 ExperienceStore，也无任何写通道。
    """

    experience_reader: ExperienceReader | None = None
    evaluation_reader: EvaluationReader | None = None


class Validator(ABC):
    """候选经验验证接口：Candidate + 只读证据 → ValidationVerdict。"""

    name: str = "validator"

    @abstractmethod
    def validate(
        self,
        candidate: ExperienceCandidate,
        context: ValidationContext,
    ) -> ValidationVerdict:
        raise NotImplementedError


class NoopValidator(Validator):
    """占位实现（Stage 2-b）：不做任何推理，返回未验证裁决。

    用于打通生命周期接口与依赖装配；真实验证规则（outcome 复核 / 一致性）属后续阶段。
    """

    name = "noop"

    def validate(
        self,
        candidate: ExperienceCandidate,
        context: ValidationContext,
    ) -> ValidationVerdict:
        return ValidationVerdict(
            validated=False,
            confidence=0.0,
            reason="noop validator：未实施验证规则（Stage 2-b 占位）",
        )

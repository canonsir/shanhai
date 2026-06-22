"""Evaluator 抽象与 Layer 1 实现（见 ADR 0010）。

边界（强制）：Evaluation 只消费 Agent Runtime 的只读运行记录（RunResult / RunRecord），
不直连数据库、不调用模型、不修改 Agent Runtime 或 Tool Registry。被评数据由调用方
从 RunStore 取出后传入；Evaluator 自身不持有数据源。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shanhai_agent_runtime.store import RunRecord
from shanhai_agent_runtime.types import RunResult, StepType

from shanhai_evaluation.models import EvaluationResult, Metric


def _as_result(target: RunResult | RunRecord) -> tuple[RunResult, str]:
    """统一入参：接受 RunResult 或 RunStore 读出的 RunRecord。"""
    if isinstance(target, RunRecord):
        return target.result, target.run_id
    return target, ""


class Evaluator(ABC):
    """评估器接口：输入被评运行，输出 EvaluationResult。"""

    name: str = "evaluator"

    @abstractmethod
    def evaluate(self, target: RunResult | RunRecord) -> EvaluationResult:
        raise NotImplementedError


class RuntimeEvaluator(Evaluator):
    """Layer 1：评价 Agent Runtime 的执行过程是否健康。

    指标（确定性、零外部依赖，全部来自结构化运行记录）：
      - success：运行是否成功（RunResult.ok）
      - step_count：步骤总数
      - tool_usage_count：act 步骤中实际发生的工具调用次数
      - error_type：失败时的错误类型（取 "类型: 消息" 的类型段）；成功为 None
    """

    name = "runtime_evaluator"

    def evaluate(self, target: RunResult | RunRecord) -> EvaluationResult:
        result, run_id = _as_result(target)

        success = result.ok
        step_count = len(result.steps)
        tool_usage_count = sum(
            1 for s in result.steps if s.type == StepType.ACT and s.tool is not None
        )
        error_type = self._error_type(result.error) if not success else None

        metrics = [
            Metric(name="success", value=success),
            Metric(name="step_count", value=step_count, unit="step"),
            Metric(name="tool_usage_count", value=tool_usage_count, unit="call"),
            Metric(name="error_type", value=error_type),
        ]

        return EvaluationResult(
            run_id=run_id,
            evaluator=self.name,
            metrics=metrics,
            passed=success,
            detail={"agent": result.agent, "status": result.status.value},
        )

    @staticmethod
    def _error_type(error: str | None) -> str | None:
        """从 "类型: 消息" 形态的 error 中归类出错误类型。"""
        if not error:
            return None
        return error.split(":", 1)[0].strip() or None

"""ShanHai Evaluation — Agent Runtime 反馈闭环（见 ADR 0010）。

Layer 1 Runtime Evaluation：基于结构化运行记录评价执行过程是否健康。
数据只经 RunStore / RunResult 获取，不直连 DB、不调用模型、不侵入 Runtime。
"""

from shanhai_evaluation.evaluator import Evaluator, RuntimeEvaluator
from shanhai_evaluation.models import EvaluationResult, Metric

__all__ = [
    "Metric",
    "EvaluationResult",
    "Evaluator",
    "RuntimeEvaluator",
]

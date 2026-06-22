"""Evaluation Loop Layer 1 测试（见 ADR 0010）。

运行：uv run python -m tests.test_evaluation
覆盖：
  1. 成功 Run：success=True、error_type=None、passed=True
  2. 失败 Run：success=False、error_type 归类、passed=False
  3. 多 Step Run：step_count / tool_usage_count 正确计数（仅 act+tool 计入）
  4. 空 Run：零步骤不报错，计数为 0
  5. 经 RunStore 取数评估：run_id 透传（边界：只读 RunRecord）
"""

from __future__ import annotations

from shanhai_agent_runtime import InMemoryRunStore
from shanhai_agent_runtime.types import AgentStatus, RunResult, Step, StepType
from shanhai_evaluation import EvaluationResult, Metric, RuntimeEvaluator


def _think(i: int) -> Step:
    return Step(index=i, type=StepType.THINK, content="t")


def _act(i: int, tool: str | None = None) -> Step:
    return Step(index=i, type=StepType.ACT, content="a", tool=tool)


def _observe(i: int) -> Step:
    return Step(index=i, type=StepType.OBSERVE, content="continue")


def test_success_run() -> None:
    run = RunResult(agent="a", status=AgentStatus.COMPLETED, steps=[_think(0), _act(1)])
    ev = RuntimeEvaluator().evaluate(run)

    assert isinstance(ev, EvaluationResult)
    assert ev.value("success") is True
    assert ev.value("error_type") is None
    assert ev.passed is True
    assert ev.evaluator == "runtime_evaluator"
    print("[OK] 成功 Run 评估通过")


def test_failed_run() -> None:
    run = RunResult(
        agent="a",
        status=AgentStatus.FAILED,
        steps=[_think(0)],
        error="PermissionError: 未授权工具",
    )
    ev = RuntimeEvaluator().evaluate(run)

    assert ev.value("success") is False
    assert ev.value("error_type") == "PermissionError"
    assert ev.passed is False
    print("[OK] 失败 Run 评估通过")


def test_multistep_run() -> None:
    steps = [
        _think(0),
        _act(1, tool="echo"),
        _observe(2),
        _think(3),
        _act(4, tool="echo"),
        _observe(5),
        _think(6),
        _act(7),  # 直答，无工具，不计入 tool_usage_count
    ]
    run = RunResult(agent="a", status=AgentStatus.COMPLETED, steps=steps)
    ev = RuntimeEvaluator().evaluate(run)

    assert ev.value("step_count") == 8
    assert ev.value("tool_usage_count") == 2, "仅 act 且 tool 非空才计入"
    print("[OK] 多 Step Run 计数通过")


def test_empty_run() -> None:
    run = RunResult(agent="a", status=AgentStatus.COMPLETED, steps=[])
    ev = RuntimeEvaluator().evaluate(run)

    assert ev.value("step_count") == 0
    assert ev.value("tool_usage_count") == 0
    assert ev.value("success") is True
    print("[OK] 空 Run 评估通过")


def test_evaluate_from_run_store() -> None:
    # 边界验证：通过 RunStore 取数（只读 RunRecord），run_id 透传到结果
    store = InMemoryRunStore()
    run_id = store.save_run(RunResult(agent="persisted", status=AgentStatus.COMPLETED, steps=[_act(0, tool="echo")]))
    record = store.get_run(run_id)
    assert record is not None

    ev = RuntimeEvaluator().evaluate(record)
    assert ev.run_id == run_id
    assert ev.value("tool_usage_count") == 1
    assert isinstance(ev.metrics[0], Metric)
    print("[OK] 经 RunStore 取数评估通过")


def main() -> None:
    test_success_run()
    test_failed_run()
    test_multistep_run()
    test_empty_run()
    test_evaluate_from_run_store()
    print("\nEvaluation Loop Layer 1 测试全部通过 ✅")


if __name__ == "__main__":
    main()

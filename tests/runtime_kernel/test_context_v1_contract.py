"""RuntimeContext v1 字段级 Contract Table 测试（PR-2）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_context_v1_contract
覆盖：
  Case 1 七个 context 字段集合冻结（metadata_context → intent_context）
  Case 2 allowed fields 可构造最小 v1 snapshot
  Case 3 experience_context 只承载引用 / 选择理由，不承载 Artifact dump
  Case 4 Schema Evolution Strategy：v1.0 拒绝 unknown field，新增字段需走版本升级
"""

from __future__ import annotations

from pydantic import ValidationError

from shanhai_runtime_kernel import (
    ConstraintContext,
    EnvironmentContext,
    ExperienceContext,
    IdentityContext,
    IntentContext,
    PolicyContext,
    RuntimeContext,
    SelectedExperienceRef,
    TaskContext,
)


def _assert_rejected(fn, message: str) -> None:
    try:
        fn()
        raise AssertionError(message)
    except ValidationError:
        pass


def test_case1_context_field_table_frozen() -> None:
    assert set(RuntimeContext.model_fields.keys()) == {
        "identity_context",
        "task_context",
        "intent_context",
        "experience_context",
        "policy_context",
        "constraint_context",
        "environment_context",
        "schema_version",
    }
    assert set(IdentityContext.model_fields.keys()) == {
        "run_id",
        "trace_id",
        "schema_version",
    }
    assert set(TaskContext.model_fields.keys()) == {"task_type", "goal", "input"}
    assert set(IntentContext.model_fields.keys()) == {
        "objective",
        "user_intent",
        "decision_intent",
    }
    assert set(SelectedExperienceRef.model_fields.keys()) == {
        "artifact_id",
        "relevance",
        "reason",
    }
    assert set(ExperienceContext.model_fields.keys()) == {
        "experience_refs",
        "selection_reason",
        "selection_score",
    }
    assert set(PolicyContext.model_fields.keys()) == {
        "risk_limits",
        "execution_policies",
        "safety_policies",
    }
    assert set(ConstraintContext.model_fields.keys()) == {
        "constraints",
        "time_budget_ms",
        "max_steps",
    }
    assert set(EnvironmentContext.model_fields.keys()) == {
        "domain",
        "environment_labels",
        "market_state",
    }
    print("[OK] Case 1：RuntimeContext v1 七个 context 字段集合冻结")


def test_case2_allowed_fields_construct_snapshot() -> None:
    ctx = RuntimeContext(
        identity_context=IdentityContext(run_id="run_001", trace_id="trace_001"),
        task_context=TaskContext(
            task_type="research",
            goal="分析行业事件影响",
            input={"event": "policy_update"},
        ),
        intent_context=IntentContext(
            objective="形成可解释判断",
            user_intent="理解事件影响",
            decision_intent="辅助研究决策",
        ),
        experience_context=ExperienceContext(
            experience_refs=(
                SelectedExperienceRef(
                    artifact_id="artifact_001",
                    relevance=0.91,
                    reason="同类政策事件验证有效",
                ),
            ),
            selection_reason="语境匹配",
            selection_score=0.91,
        ),
        policy_context=PolicyContext(
            risk_limits=("no_trading_action",),
            execution_policies=("research_only",),
            safety_policies=("cite_sources",),
        ),
        constraint_context=ConstraintContext(
            constraints=("no_private_data",),
            time_budget_ms=30000,
            max_steps=5,
        ),
        environment_context=EnvironmentContext(
            domain="finance",
            environment_labels=("cn_capital_market",),
            market_state="high_volatility",
        ),
    )

    assert ctx.schema_version == "1.0"
    assert ctx.run_id == "run_001"
    assert ctx.identity_context.trace_id == "trace_001"
    assert ctx.experience_context.experience_refs[0].artifact_id == "artifact_001"
    print("[OK] Case 2：allowed fields 可构造 RuntimeContext v1 snapshot")


def test_case3_experience_context_refs_not_artifact_dump() -> None:
    _assert_rejected(
        lambda: ExperienceContext(
            artifact_content="full artifact dump",  # type: ignore[call-arg]
        ),
        "experience_context 不应承载 artifact_content",
    )
    _assert_rejected(
        lambda: ExperienceContext(
            historical_memory=["memory"],  # type: ignore[call-arg]
        ),
        "experience_context 不应承载 historical_memory",
    )
    _assert_rejected(
        lambda: ExperienceContext(
            embedding=[0.1, 0.2],  # type: ignore[call-arg]
        ),
        "experience_context 不应承载 embedding",
    )
    print("[OK] Case 3：experience_context 只承载引用，不承载 Artifact/Memory/Embedding")


def test_case4_schema_evolution_forbid_unknown() -> None:
    _assert_rejected(
        lambda: RuntimeContext(
            identity_context=IdentityContext(run_id="run_001"),
            market_context={},  # type: ignore[call-arg]
        ),
        "新增 market_context 必须走 schema_version 升级，v1.0 不应静默接受",
    )
    _assert_rejected(
        lambda: IdentityContext(
            run_id="run_001",
            execution_id="exec_001",  # type: ignore[call-arg]
        ),
        "修改 identity 语义必须走 major version，v1.0 不应接受 execution_id",
    )
    print("[OK] Case 4：Schema Evolution — v1.0 拒绝 unknown field")


def main() -> None:
    test_case1_context_field_table_frozen()
    test_case2_allowed_fields_construct_snapshot()
    test_case3_experience_context_refs_not_artifact_dump()
    test_case4_schema_evolution_forbid_unknown()
    print("\nRuntimeContext v1 字段级契约测试全部通过 ✅")


if __name__ == "__main__":
    main()

"""RuntimeContext 契约测试（RuntimeContext v1 / PR-2）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_context_contract
覆盖（context immutability / R7 / schema_version）：
  Case 1 deep immutable：RuntimeContext 与子 context 回写均抛 ValidationError
  Case 2 schema_version 默认 "1.0"（落库 / replay 按当时版本解释）
  Case 3 run_id 仅在 identity_context
  Case 4 RuntimeContext v1 字段集合冻结：metadata_context 已替换为 intent_context
  Case 5 extra="forbid"：未知字段 / 执行字段拒绝
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

_EXECUTION_FIELDS = {
    "model",
    "tools",
    "memory",
    "memory_service",
    "router",
    "tool_registry",
    "market_strategy",
}


def _context() -> RuntimeContext:
    return RuntimeContext(
        identity_context=IdentityContext(run_id="run_001"),
        experience_context=ExperienceContext(
            experience_refs=(
                SelectedExperienceRef(
                    artifact_id="artifact_001",
                    relevance=0.8,
                    reason="历史类似任务中验证有效",
                ),
            ),
            selection_reason="匹配任务目标",
            selection_score=0.8,
        ),
    )


def _assert_validation_error(fn, message: str) -> None:
    try:
        fn()
        raise AssertionError(message)
    except ValidationError:
        pass


def test_case1_deep_immutable() -> None:
    ctx = _context()
    _assert_validation_error(
        lambda: setattr(ctx, "schema_version", "9.9"),
        "RuntimeContext 回写不应成功（frozen 容器）",
    )
    _assert_validation_error(
        lambda: setattr(ctx.identity_context, "run_id", "other"),
        "IdentityContext 回写不应成功（frozen）",
    )
    _assert_validation_error(
        lambda: setattr(ctx.experience_context.experience_refs[0], "artifact_id", "other"),
        "SelectedExperienceRef 回写不应成功（frozen）",
    )
    _assert_validation_error(
        lambda: setattr(ctx.experience_context, "experience_refs", ()),
        "ExperienceContext tuple 字段替换不应成功（frozen）",
    )
    assert not hasattr(ctx.experience_context.experience_refs, "append")
    print("[OK] Case 1：RuntimeContext / 子契约 / 经验引用均 deep immutable")


def test_case2_schema_version_default() -> None:
    ctx = _context()
    assert ctx.schema_version == "1.0", ctx.schema_version
    assert ctx.identity_context.schema_version == "1.0"
    try:
        RuntimeContext(
            identity_context=IdentityContext(run_id="run_001"),
            schema_version="1.1",  # type: ignore[arg-type]
        )
        raise AssertionError("RuntimeContext v1 不应接受 schema_version='1.1'")
    except ValidationError:
        pass
    print("[OK] Case 2：schema_version 默认 '1.0'（replay 按当时版本解释）")


def test_case3_run_id_only_in_identity() -> None:
    ctx = _context()
    # 身份单点：便捷属性回读 identity_context.run_id
    assert ctx.run_id == "run_001"
    assert ctx.identity_context.run_id == "run_001"
    # 其余 *_context 子模型不得含 run_id 字段
    others = [
        TaskContext,
        IntentContext,
        ExperienceContext,
        PolicyContext,
        EnvironmentContext,
        ConstraintContext,
    ]
    for model in others:
        assert "run_id" not in model.model_fields, f"{model.__name__} 不应含 run_id 字段"
    print("[OK] Case 3：run_id 仅在 identity_context（其余子契约无 run_id）")


def test_case4_no_execution_fields_r7() -> None:
    fields = set(RuntimeContext.model_fields.keys())
    expected = {
        "identity_context",
        "task_context",
        "intent_context",
        "experience_context",
        "policy_context",
        "constraint_context",
        "environment_context",
        "schema_version",
    }
    # 字段集合冻结：7 *_context + schema_version，不多不少；metadata_context 不进 v1。
    assert fields == expected, fields
    assert "metadata_context" not in fields
    # R7：顶层与各子契约均不得出现执行能力字段
    leaked = fields & _EXECUTION_FIELDS
    assert not leaked, f"RuntimeContext 顶层泄漏执行字段: {leaked}"
    submodels = [
        IdentityContext,
        TaskContext,
        IntentContext,
        ExperienceContext,
        PolicyContext,
        EnvironmentContext,
        ConstraintContext,
    ]
    for model in submodels:
        sub_leaked = set(model.model_fields.keys()) & _EXECUTION_FIELDS
        assert not sub_leaked, f"{model.__name__} 泄漏执行字段: {sub_leaked}"
    print("[OK] Case 4：R7 — 字段集合冻结、metadata_context→intent_context、不含执行字段")


def test_case5_extra_forbid_unknown_and_execution_fields() -> None:
    cases = [
        lambda: RuntimeContext(identity_context=IdentityContext(run_id="r"), model="gpt-x"),  # type: ignore[call-arg]
        lambda: RuntimeContext(identity_context=IdentityContext(run_id="r"), tools=[]),  # type: ignore[call-arg]
        lambda: RuntimeContext(identity_context=IdentityContext(run_id="r"), memory_service=object()),  # type: ignore[call-arg]
        lambda: IdentityContext(run_id="r", user_id="u1"),  # type: ignore[call-arg]
        lambda: TaskContext(goal="g", model="gpt-x"),  # type: ignore[call-arg]
        lambda: IntentContext(objective="o", reasoning="hidden"),  # type: ignore[call-arg]
        lambda: ExperienceContext(artifact_content="dump"),  # type: ignore[call-arg]
        lambda: PolicyContext(system_prompt="prompt"),  # type: ignore[call-arg]
        lambda: ConstraintContext(database_session=object()),  # type: ignore[call-arg]
        lambda: EnvironmentContext(stock_price=12.3),  # type: ignore[call-arg]
    ]
    for case in cases:
        try:
            case()
            raise AssertionError("extra='forbid' 应拒绝未知/执行/存储字段")
        except ValidationError:
            pass
    print("[OK] Case 5：extra='forbid' 拒绝 unknown / execution / storage fields")


def main() -> None:
    test_case1_deep_immutable()
    test_case2_schema_version_default()
    test_case3_run_id_only_in_identity()
    test_case4_no_execution_fields_r7()
    test_case5_extra_forbid_unknown_and_execution_fields()
    print("\nRuntimeContext 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()

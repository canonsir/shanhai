"""RuntimeContext 契约测试（v0.7 §0.C G5 / Q5.4，PR-1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_context_contract
覆盖（context immutability / event schema 中的 context 面 / R7）：
  Case 1 容器 immutable：回写字段抛 ValidationError（frozen 容器）
  Case 2 schema_version 默认 "1.0"（落库 / replay 按当时版本解释）
  Case 3 run_id 仅在 identity_context（其余 *_context 无 run_id 字段；便捷属性回读身份）
  Case 4 R7 Context Ownership Drift：RuntimeContext 字段集合冻结为 7 *_context +
         schema_version，**不含** model/tools/memory_service/market_strategy 等执行能力字段
"""

from __future__ import annotations

from pydantic import ValidationError

from shanhai_runtime_kernel import (
    ConstraintContext,
    EnvironmentContext,
    ExperienceContext,
    IdentityContext,
    MetadataContext,
    PolicyContext,
    RuntimeContext,
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
    return RuntimeContext(identity_context=IdentityContext(run_id="run_001"))


def test_case1_container_immutable() -> None:
    ctx = _context()
    try:
        ctx.schema_version = "9.9"  # type: ignore[misc]
        raise AssertionError("RuntimeContext 回写不应成功（frozen 容器）")
    except ValidationError:
        pass
    # 子契约同样 frozen
    try:
        ctx.identity_context.run_id = "other"  # type: ignore[misc]
        raise AssertionError("IdentityContext 回写不应成功（frozen）")
    except ValidationError:
        pass
    print("[OK] Case 1：RuntimeContext / 子契约回写抛 ValidationError（容器 immutable）")


def test_case2_schema_version_default() -> None:
    ctx = _context()
    assert ctx.schema_version == "1.0", ctx.schema_version
    print("[OK] Case 2：schema_version 默认 '1.0'（replay 按当时版本解释）")


def test_case3_run_id_only_in_identity() -> None:
    ctx = _context()
    # 身份单点：便捷属性回读 identity_context.run_id
    assert ctx.run_id == "run_001"
    assert ctx.identity_context.run_id == "run_001"
    # 其余 *_context 子模型不得含 run_id 字段
    others = [
        TaskContext,
        ExperienceContext,
        PolicyContext,
        EnvironmentContext,
        ConstraintContext,
        MetadataContext,
    ]
    for model in others:
        assert "run_id" not in model.model_fields, f"{model.__name__} 不应含 run_id 字段"
    print("[OK] Case 3：run_id 仅在 identity_context（其余子契约无 run_id）")


def test_case4_no_execution_fields_r7() -> None:
    fields = set(RuntimeContext.model_fields.keys())
    expected = {
        "identity_context",
        "task_context",
        "experience_context",
        "policy_context",
        "environment_context",
        "constraint_context",
        "metadata_context",
        "schema_version",
    }
    # 字段集合冻结：7 *_context + schema_version，不多不少
    assert fields == expected, fields
    # R7：顶层与各子契约均不得出现执行能力字段
    leaked = fields & _EXECUTION_FIELDS
    assert not leaked, f"RuntimeContext 顶层泄漏执行字段: {leaked}"
    submodels = [
        IdentityContext,
        TaskContext,
        ExperienceContext,
        PolicyContext,
        EnvironmentContext,
        ConstraintContext,
        MetadataContext,
    ]
    for model in submodels:
        sub_leaked = set(model.model_fields.keys()) & _EXECUTION_FIELDS
        assert not sub_leaked, f"{model.__name__} 泄漏执行字段: {sub_leaked}"
    print("[OK] Case 4：R7 — 字段集合冻结、不含 model/tools/memory_service/market_strategy")


def main() -> None:
    test_case1_container_immutable()
    test_case2_schema_version_default()
    test_case3_run_id_only_in_identity()
    test_case4_no_execution_fields_r7()
    print("\nRuntimeContext 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()

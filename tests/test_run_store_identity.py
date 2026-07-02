"""RunStore identity migration 契约测试（PR-3）。

运行：PYTHONPATH=. .venv/bin/python -m tests.test_run_store_identity
覆盖：
  Case 1 external run_id 正常保存并原样返回
  Case 2 run_id=None 兼容路径发出 DeprecationWarning
  Case 3 RunStore 不暴露 generate_run_id public API
  Case 4 list/get 行为在 external identity 路径下保持稳定
"""

from __future__ import annotations

import warnings

from shanhai_agent_runtime import InMemoryRunStore, RunResult, RunStore
from shanhai_agent_runtime.types import AgentStatus


def _result(agent: str = "identity") -> RunResult:
    return RunResult(agent=agent, status=AgentStatus.COMPLETED, output="ok", steps=[])


def test_case1_external_run_id_persisted() -> None:
    store = InMemoryRunStore()

    returned = store.save_run(_result(), run_id="run_external_001")
    record = store.get_run("run_external_001")

    assert returned == "run_external_001"
    assert record is not None
    assert record.run_id == "run_external_001"
    assert record.result.agent == "identity"
    print("[OK] Case 1：external run_id 原样持久化并返回")


def test_case2_none_run_id_is_deprecated_migration_fallback() -> None:
    store = InMemoryRunStore()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        generated = store.save_run(_result("legacy"))

    assert generated
    assert store.get_run(generated) is not None
    assert any(item.category is DeprecationWarning for item in caught)
    assert "pass external run_id" in str(caught[0].message)
    print("[OK] Case 2：run_id=None 仍兼容，但发出 DeprecationWarning")


def test_case3_run_store_has_no_public_identity_generator() -> None:
    assert not hasattr(RunStore, "generate_run_id")
    assert not hasattr(InMemoryRunStore, "generate_run_id")

    public = {name for name in dir(InMemoryRunStore()) if not name.startswith("_")}
    assert "generate_run_id" not in public
    print("[OK] Case 3：RunStore 不暴露 generate_run_id public API")


def test_case4_list_get_keep_external_identity() -> None:
    store = InMemoryRunStore()
    store.save_run(_result("alpha"), run_id="run_alpha_001")
    store.save_run(_result("beta"), run_id="run_beta_001")
    store.save_run(_result("alpha"), run_id="run_alpha_002")

    assert store.get_run("run_alpha_001").run_id == "run_alpha_001"  # type: ignore[union-attr]
    alpha_runs = store.list_runs(agent="alpha")
    assert {record.run_id for record in alpha_runs} == {"run_alpha_001", "run_alpha_002"}
    assert all(record.result.agent == "alpha" for record in alpha_runs)
    print("[OK] Case 4：external identity 路径下 list/get 行为稳定")


def main() -> None:
    test_case1_external_run_id_persisted()
    test_case2_none_run_id_is_deprecated_migration_fallback()
    test_case3_run_store_has_no_public_identity_generator()
    test_case4_list_get_keep_external_identity()
    print("\nRunStore identity migration 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()

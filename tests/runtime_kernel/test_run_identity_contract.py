"""Runtime trace identity 一致性契约测试（PR-3）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_run_identity_contract
覆盖：
  Case 1 RuntimeContext.run_id = RuntimeEvent.run_id = RunRecord.run_id
  Case 2 identity fixture 不依赖 RunStore 生成能力
"""

from __future__ import annotations

from shanhai_agent_runtime import InMemoryRunStore, RunResult
from shanhai_agent_runtime.types import AgentStatus
from shanhai_runtime_kernel import (
    IdentityContext,
    RuntimeContext,
    RuntimeEvent,
    RuntimeEventType,
)


def _result() -> RunResult:
    return RunResult(agent="identity", status=AgentStatus.COMPLETED, output="ok", steps=[])


def test_case1_trace_identity_consistency() -> None:
    run_id = "run_trace_001"
    context = RuntimeContext(identity_context=IdentityContext(run_id=run_id))
    event = RuntimeEvent(
        run_id=context.run_id,
        event_type=RuntimeEventType.RUN_COMPLETED,
        payload=_result(),
    )
    store = InMemoryRunStore()

    stored_run_id = store.save_run(event.payload, run_id=event.run_id)
    record = store.get_run(stored_run_id)

    assert context.run_id == event.run_id == stored_run_id
    assert record is not None
    assert context.identity_context.run_id == record.run_id
    print("[OK] Case 1：RuntimeContext.run_id = RuntimeEvent.run_id = RunRecord.run_id")


def test_case2_runtime_identity_fixture_not_owned_by_store() -> None:
    store = InMemoryRunStore()
    run_id = "run_runtime_owned_001"

    assert not hasattr(store, "generate_run_id")
    returned = store.save_run(_result(), run_id=run_id)

    assert returned == run_id
    assert store.get_run(run_id) is not None
    print("[OK] Case 2：identity fixture 由 Runtime 侧提供，RunStore 仅持久化")


def main() -> None:
    test_case1_trace_identity_consistency()
    test_case2_runtime_identity_fixture_not_owned_by_store()
    print("\nRuntime trace identity 一致性契约测试全部通过 ✅")


if __name__ == "__main__":
    main()

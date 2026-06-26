"""运行记录持久化测试（Phase 1，见 ADR 0008）。

运行：uv run python -m tests.test_run_store
覆盖：
  1. InMemoryRunStore 契约：save / get / list（含 agent 过滤与时间倒序）
  2. AgentRunner 注入 store：运行结束后落库，记录可回读
  3. best-effort：落库失败不影响 RunResult.ok
"""

from __future__ import annotations

from pathlib import Path

from shanhai_agent_runtime import (
    AgentRunner,
    BaseAgent,
    InMemoryRunStore,
    RunResult,
    RunStore,
)
from shanhai_agent_runtime.types import AgentStatus
from shanhai_model_router import ModelRegistry, ModelRouter

MODELS_YAML = Path(__file__).resolve().parents[1] / "services" / "model-router" / "models.yaml"


def _router() -> ModelRouter:
    return ModelRouter(ModelRegistry.from_yaml(MODELS_YAML))


def _result(agent: str, status: AgentStatus = AgentStatus.COMPLETED) -> RunResult:
    return RunResult(agent=agent, status=status, output="x", steps=[])


def test_inmemory_store_contract() -> None:
    store = InMemoryRunStore()
    rid_a = store.save_run(_result("alpha"))
    store.save_run(_result("beta"))
    rid_a2 = store.save_run(_result("alpha"))

    rec = store.get_run(rid_a)
    assert rec is not None and rec.run_id == rid_a and rec.result.agent == "alpha"
    assert store.get_run("nope") is None

    all_runs = store.list_runs()
    assert len(all_runs) == 3
    # 时间倒序：最后写入的 alpha 在最前
    assert all_runs[0].run_id == rid_a2

    only_alpha = store.list_runs(agent="alpha")
    assert {r.result.agent for r in only_alpha} == {"alpha"} and len(only_alpha) == 2

    assert len(store.list_runs(limit=1)) == 1
    print("[OK] InMemoryRunStore save/get/list 契约通过")


def test_runner_persists_on_run() -> None:
    store = InMemoryRunStore()
    agent = BaseAgent(name="persisted", router=_router(), store=store)
    result = agent.run("分析山海")
    assert result.ok

    runs = store.list_runs(agent="persisted")
    assert len(runs) == 1, "运行结束应落库一条记录"
    saved = runs[0].result
    assert saved.agent == "persisted" and saved.status == AgentStatus.COMPLETED
    assert len(saved.steps) == len(result.steps), "落库应包含完整 step 序列"
    print("[OK] AgentRunner 注入 store 后运行记录落库通过")


def test_no_store_no_persistence() -> None:
    # 不注入 store：行为与现状一致，run() 正常返回
    agent = BaseAgent(name="plain", router=_router())
    result = agent.run("hi")
    assert result.ok and agent.store is None
    print("[OK] 未注入 store 时零行为变化通过")


class _BoomStore(RunStore):
    def save_run(self, run: RunResult, run_id: str | None = None) -> str:
        raise RuntimeError("db down")

    def get_run(self, run_id: str):
        return None

    def list_runs(self, agent=None, limit=50):
        return []


def test_persist_failure_is_best_effort() -> None:
    agent = BaseAgent(name="resilient", router=_router(), store=_BoomStore())
    result = agent.run("hi")
    assert result.ok, "落库失败不应影响运行结果（best-effort）"
    print("[OK] 落库失败 best-effort 不污染 RunResult 通过")


def main() -> None:
    test_inmemory_store_contract()
    test_runner_persists_on_run()
    test_no_store_no_persistence()
    test_persist_failure_is_best_effort()
    print("\n运行记录持久化测试全部通过 ✅")


if __name__ == "__main__":
    main()

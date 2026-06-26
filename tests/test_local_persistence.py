"""Local-first 持久化测试（Phase 1，见 ADR 0009）。

运行：.venv/bin/python tests/test_local_persistence.py
覆盖：
  1. SqliteRunStore 契约：save / get / list（含 agent 过滤、时间倒序、limit）+ 落盘文件
  2. 跨连接持久化：新建 store 指向同一文件仍能回读（验证真正落盘，非进程内）
  3. AgentRunner 注入 SqliteRunStore：运行结束落库，step 序列完整
  4. default_run_store 工厂：默认 sqlite / memory / postgres 缺 DSN 报错 / 未知后端报错
"""

from __future__ import annotations

import os
import tempfile
import warnings
from pathlib import Path

from shanhai_agent_runtime import (
    BaseAgent,
    InMemoryRunStore,
    RunResult,
)
from shanhai_agent_runtime.types import AgentStatus, Step, StepType
from shanhai_model_router import ModelRegistry, ModelRouter
from shanhai_persistence import SqliteRunStore, default_run_store

MODELS_YAML = Path(__file__).resolve().parents[1] / "services" / "model-router" / "models.yaml"


def _router() -> ModelRouter:
    return ModelRouter(ModelRegistry.from_yaml(MODELS_YAML))


def _result(agent: str, status: AgentStatus = AgentStatus.COMPLETED) -> RunResult:
    step = Step(index=0, type=StepType.ACT, content="c", tool="echo", tool_args={"x": 1}, tool_result={"ok": True})
    return RunResult(agent=agent, status=status, output={"out": agent}, steps=[step])


def test_sqlite_store_contract() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "nested", "runs.db")
        store = SqliteRunStore(db)
        assert Path(db).exists(), "构造即应建库文件落盘"

        rid_a = store.save_run(_result("alpha"))
        store.save_run(_result("beta"))
        rid_a2 = store.save_run(_result("alpha"))

        rec = store.get_run(rid_a)
        assert rec is not None and rec.run_id == rid_a and rec.result.agent == "alpha"
        assert rec.result.output == {"out": "alpha"}, "JSON 反序列化应还原 output"
        assert len(rec.result.steps) == 1 and rec.result.steps[0].tool == "echo"
        assert store.get_run("nope") is None

        all_runs = store.list_runs()
        assert len(all_runs) == 3
        assert all_runs[0].run_id == rid_a2, "时间倒序：最后写入在最前"

        only_alpha = store.list_runs(agent="alpha")
        assert {r.result.agent for r in only_alpha} == {"alpha"} and len(only_alpha) == 2
        assert len(store.list_runs(limit=1)) == 1
    print("[OK] SqliteRunStore save/get/list 契约 + 落盘通过")


def test_sqlite_store_external_run_id() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "runs.db")
        store = SqliteRunStore(db)

        returned = store.save_run(_result("external"), run_id="run_sqlite_external_001")
        rec = store.get_run("run_sqlite_external_001")

        assert returned == "run_sqlite_external_001"
        assert rec is not None and rec.run_id == "run_sqlite_external_001"
        assert rec.result.agent == "external"
    print("[OK] SqliteRunStore external run_id 持久化通过")


def test_sqlite_store_none_run_id_warns() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = SqliteRunStore(os.path.join(d, "runs.db"))

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            run_id = store.save_run(_result("legacy"))

        assert store.get_run(run_id) is not None
        assert any(item.category is DeprecationWarning for item in caught)
    print("[OK] SqliteRunStore run_id=None migration fallback 发出 warning")


def test_sqlite_persists_across_connections() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "runs.db")
        rid = SqliteRunStore(db).save_run(_result("gamma"))
        # 全新 store 实例指向同一文件：数据应仍在（真正落盘，非进程内 InMemory）
        reopened = SqliteRunStore(db)
        rec = reopened.get_run(rid)
        assert rec is not None and rec.result.agent == "gamma"
    print("[OK] SqliteRunStore 跨连接持久化通过")


def test_runner_persists_to_sqlite() -> None:
    with tempfile.TemporaryDirectory() as d:
        store = SqliteRunStore(os.path.join(d, "runs.db"))
        agent = BaseAgent(name="persisted", router=_router(), store=store)
        result = agent.run("分析山海")
        assert result.ok

        runs = store.list_runs(agent="persisted")
        assert len(runs) == 1
        saved = runs[0].result
        assert saved.agent == "persisted" and saved.status == AgentStatus.COMPLETED
        assert len(saved.steps) == len(result.steps), "落库应含完整 step 序列"
    print("[OK] AgentRunner 落库到 SQLite 通过")


def test_factory_backends() -> None:
    keys = ["SHANHAI_RUN_STORE", "SHANHAI_SQLITE_PATH", "SHANHAI_PG_DSN"]
    saved = {k: os.environ.get(k) for k in keys}
    try:
        with tempfile.TemporaryDirectory() as d:
            # 默认 sqlite
            for k in keys:
                os.environ.pop(k, None)
            os.environ["SHANHAI_SQLITE_PATH"] = os.path.join(d, "runs.db")
            assert isinstance(default_run_store(), SqliteRunStore), "默认应为 sqlite"

            # memory
            os.environ["SHANHAI_RUN_STORE"] = "memory"
            assert isinstance(default_run_store(), InMemoryRunStore)

            # postgres 缺 DSN 报错
            os.environ["SHANHAI_RUN_STORE"] = "postgres"
            os.environ.pop("SHANHAI_PG_DSN", None)
            _expect_value_error(default_run_store, "postgres 缺 DSN 应报错")

            # 未知后端报错
            os.environ["SHANHAI_RUN_STORE"] = "weird"
            _expect_value_error(default_run_store, "未知后端应报错")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    print("[OK] default_run_store 工厂按环境变量选后端通过")


def _expect_value_error(fn, msg: str) -> None:
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(msg)


def main() -> None:
    test_sqlite_store_contract()
    test_sqlite_store_external_run_id()
    test_sqlite_store_none_run_id_warns()
    test_sqlite_persists_across_connections()
    test_runner_persists_to_sqlite()
    test_factory_backends()
    print("\nLocal-first 持久化测试全部通过 ✅")


if __name__ == "__main__":
    main()

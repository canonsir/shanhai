# RunStore Identity Migration Closure Review（PR-3 Post Implementation）

> 状态：**✅ Closure Review Completed — PR-3 Approved**。
> 对象：`7483309 feat(runtime): migrate RunStore identity ownership`。
> 范围：post implementation review only；不修改代码，不进入 PR-4 实现。

---

## 1. Implementation Summary

PR-3 完成了 RunStore identity ownership migration 的最小实现。

已实现：

- `RunStore.save_run(run, run_id: str | None = None) -> str`
- external `run_id` 为 Runtime-owned identity 主路径。
- `run_id=None` 保留为 migration window fallback，并发出 `DeprecationWarning`。
- `InMemoryRunStore` / `SqliteRunStore` / `PostgresRunStore` 同步签名，避免抽象与实现不一致。
- 新增 identity contract tests：
  - `tests/test_run_store_identity.py`
  - `tests/runtime_kernel/test_run_identity_contract.py`
- 强化 SQLite persistence tests：
  - `tests/test_local_persistence.py`

未实现 / 未进入：

- RuntimeKernel identity generator
- RuntimeKernel execution path
- AgentRunner adapter
- Experience Runtime
- Memory / Artifact / Evaluation / E2E
- migration fallback removal

---

## 2. Contract Compliance Matrix

| Constraint | Review Result | Evidence |
|---|---|---|
| RunIdentity ownership 从 RunStore 移出 | ✅ Pass | `save_run(..., run_id=external)` 成为主路径；RunStore 只接收并持久化 run_id。 |
| RunStore 仅承担 execution trace persistence | ✅ Pass | RunStore 仍只提供 `save_run/get_run/list_runs`；未新增 lifecycle / orchestration / decision API。 |
| `save_run(run, run_id=None)` 符合 migration window | ✅ Pass | `run_id=None` 分支仍可用，但发出 `DeprecationWarning`；关闭 fallback 留后续 Gate。 |
| 不存在 public `generate_run_id` | ✅ Pass | 测试断言 `RunStore` / `InMemoryRunStore` 不暴露 `generate_run_id`；实现未新增该 API。 |
| trace identity consistency | ✅ Pass | 测试验证 `RuntimeContext.run_id = RuntimeEvent.run_id = RunRecord.run_id`。 |
| 不耦合 orchestration migration | ✅ Pass | 未修改 `kernel.py` / AgentRunner / E2E。 |

---

## 3. Migration Window Status

当前处于 migration window Phase 1：

```text
Phase 1（当前）
    save_run(run, run_id=None)
    allowed
    emits DeprecationWarning

Phase 2（未来）
    run_id required in new Runtime path
    old path deprecated under explicit compatibility tests only

Phase 3（未来 Closure Gate）
    remove fallback
    save_run(run, run_id: str) only
```

当前实现符合 Phase 1：

- external run_id 可原样持久化。
- `run_id=None` 不静默；会发出 warning。
- fallback 仍内部 mint id，仅用于 legacy compatibility。
- fallback 未移除；移除必须另开 Migration Closure Gate。

风险记录：

- 现有旧路径测试会打印 `DeprecationWarning`，这是预期信号。
- 后续 PR-5 接入 Runtime identity 后，应逐步减少旧路径调用。
- 不应在 PR-4 Experience Runtime 中关闭 fallback。

---

## 4. Test Evidence

Closure Review 复跑命令：

```bash
PYTHONPATH=. .venv/bin/python -m tests.test_run_store_identity
PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_run_identity_contract
PYTHONPATH=. .venv/bin/python -m tests.test_run_store
PYTHONPATH=. .venv/bin/python -m tests.test_local_persistence
PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_dependency_boundary
```

结果：

| Test | Result | Coverage |
|---|---|---|
| `tests.test_run_store_identity` | ✅ Pass | external run_id / fallback warning / no `generate_run_id` / list-get stable |
| `tests.runtime_kernel.test_run_identity_contract` | ✅ Pass | `RuntimeContext.run_id = RuntimeEvent.run_id = RunRecord.run_id` |
| `tests.test_run_store` | ✅ Pass | legacy InMemory behavior + AgentRunner best-effort persistence compatibility |
| `tests.test_local_persistence` | ✅ Pass | SQLite external identity + fallback warning + persistence compatibility |
| `tests.runtime_kernel.test_dependency_boundary` | ✅ Pass | runtime-kernel dependency boundary remains clean |

此前 PR-3 implementation 阶段已跑全量回归，结果为 all-pass；本 closure review 复跑重点契约与边界测试，未发现新增缺陷。

---

## 5. Forbidden Boundary Verification

PR-3 commit touched files:

```text
CHANGELOG.md
docs/PROJECT_STATE.md
docs/design/runstore-identity-migration-review-v0.1.md
services/agent-runtime/shanhai_agent_runtime/store.py
services/persistence/shanhai_persistence/postgres_run_store.py
services/persistence/shanhai_persistence/sqlite_run_store.py
tests/runtime_kernel/test_run_identity_contract.py
tests/test_local_persistence.py
tests/test_run_store.py
tests/test_run_store_identity.py
```

Forbidden files / areas not modified:

| Boundary | Status |
|---|---|
| RuntimeKernel execution path | ✅ Not touched |
| `services/runtime-kernel/shanhai_runtime_kernel/kernel.py` | ✅ Not touched |
| `events.py` | ✅ Not touched |
| `lifecycle.py` | ✅ Not touched |
| RuntimeContext contract | ✅ Not touched |
| AgentRunner | ✅ Not touched |
| Experience Runtime | ✅ Not introduced / not touched |
| Memory | ✅ Not touched |
| Artifact Layer | ✅ Not touched |
| Evaluation | ✅ Not touched |
| E2E execution flow | ✅ Not touched |

No boundary violation found.

---

## 6. Final Decision

PR-3 RunStore Identity Migration is approved.

Final status:

```text
PR-3 RunStore Identity Migration
    ✅ Implementation Completed
    ✅ Closure Review Completed

Next:
PR-4 Experience Runtime Review Gate
    ⏸️ Review only; no implementation yet
```

Decision:

- PR-3 satisfies frozen Design Constraints.
- Identity ownership has migrated from storage-owned to Runtime-owned contract surface.
- RunStore remains execution trace persistence.
- Migration window is explicit and observable via `DeprecationWarning`.
- No forbidden boundary was touched.

Stop here. Do not enter PR-4 implementation without a separate Review Gate approval.

# RuntimeContext Contract Implementation Review（PR-2 Gate）

> 状态：**Review Gate — 待确认后再写 PR-2 实现**。
> 前置：Runtime Kernel v0.7 Phase 1 / PR-1 已 Approved（Runtime Kernel Skeleton + Contract Test Layer）。
> 本轮目标：在进入 RuntimeContext v1 implementation 之前，确认 PR-1 skeleton 中的 contract 是否需要调整。

---

## 0. PR-1 Post Review 结论

Phase 1 / PR-1：`Runtime Kernel Skeleton + Contract Layer` 已完成并通过 Review。

已确认：

- commit 顺序符合冻结策略：
  - `f388494 chore(runtime-kernel): create package skeleton`
  - `b084a90 feat(runtime-kernel): add lifecycle state machine`
  - `96f179b feat(runtime-kernel): add RuntimeContext contract`
  - `dedc589 feat(runtime-kernel): add RuntimeEvent contract`
  - `40ecd05 test(runtime-kernel): add contract tests`
- 未进入后续 PR：
  - no RuntimeContext implementation
  - no RunStore identity migration
  - no Experience Runtime
  - no E2E integration
- boundary 未污染：
  - runtime-kernel 只拥有 `RuntimeKernel` / `RuntimeContext` / `RuntimeEvent` / `RuntimeState`
  - 未引入 Agent / Tool / Model / Memory / Artifact
- contract tests 已锁定：
  - context immutability / R7 字段边界
  - lifecycle transition
  - event schema
  - dependency boundary

结论：**PR-1 Approved**。

---

## 1. 后续 PR 顺序（Post Review 调整）

为避免过早进入 RunStore migration，后续顺序调整为：

```
PR-2  RuntimeContext v1 implementation review + implementation
PR-3  RunStore identity migration
PR-4  Experience Runtime
PR-5  E2E integration
```

治理原则保持：

- additive first
- behavior change last
- 不改 AgentRunner 行为
- 不改 RunStore identity（直到 PR-3）
- 不实现 Selector / Projection（直到 PR-4）
- 不恢复 Commit 7 ArtifactReader
- 不接 Memory

---

## 2. PR-2 Review 要确认的问题

PR-2 不应直接写实现。先确认以下 contract 问题。

### Q1. RuntimeKernel API 是否符合 v0.5 freeze？

当前 skeleton：

```python
RuntimeKernel.create(run_id: str) -> RuntimeHandle
RuntimeKernel.assemble(handle: RuntimeHandle) -> RuntimeContext
RuntimeKernel.execute(handle: RuntimeHandle, context: RuntimeContext) -> RuntimeHandle
RuntimeKernel.close(handle: RuntimeHandle) -> RuntimeHandle
```

待确认：

- `create()` 是否应由 Kernel mint `run_id`，还是继续由调用方传入？
- `assemble()` 是否只返回 `RuntimeContext`，还是同时返回 `RuntimeHandle(state=READY)`？
- `execute()` 在 PR-2 是否仍必须占位，不触碰 AgentRuntime？
- `close()` 是否只处理 lifecycle，不产生存储行为？

默认建议：**PR-2 仍不实现 execute / close 行为**；只冻结 RuntimeContext v1 构造与 schema。

### Q2. RuntimeContext schema 是否需要调整？

当前 skeleton：

```python
RuntimeContext(
    identity_context,
    task_context,
    experience_context,
    policy_context,
    environment_context,
    constraint_context,
    metadata_context,
    schema_version="1.0",
)
```

待确认：

- 7 个 `*_context` 是否保持完整且不增删？
- `task_context` 当前 `objective/task_type` 是否足够作为 v1 最小字段？
- `experience_context.selection_ref` 是否过早暗示 Selector，是否应改为更中性的 `experience_refs` / `projection_ref` / 留空结构？
- `metadata_context.metadata: dict[str, Any]` 是否会成为 R7 漏洞入口？
- 是否需要 `extra="forbid"` 防止 `RuntimeContext(model=..., tools=...)` 被 Pydantic 接受？

默认建议：**PR-2 应加 `extra="forbid"` 到 RuntimeContext 及所有子 context**，强化 R7。

### Q3. RuntimeEvent envelope 是否完整？

当前 skeleton：

```python
RuntimeEvent(
    event_id,
    run_id,
    event_type,
    timestamp,
    payload,
)
```

待确认：

- 是否需要 `schema_version`？
- `event_type` 是否只保留生命周期事件，避免引入 Experience 语义？
- `payload: Any` 是否继续保留，还是收窄为 `dict[str, Any]`？
- 是否需要 `source` / `producer`？若加入，是否会把 agent/evaluation 语义提前塞进 RuntimeEvent？

默认建议：**RuntimeEvent 不在 PR-2 扩展**。PR-2 聚焦 RuntimeContext v1。

### Q4. 生命周期状态是否需要补 terminal state？

当前合法链：

```text
CREATED → ASSEMBLING → READY → RUNNING → COMPLETED → CLOSED
```

待确认：

- 是否需要 `FAILED`？
- 是否需要 `CANCELLED`？
- 如果加入失败态，是 PR-2 前置，还是留到 AgentRuntime adapter / E2E 后再加？

默认建议：**PR-2 不加 terminal 扩展态**。失败/取消语义需要和 AgentRuntime `AgentStatus.FAILED` 对齐，留 PR-4/PR-5 前再开 Gate。

### Q5. package naming 是否最终确定？

当前：

- package path：`services/runtime-kernel`
- import name：`shanhai_runtime_kernel`
- distribution name：`shanhai-runtime-kernel`

待确认：

- 是否保持 `runtime-kernel` 而非 `runtime-core` / `runtime-orchestrator`？
- 是否需要 package README / owner doc？

默认建议：**命名保持不变**。它准确表达 ownership boundary：Runtime Kernel = orchestrator boundary，非 executor。

---

## 3. PR-2 Definition of Done（待 Review 批准）

PR-2 只允许：

- 冻结 RuntimeContext v1 schema。
- 加强 RuntimeContext / 子 context 的 Pydantic 配置（如 `extra="forbid"`）。
- 调整 RuntimeContext 字段命名（若 Review 批准）。
- 增补 contract tests。
- 更新 docs / PROJECT_STATE / CHANGELOG。

PR-2 禁止：

- 不改 AgentRunner 行为。
- 不改 RunStore identity。
- 不实现 Selector / Projection。
- 不接 Experience Runtime。
- 不接 Memory。
- 不实现 Domain Provider。
- 不恢复 ArtifactReader。
- 不做 E2E integration。

---

## 4. 当前建议

建议 PR-2 Review 先聚焦一个判断：

> RuntimeContext v1 是否应从 PR-1 skeleton 的「字段存在」提升为「字段集合 + extra forbid + R7 防漂移」的稳定 contract？

若批准，PR-2 的最小实现面应是：

1. `ConfigDict(frozen=True, extra="forbid")`
2. RuntimeContext 与 7 个子 context 全部 forbid unknown fields
3. contract tests 增加未知字段拒绝用例（`model/tools/memory_service/market_strategy`）
4. 不触碰 `RuntimeKernel.execute()` / AgentRunner / RunStore

> 当前停在 **RuntimeContext Contract Implementation Review Gate**。未开始 PR-2 代码实现。

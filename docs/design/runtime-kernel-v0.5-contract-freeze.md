# Runtime Kernel v0.5 — Contract Freeze Review（契约冻结稿，仅讨论，不编码）

> 状态：**✅ Contract Frozen（v0.5 契约已冻结）→ 进入** **[v0.6 Implementation Boundary](runtime-kernel-v0.6-implementation-boundary.md)** — Review 原则批准并补充 6 项约束（含新增 §Q6 Context Foundation Boundary），已折入本文 §0.A。仍 **Design Only**：不建包、不改 RunStore/AgentRunner、不实现 RuntimeContext/Selector、不解冻 Commit 7。
> 状态（历史）：⏳ Contract Freeze Review — 冻结五项契约（Q1 public contract / Q2 RuntimeContext v1 schema / Q3 RuntimeEvent schema / Q4 ExperienceSelector interface / Q5 Package dependency graph）。
> 阶段：Phase 1 — Agent Runtime / Runtime Kernel Contract Freeze。
> 前置：[Runtime Kernel Architecture v0.4](runtime-kernel-architecture-v0.4.md) ✅ Direction Approved（含 8 约束）；[Runtime Context API v0.3](runtime-context-api-v0.3.md) ✅ Direction Approved（含 7 约束）；[Runtime Kernel Design v0.2](runtime-kernel-v0.2.md) ✅ Direction Approved；[v0.1](runtime-kernel-v0.1.md) Principle Approved。
> 关联：\[ADR 0006 执行模型]、\[ADR 0008/0009 RunStore]、[ADR 0018 Artifact](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0004](../../.shanhai-meta/decisions/records/DEC-0004-future-market-cognition.md)、[DEC-0005](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

***

## 0.A Review 补充约束（v0.5 冻结附带，已折入下文）

Review 原则批准五项契约，冻结前补充 6 项约束（含 1 条新增 §Q6）：

| # | 约束                                                                                                                                                                                                                                                                                                       | 落点                                   |
| - | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 1 | **Kernel API = 生命周期 API，不是业务 API**：禁 `analyze_market()/make_decision()/select_stock()`；Kernel 不知股票/行业/偏好/策略，只知「如何创建一次智能运行」                                                                                                                                                                               | Q1.4 新增                              |
| 2 | **RuntimeContext 分层为 7 个** **`*_context`**：`identity / task / experience / policy / environment / constraint / metadata`，与 RuntimeSituation 对应；`environment_context` 承接未来市场认知（market\_state/liquidity\_state/risk\_state），不污染 Kernel                                                                     | Q2 schema 重构为分层                      |
| 3 | **RuntimeEvent 必须含 execution identity**：`{event_id, run_id, timestamp, event_type, payload}`，`run_id` 必须来自 Kernel，**RuntimeEvent 不得自生 run\_id**                                                                                                                                                          | Q3.5 新增 event identity envelope      |
| 4 | **Selection 输出不是 Artifact**：`Selector → ExperienceSelection → Projection → RuntimeContext`；Selection 是一次运行决策（per-run），Artifact 是资产，生命周期不同，**Selection 不改 Artifact**                                                                                                                                      | Q4 强化 ExperienceSelection ≠ Artifact |
| 5 | **禁止横向依赖**：禁 `agent-runtime → experience-runtime`、禁 `experience-artifact → runtime-kernel`；保持 DAG，顶点是 Context Provider                                                                                                                                                                                   | Q5.3/Q5.5 强化 DAG                     |
| 6 | **新增 Q6：Runtime Kernel 不读 Meta Context**：禁 `kernel.load(".shanhai-meta")/read(cognition.json)/read(decision registry)`；链路 `Context Foundation → Context Provider → RuntimeContext → Kernel`，Runtime 只见投影后上下文（DEC-0002 一致）；并明确 Domain Provider = **Provider 非 Plugin**（提供输入，不改行为，不得 override `execute()`） | 新增 Q6                                |

***

## 0. 本轮要冻结什么 / 不冻结什么

| 冻结（contract freeze）                                                           | 不冻结（留 implementation phase） |
| ----------------------------------------------------------------------------- | --------------------------- |
| Kernel public contract 的**方法集与语义边界**（Q1）                                      | 方法内部实现 / 具体类层级              |
| RuntimeContext v1 的**顶层字段集与不变量**（Q2）                                          | 各 `*_context` 内部子字段细节（仍可扩展） |
| RuntimeEvent 的**载体与边界**（Q3，复用 RunResult/Step，不新造 schema）                      | 是否物化离散事件流（按需再 Review）       |
| ExperienceSelector 的**接口签名与契约**（Q4，`select(situation, candidates)→selection`） | SelectionStrategy 的打分维度实现   |
| **包依赖图**（Q5，单向不成环）                                                            | 各包内部模块拆分                    |

> 「冻结」= 在文档层确立稳定契约形态，作为后续实现的对照基准；**不等于落地代码**。本轮零代码改动。

***

## Q1 — Runtime Kernel public contract

### Q1.1 契约方法集（冻结）

Kernel 对外暴露四个方法，与 v0.4 Q2 生命周期状态机一一对应。**Kernel 是 orchestrator，不是 executor**（v0.4 约束 1）：四个方法都是「协调动作」，执行委派给 agent-runtime。

```python
# 契约示意（非实现），冻结的是方法集与语义边界，不是内部实现
class RuntimeKernel:

    def create(self, *, agent, input, situation=None) -> RuntimeHandle:
        """CREATED：mint run_id，初始化运行元数据。不读 Meta、不跑 Agent。"""

    def assemble(self, handle: RuntimeHandle) -> RuntimeContext:
        """ASSEMBLING→READY：经 experience-runtime 做 Selection+Projection，
        装配只读 RuntimeContext 并冻结。不修改 Artifact、不写 ExperienceEvent。"""

    def execute(self, context: RuntimeContext) -> RunResult:
        """RUNNING→COMPLETED：把冻结的 RuntimeContext 交 AgentRunner.run 执行，
        随后 collect_events 落 RunStore。不接管 think/act/observe（agent-runtime）。"""

    def close(self, handle: RuntimeHandle) -> None:
        """CLOSED：释放 per-run 资源（含 Projection 视图），终态标记。
        不缓存 Selection 结果为跨运行共享。"""
```

> 采纳 Review 批准的调用形态（`execute` 入参为 `RuntimeContext`，因 RuntimeContext 内含 `identity_context.run_id`，可回溯 handle）：
>
> ```python
> run     = kernel.create()
> context = kernel.assemble(run)
> result  = kernel.execute(context)
> kernel.close(run)
> ```

### Q1.2 方法 ↔ 状态机 ↔ 职责对照（冻结）

| 方法           | 状态迁移                           | 职责                                                                         | 明确不做                                                        |
| ------------ | ------------------------------ | -------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `create()`   | `→ CREATED`                    | mint `run_id`（身份诞生点）、初始化元数据                                                | 不读 Meta、不跑 Agent、不装配                                        |
| `assemble()` | `CREATED → ASSEMBLING → READY` | Selection + Projection → 装配只读 `RuntimeContext`，READY 后冻结                   | 不修改 Artifact、不写 ExperienceEvent、不执行                         |
| `execute()`  | `READY → RUNNING → COMPLETED`  | 委派 `AgentRunner.run(input, runtime_context)` + `collect_events` 落 RunStore | **不接管 think/act/observe**、不跑 Evaluation、不直发 ExperienceEvent |
| `close()`    | `COMPLETED/FAILED → CLOSED`    | per-run 资源回收、终态标记                                                          | 不跨运行缓存 Selection/Projection                                 |

> 注：v0.4 Q2 的 `collect_events` 不作为独立 public 方法暴露，而是**收编进** **`execute()`** **的尾段**（执行完即收集落库），保持对外契约为四方法。内部实现可再分。

### Q1.3 契约不变量（冻结）

* **四方法严格顺序、不可逆**：`create → assemble → execute → close`，对应 `CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED`；**禁** **`RUNNING→ASSEMBLING`**（snapshot 不可重装配，v0.4 约束 2）。失败任一步 → 直接 `close`（标 FAILED）。

* **orchestrator≠executor**：Kernel 不持有 `AgentRunner / ToolRegistry / ModelRouter` 实例；`execute` 是「委派」（v0.4 约束 1）。

* **身份贯穿**：`run_id` 在 `create` 诞生，`RuntimeContext / RuntimeEvent / RunRecord` 共用同一 `run_id`（DEC-0005）。

* **RuntimeContext 在 assemble 末冻结**：`execute` 阶段只读（v0.3 Q1.3 immutable）。

* **向后兼容**：不经 Kernel 直接调用 `AgentRunner.run(input)` 行为不变（v0.3 Q4.2）。

> `RuntimeHandle` 仅为「持有 run\_id + 当前状态 + 装配产物引用」的内部句柄，本轮不冻结其字段细节（implementation phase 定）。

### Q1.4 Kernel API = 生命周期 API，不是业务 API（采纳 Review 约束 1）

冻结一条命名/职责铁律：**Kernel 的 public 方法只能是生命周期动词，禁止出现任何业务动词**。Kernel 不知道领域，只知道「如何创建一次智能运行」。

```python
❌ 禁止（业务 API 渗入 Kernel → Kernel 被领域焊死）：
   kernel.analyze_market()
   kernel.make_decision()
   kernel.select_stock()

✅ 正确（只有生命周期 API）：
   run     = kernel.create()       # 创建一次运行（mint run_id）
   context = kernel.assemble(run)  # 装配只读 RuntimeContext
   result  = kernel.execute(context)
   kernel.close(run)
```

| Kernel **不知道**    | Kernel **只知道**        |
| ----------------- | --------------------- |
| 股票 / 行业 / 公告 / 行情 | 如何创建一次智能运行（create）    |
| 用户投资偏好            | 如何装配运行的认知环境（assemble） |
| 交易/选股/择时策略        | 如何委派执行（execute）       |
| 任何领域语义            | 如何收束并释放（close）        |

> 这与 v0.4 Q1.3「orchestrator≠executor」、Q5.1「generic decision runtime」一脉相承：业务/领域语义全部经 Context Provider 注入 `RuntimeContext`（见 Q2/Q6），Kernel API 表面永远只有四个生命周期方法。

***

## Q2 — RuntimeContext v1 schema

### Q2.1 顶层分层（冻结 v1：7 个 `*_context`，采纳 Review 约束 2）

Review 要求 **RuntimeContext 分层，不要平铺**，且与 RuntimeSituation 的 context 划分对应。**本轮冻结 7 个顶层** **`*_context`**；各 context 内部子字段仍可扩展（v0.3 约束 1：冻结边界不冻结子字段）。

```python
# RuntimeContext v1（契约冻结：7 个顶层 *_context + 不变量；子字段可扩展）
RuntimeContext(
    identity_context,     # 运行身份（run_id 等稳定不可变标识符）        ← Kernel.create()
    task_context,         # 任务理解（做什么 / 为何做 / 期望什么）         ← Task Understanding
    experience_context,   # 经 Selector→ExperienceSelection→Projection 的只读经验视图 ← Experience Selection
    policy_context,       # 运行策略（步数上限/阈值/超时）               ← Policy System（未来，v1 可空）
    environment_context,  # 运行环境/领域信号（未来市场认知注入点）       ← Context Provider（未来）
    constraint_context,   # 运行约束（只读；源自 Meta 必经单向 ContextProjection）
    metadata_context,     # 可变信息（created_at / status 等，非身份）
)
```

> 与 RuntimeSituation（v0.3 Q3.1 五 context：task/user/environment/capability/constraint）的对应：Situation 是 Selector 的**输入情境**，RuntimeContext 是装配**输出快照**；二者共享 `task/environment/constraint` 命名轴，`identity/experience/policy/metadata` 是 Context 特有的装配产物层。原 `intent_context`（为何做/期望）并入 `task_context` 子字段，不再单列。

### Q2.2 各 context 语义与冻结状态

| `*_context`           | 含义                                                                  | v1 状态                             | 明确不放                                              |
| --------------------- | ------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------- |
| `identity_context`    | 运行身份（`run_id` 等，DEC-0005 稳定标识符）                                     | **冻结必填**                          | 不放时间/状态（入 metadata\_context）                      |
| `task_context`        | 结构化「做什么 / 为何做 / 期望什么」                                               | **冻结必填**                          | 不放工具句柄、prompt 模板、原始对话流                            |
| `experience_context`  | 已策展只读经验视图（rule/expected\_outcome/confidence/provenance 裁剪）          | **冻结必填**（可空视图）                    | 不放 Artifact 原件、不放可写句柄、不放 ExperienceSelection 决策对象 |
| `policy_context`      | 运行级参数（max\_steps/阈值/超时投影）                                           | **冻结字段位，v1 可空**（Policy System 未建） | 不放业务决策逻辑                                          |
| `environment_context` | 运行环境/领域信号；**未来市场认知注入点**（market\_state/liquidity\_state/risk\_state） | **冻结字段位，v1 可空**（DEC-0004 gating）  | 不放领域语义进 Kernel；Kernel 只见通用 `*_context`（Q6）        |
| `constraint_context`  | 运行边界（禁用工具/风险红线）                                                     | **冻结字段位，v1 可空**                   | 不直接塞 cognition.json/DecisionRecord（DEC-0002）      |
| `metadata_context`    | 时间/状态等可变信息                                                          | **冻结必填**                          | 不放身份（身份归 identity\_context）                       |

> **`environment_context`** **是分层的关键收益**：未来资本市场认知作为 Context Provider 产出 `environment_context = {market_state, liquidity_state, risk_state}` 注入，**不污染 Kernel、不改 schema 顶层**——新增领域只填充 `environment_context` 子字段（Q6 + v0.4 Q5.4）。

### Q2.3 RuntimeContext v1 不变量（冻结）

* **immutable**：`Kernel assemble → RuntimeContext(read-only) → AgentContext`；**禁 Agent 回写**（v0.3 约束 2）。运行态进 AgentContext（steps/observations），绝不回写 RuntimeContext。

* **方向单向**：`RuntimeContext → AgentContext`，禁反向。

* **身份在 identity\_context**：`run_id` 归 `identity_context`（DEC-0005 稳定不可变标识符）；时间/状态等可变信息归 `metadata_context`。

* **不含 Meta 原件**：治理约束只经单向只读 ContextProjection（Meta→Policy），永不共享 schema（DEC-0002，见 Q6）。

* **不含资产原件**：`experience_context` 只放投影视图，不放 Artifact 存储对象、不放 ExperienceSelection 决策对象（Q4）。

* **RuntimeContext ≠ AgentContext**：前者是执行前认知装配快照；后者是执行期能力句柄（router/tool/memory/steps），二者不合并。

> v1 与未来扩展：领域信号经 Context Provider 注入 `environment_context` 子字段（**加子字段而非改顶层**）；`policy_context` 待 Policy System 落地后充实。冻结 7 个顶层 `*_context` 即冻结**装配边界**。

***

## Q3 — RuntimeEvent schema

### Q3.1 schema（冻结：复用既有载体，不新造）

v0.2/v0.4 已确立 RuntimeEvent ≈ `RunResult/Step`。**v0.5 冻结：RuntimeEvent 复用** **`RunResult`（run 级）+** **`Step`（步级），不新建并行 schema、不新建 RuntimeEventStore**（v0.4 约束 5）。

```python
# 复用 services/agent-runtime 既有类型（不改 types.py）：
RunResult(agent, status, output, steps: list[Step], error)      # run 级
Step(index, type: think|act|observe, content, tool, tool_args, tool_result)  # 步级

# 语义事件类型（run_started / step_completed / tool_called / tool_failed / run_finished）
# = Step/Status 的「视图投影」，本轮不物化为离散事件表（按需再 Review）。
```

### Q3.2 契约边界（冻结）

| 契约项                   | 冻结内容                                                                                                                    |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **schema**            | `RunResult` + `Step`（复用，不新造）。语义事件 = 视图投影，不物化。                                                                           |
| **producer**          | **唯一 = Runtime Kernel** **`execute`** **内的 collect 段**（经 AgentRunner 产出 RunResult）。其它模块不得生产。                            |
| **consumer**          | **仅 Evaluation 只读消费**。**禁 ExperienceSelector 消费**（v0.3 约束 7）。                                                           |
| **persistence**       | 复用 `RunStore`（定位 = **Execution Trace Store**，不拆，v0.4 约束 5）；best-effort 落库。                                              |
| **fact ≠ experience** | RuntimeEvent 是**事实**；`tool_failed` 等必经 **Evaluation** 才能升格 ExperienceEvent；**禁 RuntimeEvent → Artifact 直连**（v0.4 约束 4）。 |

### Q3.3 唯一通路（冻结铁律）

```
producer                          consumer
Runtime Kernel ─► RuntimeEvent ─► RunStore ─► Evaluation ─► ExperienceEvent ─► … ─► Artifact
(execute/collect)  (RunResult)    (Trace Store)  (只读，事实→经验闸门)

❌ 禁止：RuntimeEvent ─► ExperienceSelector      （运行事实污染经验消费）
❌ 禁止：RuntimeEvent ─► Artifact                （事实直接资产化，绕过 Evaluation）
❌ 禁止：其它模块直接生产 RuntimeEvent
```

### Q3.4 run\_id 前移（方向已批，本轮不改代码）

`RunStore` 从 *create identity* 转 *persist identity*：`run_id` 由 `Kernel.create()` mint，`save_run(result, run_id=...)` 接受外部身份（不传则向后兼容内部 mint）。**implementation phase 再改 store.py**（v0.4 Q3.4）。

### Q3.5 RuntimeEvent 必须含 execution identity（冻结，采纳 Review 约束 3）

RuntimeEvent 在「内容载体」（RunResult/Step）之外，必须携带一层 **execution identity envelope**，且 `run_id` **必须来自 Kernel**，事件**不得自生 run\_id**：

```python
# RuntimeEvent identity envelope（冻结字段位；payload 复用 RunResult/Step）
RuntimeEvent(
    event_id,     # 事件自身标识（事件层 mint，仅标识「这条事件」）
    run_id,       # 执行身份 —— 必须来自 Kernel.create()，事件不得自生
    timestamp,    # 事件时间
    event_type,   # run_started / step_completed / tool_called / tool_failed / run_finished
    payload,      # 内容载体 = RunResult / Step 视图（Q3.1，不新造 schema）
)
```

身份来源链（冻结，闭环关键）：

```
Kernel.create()  ──►  run_id  ──►  RuntimeContext.identity_context  ──►  RuntimeEvent.run_id
                                                                              │
                                            Context → Execution → Experience  ▼  完整闭环
```

| 字段         | 谁 mint              | 约束                                                                           |
| ---------- | ------------------- | ---------------------------------------------------------------------------- |
| `run_id`   | **Kernel.create()** | 全链唯一身份；RuntimeContext / RuntimeEvent / RunRecord 共用同一值（DEC-0005）；**事件层禁止自生** |
| `event_id` | 事件层                 | 仅标识单条事件，不充当运行身份                                                              |

> 这把 v0.4 Q3.4「run\_id 前移」从「持久化解耦」上升为**闭环必要条件**：只有 `run_id` 从 Kernel 一路贯穿 Context→Event，`Context → Execution → Experience` 才能按同一身份归因、回流。`event_id/timestamp/event_type` 为 envelope 字段位，**本轮只冻结契约形态，不实现**（payload 仍复用既有 RunResult/Step，不新建事件表）。

***

## Q4 — ExperienceSelector interface

### Q4.1 接口签名（冻结）

ExperienceSelector = **stateless reasoning service**；接口为 `select(situation, candidates) → selection`，落 `services/experience-runtime`（v0.3 约束 6）。

```python
# 接口契约（非实现），落 services/experience-runtime
class ExperienceSelector(ABC):
    @abstractmethod
    def select(
        self,
        situation: RuntimeSituation,        # 判断依据（5 context，v0.3 Q3.1）
        candidates: Iterable[ArtifactView],  # 判断对象（候选池，经 ArtifactReader 提供）
    ) -> Selection:                          # 打分→排序→top-k 的结果（非布尔 filter）
        ...

# 输入情境（v0.3 Q3.1，5 context；冻结顶层，子字段可扩展）
RuntimeSituation(
    task_context, user_context, environment_context, capability_context, constraint_context,
)

# 输出（冻结形态：携带排序与依据，便于 Projection 与可观测归因）
Selection(
    selected: list[ScoredArtifact],   # 已排序 top-k，每项含 score + 命中维度
    rationale,                        # 选择依据（可观测/可追溯，绑定 run_id）
)
```

### Q4.2 接口契约（冻结）

| 契约项              | 冻结内容                                                                                                      |
| ---------------- | --------------------------------------------------------------------------------------------------------- |
| **形态**           | stateless service（长生命周期、无运行间状态、可单例/可注入）；输出仅由入参决定                                                          |
| **输入**           | `situation`（判断依据）+ `candidates`（判断对象）；二者角色分离（v0.3 Q3.1）                                                   |
| **输出**           | `Selection`（打分+排序+top-k，**结构上必须是可扩展打分**，非 `filter(==)`，v0.3 Q3.2）                                         |
| **不是 Retrieval** | Selection ≠ Retrieval；Selector 是 reasoning component over candidates，vector search 至多是其中一个打分子项（v0.3 约束 3） |
| **不学习**          | Selector 不持跨运行记忆；跨运行学习（更新 Artifact）归 **Evolution**（v0.4 约束 6）                                             |
| **策略可插拔**        | 背后 `SelectionStrategy` 可替换；MVP 即便少维度，结构仍是「打分+排序+截断」                                                       |
| **候选来源**         | 经 `ArtifactReader`（内部 read port，Commit 7 前置）提供，**禁 RuntimeEvent 入候选**                                     |

### Q4.3 与 Projection / RuntimeContext 的衔接（冻结）

```
ArtifactReader.candidates ─► ExperienceSelector.select(situation, candidates)
                                        │
                                        ▼  Selection（per-run，不跨运行缓存）
                              ExperienceProjection.project(selection)
                                        │
                                        ▼  只读经验视图
                              RuntimeContext.experience_context（immutable）
```

> 本轮**只冻结接口形态，不实现** Selector/Projection/Reader（Commit 7 仍冻结，待此接口批准后解冻）。

### Q4.4 Selection 输出不是 Artifact（冻结铁律，采纳 Review 约束 4）

这是本轮要钉死的一条经验侧语义铁律：**Selector 的输出是** **`ExperienceSelection`（一次运行决策），不是** **`Artifact`（资产）**。二者生命周期不同，**Selection 永不改写 Artifact**。

```
❌ 禁止（Selector 直接产出/改写资产 → 选择决策污染资产层）：
   ExperienceSelector ──► Artifact

✅ 正确（经中间决策对象，逐层投影进运行）：
   ExperienceSelector ──► ExperienceSelection ──► Projection ──► RuntimeContext
                          (per-run 运行决策)      (裁剪视图)      (immutable 经验视图)
```

| <br /> | `ExperienceArtifact`（资产）                    | `ExperienceSelection`（运行决策）        |
| ------ | ------------------------------------------- | ---------------------------------- |
| 性质     | 已验证、可复用的**能力单元**（ADR0018）                   | 「本次运行选了哪些经验 + 为何选」的一次性判断           |
| 生命周期   | 长生命周期，跨运行存在，经 Evolution 演化                  | per-run，随 RuntimeContext 生命周期结束即消亡 |
| 可变性    | 只读资产，仅 Evolution 可演化其 confidence/evaluation | 不回写任何资产；Selector 只「读」资产做即时推理       |
| 归属     | `experience-artifact`（生产/资产侧）               | `experience-runtime`（消费/运行侧）       |

> 关键例证（生命周期不同的直观体现）：**同一个 Artifact，上午被选中、下午可能不被选**——因为 Selection 是 `situation` 的函数（per-run 情境推理），而 Artifact 的内容不随某次选择改变。若让 Selection 改写 Artifact，则「这次没选它」会错误地降级一个本身有效的资产。故 **Selection 不改 Artifact**，二者经 `ExperienceSelection → Projection` 单向流入运行，与 Q4.2「Selector 不学习、学习归 Evolution」一脉相承（读写对偶：Selector 读、Evolution 写）。

***

## Q5 — Package dependency graph

### Q5.1 目标包结构（冻结）

```
services/
├── context-foundation      （Meta / DEC-0002，单向只读经 ContextProjection）
├── experience-artifact     （Artifact schema / lifecycle，生产侧 storage boundary，ADR0018）
├── experience-evolution    （Candidate → Promotion → ArtifactBuilder，生产侧）
├── experience-runtime      （Selection / Projection / Runtime adaptation，消费侧，v0.3 约束 6）
├── runtime-kernel ⭐        （Context Assembly / Experience Selection 编排 / Runtime Boundary）
└── agent-runtime           （Agent execution / Tool calling / LLM interaction，executor）
```

### Q5.2 依赖图（冻结，单向不成环）

```
                         runtime-kernel
                          ╱         ╲
                         ▼           ▼
               experience-runtime   agent-runtime
                         │
                         ▼
               experience-artifact
                         │
                         ▼  （只读）
                 experience（events）

context-foundation ──(单向只读 ContextProjection, Meta→Policy)──► runtime-kernel
（未来）market-cognition-provider ──产出 *_context──► RuntimeSituation （Q5.4 Domain Provider，不进 runtime-kernel）
```

### Q5.3 依赖规则（冻结铁律）

| 允许                                                            | 禁止                                                              |
| ------------------------------------------------------------- | --------------------------------------------------------------- |
| `runtime-kernel → agent-runtime`（委派执行 AgentRunner）            | `agent-runtime → runtime-kernel`（执行层不得上浮）                       |
| `runtime-kernel → experience-runtime`（Selection/Projection）   | `experience-runtime → runtime-kernel`                           |
| `experience-runtime → experience-artifact`（读 Artifact schema） | `agent-runtime → experience-runtime`（执行层不得依赖经验消费层）              |
| `experience-evolution → experience-artifact`（生产侧已立，ADR0018）   | `experience-artifact → experience-runtime`（生产不得知消费方式，v0.3 约束 6） |
| `context-foundation → runtime-kernel`（单向只读 ContextProjection） | 任何指向 `context-foundation` 的 Runtime 反向写（DEC-0002）               |

### Q5.4 Domain Provider 不进依赖图核心（冻结，v0.4 约束 8）

领域能力（如 `market-cognition-provider`）是 **Context Provider 不是 Kernel plugin**：产出 `market_state_context / risk_context / industry_context` **注入 RuntimeSituation 的** **`environment_context`**，`runtime-kernel` 全程只见通用 `*_context`，不知道股票/公告/行情。**本轮不建 provider**（DEC-0004 gating）。

### Q5.5 禁止横向依赖，保持 DAG（冻结铁律，采纳 Review 约束 5）

Review 钉死一条结构铁律：**依赖图必须是 DAG，禁止任何横向/反向依赖**。顶点是 **Context Provider**（认知装配的源头），所有依赖单向向下，永不成环。

```
                  Context Provider          ← 顶点（认知装配源头）
                        │
                        ▼
                  runtime-kernel             ← orchestrator
                   ╱          ╲
                  ▼            ▼
        experience-runtime   agent-runtime   ← 两条并行下游，互不依赖
                  │
                  ▼
         experience-artifact                 ← 资产侧（生产不知消费）
```

显式禁止（横向/反向，任一出现即破坏 DAG）：

```
❌ agent-runtime ──► experience-runtime      （执行层横向依赖经验消费层）
❌ experience-runtime ──► agent-runtime      （经验消费层横向依赖执行层）
❌ experience-artifact ──► runtime-kernel    （资产侧反向上浮到 orchestrator）
❌ experience-artifact ──► experience-runtime（生产侧反向知道消费方式，v0.3 约束 6）
❌ agent-runtime ──► runtime-kernel          （执行层上浮到 orchestrator）
❌ experience-runtime ──► runtime-kernel     （下游反向依赖 orchestrator）
```

> 关键判断：`experience-runtime` 与 `agent-runtime` 是 `runtime-kernel` 的**两条并行下游分支**，二者之间**没有任何依赖边**——执行（agent-runtime）与经验消费（experience-runtime）在 Kernel 处汇合，而非互相调用。任何把这两支连起来、或把下游连回 Kernel/Context Provider 的边，都会引入环或横向耦合，**一律禁止**。这与 Q1.3 orchestrator≠executor、Q4.4 Selection 不改 Artifact 共同保证整图无环。

***

## Q6 — Runtime Kernel 与 Context Foundation 的边界（新增，采纳 Review 约束 6）

这是 Review 新增、并被指认为「未来最容易犯错的地方」的一条边界。冻结一条铁律：**Runtime Kernel 永不读取 Meta Context**。

### Q6.1 Runtime Kernel 不读 Meta Context（冻结铁律）

```
❌ 禁止（Kernel 直接触达 Meta 层 → 击穿 DEC-0002 Meta↔Runtime 分离）：
   kernel.load(".shanhai-meta")
   kernel.read(cognition.json)
   kernel.read(decision_registry)

✅ 正确（Meta 经投影逐层下沉，Kernel 只见投影后上下文）：
   Context Foundation ──► Context Provider ──► RuntimeContext ──► Runtime Kernel
   (facts/decisions/cognition)  (投影/裁剪)     (只读快照)        (只消费快照)
```

| Runtime Kernel **看得见**                                     | Runtime Kernel **看不见**                |
| ---------------------------------------------------------- | ------------------------------------- |
| 投影后的 `RuntimeContext`（7 个 `*_context`）                     | `.shanhai-meta` 目录                    |
| `constraint_context`（经 ContextProjection 的 Meta→Policy 视图） | `cognition.json` 原件                   |
| `environment_context`（经 Provider 的领域信号视图）                  | DecisionRecord / decision registry 原件 |

> 即：**Runtime 看到的是投影后的上下文，不是 Meta 数据**。Meta 层（facts/decisions/cognition）只能经 **Context Provider 投影**单向下沉为 `RuntimeContext` 的某个 `*_context` 子字段；Kernel 不持有任何指向 `.shanhai-meta` 的读路径。这与 [DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)（Meta↔Runtime 严格分离、不共享不转换）完全一致，也是 Q5.5 DAG「顶点是 Context Provider」的语义来源——Kernel 的上游是 Provider，不是 Meta。

### Q6.2 Domain Provider = Provider 不是 Plugin（冻结）

承接 v0.4 Q5.4，进一步钉死 **Provider 与 Plugin 的语义区别**：

| <br />      | **Provider**（✅ 山海采用）                               | **Plugin**（❌ 禁止形态）                    |
| ----------- | -------------------------------------------------- | ------------------------------------- |
| 作用          | **提供 Runtime 输入**（产出 `*_context`）                  | **改变 Runtime 行为**（注入/覆盖逻辑）            |
| 与 Kernel 关系 | 在 Kernel 之上游，喂数据进 RuntimeSituation/RuntimeContext  | 嵌入 Kernel 内部，篡改其执行路径                  |
| 例           | `MarketCognitionProvider` 输出 `environment_context` | （禁）`override RuntimeKernel.execute()` |

```
✅ 正确（Provider 提供输入，不碰 Kernel 行为）：
   MarketCognitionProvider ──► environment_context ──► RuntimeContext ──► Kernel（照常 create/assemble/execute/close）

❌ 禁止（Plugin 改变行为，焊死领域语义进 Kernel）：
   MarketTradingPlugin ──► override RuntimeKernel.execute()
```

> 一句话区分：**Plugin 改变 Runtime 行为，Provider 提供 Runtime 输入**。领域能力一律以 Provider 形态接入（产出 `*_context`），**绝不允许 override 任何 Kernel 生命周期方法**（`create/assemble/execute/close`）。这保证 Kernel 永远是 generic decision runtime（v0.4 Q5.1），新增任意领域只增加 Provider、不改 Kernel 一行。

***

## D. 契约冻结清单（Review 决议对照 + 6 约束）

| Q  | 冻结项                            | 结论                                                                                                                                                                                |
| -- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q1 | Kernel public contract         | `create() / assemble() / execute() / close()`，四方法严格顺序不可逆，orchestrator≠executor；**生命周期 API 非业务 API**（约束 1）                                                                         |
| Q2 | RuntimeContext v1 schema       | 顶层 **7 个** **`*_context`**（identity/task/experience/policy/environment/constraint/metadata），immutable，子字段可扩展（约束 2）                                                                |
| Q3 | RuntimeEvent schema            | 复用 RunResult/Step，外加 **execution identity envelope**（event\_id/run\_id/timestamp/event\_type/payload），**run\_id 必来自 Kernel**；producer=Kernel，consumer=Evaluation only，事实≠经验（约束 3） |
| Q4 | ExperienceSelector interface   | stateless `select(situation, candidates)→Selection`，**输出是 ExperienceSelection 非 Artifact**（`Selector→Selection→Projection→RuntimeContext`），不学习，落 experience-runtime（约束 4）         |
| Q5 | Package dependency graph       | runtime-kernel→{experience-runtime→experience-artifact, agent-runtime}，**DAG 禁横向依赖**，顶点 Context Provider（约束 5）                                                                    |
| Q6 | Kernel / Context Foundation 边界 | **Kernel 不读 Meta**（`Context Foundation→Provider→RuntimeContext→Kernel`）；**Domain Provider = Provider 非 Plugin**，不得 override 生命周期方法（约束 6）                                          |

***

## E. 待决项（v0.5 冻结后才考虑，逐项再解冻批准）

| 待决项                                                                      | 依赖前置               | 倾向                                           |
| ------------------------------------------------------------------------ | ------------------ | -------------------------------------------- |
| `services/runtime-kernel` package skeleton                               | v0.5 五项冻结获批        | 空包骨架，依赖 agent-runtime + experience-runtime   |
| `services/experience-runtime` package skeleton                           | 同上                 | 消费侧空包（Selector/Projection 占位）                |
| RunStore identity migration（run\_id 前移 + `save_run(result, run_id=...)`） | Q1/Q3 冻结 + 兼容验证    | 外部传入，默认仍内部 mint（向后兼容）                        |
| `AgentRunner.run(input, runtime_context)` 接口扩展                           | Q2 冻结              | 可选入参，默认 None=现行为                             |
| ExperienceSelector MVP（少维度打分）                                            | Q4 冻结              | 结构=打分+排序+top-k，非 filter                      |
| RuntimeContext implementation                                            | Q2 冻结              | immutable 数据结构                               |
| ArtifactReader 接口形态（Commit 7）                                            | Q4 候选来源冻结          | `find_by_context/find_applicable`，非 `list()` |
| domain cognition provider（市场认知）                                          | 远期，DEC-0004 gating | 现在不做                                         |

***

## F. 非目标 / 约束（继续遵守，保持 Review Gate）

* **本阶段只冻结契约、不编码**：不建 `runtime-kernel`/`experience-runtime` 包、不实现 Selector/Projection/RuntimeContext、不改 RunStore/AgentRunner、不接 Memory、不解冻 Commit 7。

* 不引入 Vector / Graph / Retrieval / embedding / 市场 regime / 用户偏好建模 / Memory 持久化写入。

* 不破坏冻结不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）、身份原则（DEC-0005）、市场认知 gating（DEC-0004）、agent-runtime v0.2.0 契约。

* ADR 0018 维持 **MVP Contract Established**，**不 Finalize**。

***

## G. 下一步（Contract Frozen → 进入 v0.6 Implementation Boundary Review）

1. v0.5 六问契约 + 6 约束已 **Contract Frozen**（Review 原则批准）。
2. 进入 **[Runtime Kernel v0.6 — Implementation Boundary Review](runtime-kernel-v0.6-implementation-boundary.md)**（**仍 Design Only**），冻结实现边界：Q1 runtime-kernel package skeleton（哪些文件存在）｜Q2 RuntimeContext python model（是否 Pydantic）｜Q3 RunStore identity migration（run\_id 如何前移）｜Q4 Experience Runtime MVP（Selector/Projection/Reader 三者关系）｜Q5 第一条 end-to-end flow（create→RuntimeContext→AgentRunner→RuntimeEvent→Evaluation→Artifact）。
3. v0.6 通过后，方可进入 implementation phase（仍需逐项解冻批准）。

> 当前完成状态：✅ Context Foundation Frozen｜✅ Conversation Ingestion｜✅ Experience Artifact Production Chain｜✅ RuntimeContext Direction Approved｜✅ Runtime Kernel Architecture v0.4 Direction Approved｜✅ **Runtime Kernel v0.5 Contract Frozen（含 6 约束）**｜⏳ **Runtime Kernel v0.6 Implementation Boundary Review — 待批准**。

> 当前停在 **Review Gate**，Design Only。不进入代码、不建包、不改 RunStore/AgentRunner、不实现 RuntimeContext/Selector、不解冻 Commit 7。

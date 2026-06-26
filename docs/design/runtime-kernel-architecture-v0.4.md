# Runtime Kernel Architecture Review v0.4（设计稿，仅讨论，不编码）

> 状态：**✅ Direction Approved（v0.4 方向获批）→ 冻结进入 [v0.5 Contract Freeze](runtime-kernel-v0.5-contract-freeze.md)** — Review 批准五问方向，补充 8 条约束（含新增 §8 Domain Provider Boundary），已折入本文 §0.A。仍 Design Only，不建包、不改 RunStore/AgentRunner。
> 状态（历史）：Design Review（v0.4）— 回答 Q1 独立包 / Q2 状态机 / Q3 RuntimeEvent / Q4 Selector 生命周期 / Q5 与资本市场关系。
> 阶段：Phase 1 — Agent Runtime / Runtime Kernel Architecture。
> 前置：[Runtime Context API v0.3](runtime-context-api-v0.3.md) ✅ Direction Approved（含 7 条架构约束）；[Runtime Kernel Design v0.2](runtime-kernel-v0.2.md) ✅ Direction Approved；[v0.1](runtime-kernel-v0.1.md) Principle Approved。
> 本轮聚焦五问（**重点是 Kernel 本体工程形态与生命周期，不是 API**）：**Q1** Kernel 是否独立 package｜**Q2** Kernel 生命周期状态机｜**Q3** RuntimeEvent Contract｜**Q4** ExperienceSelector 生命周期｜**Q5** 与 AI Native 资本市场认知系统的关系。
> 关联：[ADR 0006 执行模型]、[ADR 0008/0009 RunStore]、[ADR 0018 Artifact](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0004](../../.shanhai-meta/decisions/records/DEC-0004-future-market-cognition.md)、[DEC-0005](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

---

## 0. 现状对账（动笔前盘点真实代码）

| 既有件 | 位置 | 与本轮相关事实 |
|---|---|---|
| `AgentRunner.run(input)` | [runner.py](../../services/agent-runtime/shanhai_agent_runtime/runner.py) | 生命周期已部分存在：`new_context → loop(think/act/observe) → RunResult → _persist`。**但无「装配」前段、无「close」语义**。 |
| `RunResult / Step` | [types.py](../../services/agent-runtime/shanhai_agent_runtime/types.py) | RuntimeEvent 的内容载体（v0.2 §A 已对账）。 |
| `RunStore / RunRecord` | [store.py](../../services/agent-runtime/shanhai_agent_runtime/store.py) | RuntimeEvent 日志载体。**关键：`run_id` 当前在 `save_run` 内由 `uuid4` 生成**——即身份在**运行结束落库时**才产生。 |
| `AgentContext` | [context.py](../../services/agent-runtime/shanhai_agent_runtime/context.py) | 执行期能力句柄，v0.3 已确定 `RuntimeContext → AgentContext` 单向。 |

> ⚠️ **一个必须在本轮暴露的张力（影响 Q2/Q3）**：v0.3 把 `run_id` 定为 RuntimeContext 的**身份**（运行前装配即存在，DEC-0005）；而现状 `run_id` 是 **`RunStore.save_run` 运行后**才 mint 的。二者时点冲突——Kernel 生命周期一旦确立「create 即有身份」，`run_id` 的生成点必须**前移到 Kernel create**，`RunStore` 改为「接受外部 run_id」。本轮只**记录该决策方向**，不改代码（见 Q2.3 / Q3.4）。

---

## 0.A Review 补充约束（v0.4 获批附带，已折入下文）

Review 批准五问方向，补充 8 条约束（含 1 条新增设计 §8 Domain Provider Boundary）：

| # | 约束 | 落点 |
|---|---|---|
| 1 | **runtime-kernel 不拥有 Agent 生命周期**：Kernel = orchestrator（Context Assembly / Experience Selection / Runtime Boundary），**不持 AgentRunner / Tool execution / Model call**；执行归 agent-runtime | Q1.3 增「orchestrator≠executor」铁律 |
| 2 | Kernel 生命周期补**显式状态枚举 + 不可逆**：`CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED`，禁 `RUNNING→ASSEMBLING`（snapshot 不可重装配） | Q2.1 状态机改为命名态 + 不可逆 |
| 3 | **run_id 生命周期前移获批**：RunStore 从 *create identity* 变 *persist identity*；**但不现在改代码**，留 implementation phase | Q3.4 标注「已批准方向，implementation phase 再改」 |
| 4 | **RuntimeEvent 是事实不是经验**：`tool_failed` 等必经 Evaluation，禁 `RuntimeEvent → Artifact` 直连 | Q3.2 强化 |
| 5 | **RunStore 不拆**：复用为 Execution Trace Store，未来在其内演化 RuntimeEvent/RunResult/Trace 视图，不建 RuntimeEventStore | Q3.1 强化 |
| 6 | **Selector 不学习，Evolution 学习**：stateless ≠ 无状态智能；跨运行学习（更新 Artifact）归 Evolution | Q4.2 强化 |
| 7 | 保持 **Generic Decision Runtime**，不是 Market Trading Runtime；市场认知是领域能力（类比 Python runtime ↑ Data Science package） | Q5.1 强化 |
| 8 | **新增 Domain Provider Boundary**：领域能力是 **Context Provider 不是 Kernel plugin**；如 `market-cognition-provider` 产出 `market_state_context/risk_context/industry_context` **注入 RuntimeSituation**，而非让 runtime-kernel 知道股票/公告/行情 | 新增 Q5.4 |

---

## Q1 — Runtime Kernel 是否成为独立 service/package？

### Q1.1 选项

```
A. agent-runtime 内子模块            B. 独立 package services/runtime-kernel
   services/agent-runtime               services/runtime-kernel
     └── kernel/                          依赖 → agent-runtime（调用 AgentRunner）
```

### Q1.2 结论：**B —— 独立 package `services/runtime-kernel`**

| 维度 | A（agent-runtime 内） | B（独立 package）✅ |
|---|---|---|
| 职责边界 | ✗ Kernel = Context Assembly + Run Boundary，会让 agent-runtime 既"执行"又"装配认知"，膨胀为超级模块（v0.1 Q1 明确反对） | ✓ 装配/边界与执行物理分离 |
| 依赖方向 | ✗ 装配需依赖 experience-runtime（Selection/Projection），会让 agent-runtime 反向依赖经验消费侧，破坏现有干净边界 | ✓ Kernel 依赖 agent-runtime + experience-runtime，agent-runtime 保持零经验依赖 |
| 可测试性 | 装配逻辑混在执行里难独立测 | ✓ Kernel 可独立测装配 |
| 向后兼容 | — | ✓ 不传 Kernel 时 `AgentRunner` 行为完全不变（v0.3 Q4.2） |
| 复杂度 | 短期省一个包 | 多一个包（可接受成本） |

依赖方向（新增，单向不成环）：

```
runtime-kernel ─► agent-runtime        （调用 AgentRunner 执行）
runtime-kernel ─► experience-runtime   （Selection / Projection，v0.3 约束 6）
runtime-kernel ─► (未来) context-projection（Meta→Policy 单向只读，v0.2 §C.3）

禁止反向：agent-runtime ↛ runtime-kernel；experience-runtime ↛ runtime-kernel
禁止：    agent-runtime ↛ experience-runtime（执行层不得依赖经验消费层）
```

> 关键判断：Kernel 是**上层协调者（orchestrator）**，必须在依赖图的**上游**；把它塞进 agent-runtime 会让最底层的执行包被迫上浮。故选 B。

### Q1.3 铁律：Kernel = orchestrator ≠ executor（采纳 Review 约束 1）

Runtime Kernel 独立出来后，它会成为未来所有 Agent / 领域认知 / 市场决策能力的入口——**最大风险是膨胀为「大总管」**。故冻结一条边界铁律：**Kernel 只编排（orchestrate），不执行（execute）**。

```
❌ 禁止（Kernel 拥有 Agent 生命周期 → 退化为超级执行器）：
   runtime-kernel
     ├── AgentRunner
     ├── Tool execution
     └── Model call

✅ 正确（职责物理切分）：
   runtime-kernel        负责：Context Assembly / Experience Selection / Runtime Boundary
   agent-runtime         负责：Agent execution / Tool calling / LLM interaction
```

| 关注点 | 归属 | 理由 |
|---|---|---|
| Context Assembly（装配只读 RuntimeContext） | **runtime-kernel** | 认知装配是「运行前」的协调动作 |
| Experience Selection（调 Selector→Projection） | **runtime-kernel**（委派 experience-runtime） | 选哪些经验进入运行，是装配的一部分 |
| Runtime Boundary（create/close、run_id、生命周期状态机） | **runtime-kernel** | 边界与身份是协调者职责 |
| Agent execution（think/act/observe loop） | **agent-runtime** | 既有 AgentRunner，Kernel 只 `execute` 委派 |
| Tool calling | **agent-runtime**（经 ToolRegistry，granted 校验） | 执行期能力，非装配期 |
| Model call | **agent-runtime**（经 Model Router） | 执行期能力，非装配期 |

> 即：Kernel **不持有** `AgentRunner / ToolRegistry / ModelRouter` 实例，只在 `execute` 阶段把装配好的 `RuntimeContext` **交给** AgentRunner。这与 Q2.2 `execute` 阶段「不接管 think/act/observe」一致——execute 是「委派」不是「实现」。

---

## Q2 — Runtime Kernel 生命周期（需要冻结状态机）

### Q2.1 状态机（采纳 Review 约束 2：显式命名态 + 不可逆）

Review 要求把生命周期升级为**显式状态枚举**并冻结**不可逆**，理由：**RuntimeContext 是 snapshot，一旦进入执行阶段就不能重新装配认知环境**。

命名态（冻结，单向不可逆）：

```
CREATED ──► ASSEMBLING ──► READY ──► RUNNING ──► COMPLETED ──► CLOSED
   │           │             │          │            │            │
 mint        Selection+    装配完成   交 AgentRunner  RunResult→   释放 per-run
 run_id      Projection→   只读冻结   (think/act/    RuntimeEvent  资源、终态
 (身份诞生)   RuntimeContext           observe)       (写 RunStore)

❌ 禁止回退：RUNNING ──► ASSEMBLING   （snapshot 已冻结，不可重装配认知环境）
失败路径：任一态异常 ──► CLOSED（标 FAILED），不回退到更早态
```

状态态 ↔ 阶段动作对应：

| 状态（名词态） | 触发动作（动词） | 进入条件 |
|---|---|---|
| `CREATED` | `create_runtime()` 完成 | mint `run_id`、初始化元数据 |
| `ASSEMBLING` | `assemble_context()` 进行中 | Selection + Projection 装配 |
| `READY` | `assemble_context()` 完成 | RuntimeContext 装配完成并**冻结只读** |
| `RUNNING` | `execute()` 进行中 | 已交 AgentRunner，执行中 |
| `COMPLETED` | `execute()` 返回 + `collect_events()` 完成 | RunResult 收集并落 RunStore |
| `CLOSED` | `close_runtime()` 完成 | per-run 资源释放、终态标记 |

> 关键不变量：**READY 之后 RuntimeContext 即冻结**；RUNNING 期间任何「想重新选经验/改装配」的需求都不允许就地修改，只能开**新的一次 run**（新 run_id、新 snapshot）。这从状态机层面保证了 v0.3 Q1.3 的 immutability。

### Q2.2 各阶段职责与边界

| 阶段 | 职责 | 明确不做 |
|---|---|---|
| `create_runtime` | **mint `run_id`（身份诞生点）**、初始化运行元数据 | 不读 Meta、不跑 Agent |
| `assemble_context` | 调 ExperienceSelector → Projection → 装配只读 `RuntimeContext` | 不修改 Artifact、不写 ExperienceEvent |
| `execute` | 把 `RuntimeContext` 交 `AgentRunner.run(input, runtime_context)` | **不接管 think/act/observe**（归 agent-runtime，v0.2 §A.6） |
| `collect_events` | 收 `RunResult` → 经 `RunStore` 记为 RuntimeEvent | 不跑 Evaluation（归 services/evaluation）、不直发 ExperienceEvent（v0.3 Q4.4） |
| `close_runtime` | 释放 per-run 资源（含 Projection 视图，v0.3 Q2 per-run）、终态标记 | 不缓存 Selection 结果为跨运行共享（v0.3 Q2.2） |

### Q2.3 状态机不变量（冻结）

- **单向不可逆**：`CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED`，无环、无回退；**禁 `RUNNING→ASSEMBLING`**（snapshot 不可重装配）；失败 → 直接进 `CLOSED`，标 FAILED。
- **身份在 CREATED 诞生**：`run_id` 在 `create_runtime` 生成（前移，见 §0 张力 + Q3.4），贯穿全生命周期；RuntimeContext / RuntimeEvent / RunRecord 共用同一 `run_id`（DEC-0005）。
- **RuntimeContext 在 READY 冻结**：RUNNING 阶段只读（v0.3 Q1.3 immutable）。
- **Kernel 不接管执行**：execute 是「委派」不是「实现」（Q1.3 orchestrator≠executor）。

---

## Q3 — RuntimeEvent Contract（schema / producer / consumer / persistence boundary）

### Q3.1 定位：RuntimeEvent = 运行过程事实，复用既有载体（不新造 schema）

v0.2 §A 已确立 RuntimeEvent ≈ `RunResult/Step`、日志 = `RunStore`。v0.4 把它**契约化**，但**不新建并行 schema**。

| 契约项 | 内容 |
|---|---|
| **schema** | 复用 `RunResult`（run 级）+ `Step`（步级：think/act/observe，含 tool/tool_args/tool_result）。语义事件类型（run_started / step_completed / tool_called / tool_failed / run_finished）作为 **Step/Status 的视图投影**，**本轮不物化为离散事件表**（按需再 Review，v0.2 §A.4）。 |
| **producer** | **唯一生产者 = Runtime Kernel `collect_events`**（经 AgentRunner 产出 RunResult）。其它模块不得生产 RuntimeEvent。 |
| **consumer** | **仅 Evaluation（services/evaluation）只读消费**。**禁止 ExperienceSelector 消费**（v0.3 Q4.4 铁律：`RuntimeEvent → Selector` 禁止）。 |
| **persistence boundary** | 复用 `RunStore`，定位为 **Execution Trace Store**（sqlite/postgres，ADR 0008/0009）。**不拆、不新建 RuntimeEventStore**——未来在 RunStore 内部演化 `RuntimeEvent / RunResult / Execution Trace` 视图（约束 5）。落库为 best-effort（不反噬主流程，沿用 `_persist`）。 |

### Q3.2 生产/消费唯一通路（铁律图）

```
producer                         consumer
Runtime Kernel ─► RuntimeEvent ─► RunStore ─► Evaluation ─► ExperienceEvent ─► … ─► Artifact
(collect_events)   (RunResult)   (持久边界)   (只读)         (经验侧)

❌ 禁止：RuntimeEvent ─► ExperienceSelector   （运行过程污染经验消费，v0.3 Q4.4）
❌ 禁止：其它模块直接生产 RuntimeEvent
```

#### Q3.2.1 RuntimeEvent 是事实，不是经验（采纳 Review 约束 4）

这是本轮要钉死的一条语义铁律：**RuntimeEvent 只是「发生了什么」的客观事实，不是「学到了什么」的经验**。

```
tool_failed             ← 这是事实（fact），不是经验（experience）

❌ 禁止：tool_failed ──► ExperienceArtifact            （事实直接资产化）
✅ 必须：tool_failed ──► Evaluation ──► ExperienceEvent ──► … ──► Artifact
                         （评估：这次失败是否构成可学习经验？为什么？置信度多少？）
```

理由：若任何运行事实都能直连 Artifact，则**所有执行日志都会污染经验库**（一次偶发的网络超时、一次 prompt 笔误造成的 tool_failed 都被当成「经验」）。**Evaluation 是事实→经验之间的强制闸门**：只有经评估判定为「可学习、可复用、有置信度」的事实，才升格为 ExperienceEvent 并进入演化。事实层（RuntimeEvent/RunStore）与经验层（ExperienceEvent/Artifact）之间**不存在直连**。

### Q3.3 RuntimeEvent vs ExperienceEvent vs ContextEvent（三层定稿复述）

| | 语义 | producer | consumer | 存储 |
|---|---|---|---|---|
| ContextEvent | 系统认知变化（Meta） | 人/AI 协作（.shanhai-meta） | Meta 工具链 | context store（Meta） |
| **RuntimeEvent** | 一次运行过程事实 | **Runtime Kernel** | **Evaluation only** | **RunStore** |
| ExperienceEvent | 可学习经验 | Evaluation/Evolution | Candidate/Promotion | ExperienceStore |

### Q3.4 持久边界的一个待解耦点（run_id 前移，**方向已获批，implementation phase 再改**）

现状 `RunStore.save_run` 内部 `uuid4` 生成 `run_id`（运行后 mint）。Kernel 确立「create 即有身份」后，需把 `run_id` 改为**外部传入**——Review 已**批准此方向**，语义上 RunStore 从「创建身份」转为「持久化身份」：

```
现状： save_run(result) → 内部 mint run_id            （RunStore = create identity，身份滞后）
方向： run_id = kernel.create_runtime()              （Kernel = create identity，身份前置）
       save_run(result, run_id=run_id)               （RunStore = persist identity；向后兼容：不传则仍内部 mint）
```

| | 现状 | 获批方向 |
|---|---|---|
| `run_id` mint 点 | `RunStore.save_run`（运行后） | `Kernel.create_runtime`（运行前，CREATED 态） |
| RunStore 角色 | **create identity** | **persist identity** |
| 兼容性 | — | `save_run(result, run_id=None)` 默认仍内部 mint，老调用不破 |

> **本轮只确认方向，不改 `store.py`**。实际改动留到 **Runtime Kernel implementation phase**（属 Schema 定稿专项 + 兼容性验证后再动，列 §E）。

---

## Q4 — ExperienceSelector 生命周期（per-run instance / stateless service / policy runtime？）

### Q4.1 结论：**stateless service + per-run 输入/输出**（policy 可热插拔）

```
ExperienceSelector = stateless reasoning service
    - 实例：长生命周期、无运行间状态（可单例/可注入）
    - 每次调用：select(situation) → selected，纯输入→输出，per-run（v0.3 Q2）
    - 策略：SelectionStrategy 可插拔（policy runtime 的能力，但 Selector 本身不持运行态）
```

| 选项 | 评价 |
|---|---|
| per-run instance（每运行 new 一个） | ✗ 无必要：Selector 不需运行间状态；频繁构造浪费，且易诱导把状态塞进实例 |
| **stateless service**（✅ 采纳） | ✓ 无状态→天然并发安全→可复用→输出仅由 `situation` 决定（与 v0.3 Q2 per-run 一致：状态在输入 situation，不在 Selector） |
| policy runtime | ◐ 部分采纳：策略可换是 policy runtime 的特征，但实现为 **stateless service + 可注入 Strategy**，而非有状态运行时 |

### Q4.2 为何 stateless 与 v0.3「Intelligence Layer」不矛盾（采纳 Review 约束 6：Selector 不学习，Evolution 学习）

Review 强调一条关键澄清：**stateless ≠ 无状态智能**。Selector 是无状态的「推理服务」，但它依然智能——智能不来自记忆，来自推理逻辑。学习能力被明确划给 Evolution，**不**给 Selector：

```
ExperienceSelector（不学习）：           Experience Evolution（学习）：
    输入：RuntimeSituation                    输入：过去运行结果（评估后）
          Candidates                                 │
       │                                             ▼
       ▼  纯推理（无记忆）                          学习 / 沉淀
    输出：Selection                              │
                                                  ▼
                                            更新 Artifact（confidence/evaluation）
```

- **Intelligence ≠ stateful**：Selector 的「智能」体现在 **strategy 的推理逻辑**（similarity/confidence/applicability/regime…），而非保留跨运行记忆。
- **学习归 Evolution**：跨运行的「经验有效性学习」属于 **Evolution 侧**（更新 Artifact 的 confidence/evaluation），**不**由 Selector 自己记忆——否则 Selector 会变成隐藏的经验存储，违反「Memory 不拥有资产 / 资产归 Experience System」。
- **职责对偶**：Selector「读」演化后的资产做即时推理；Evolution「写」资产积累跨运行学习。一读一写，互不越界。

### Q4.3 归属与依赖

- 落 `services/experience-runtime`（v0.3 约束 6）。
- 输入 `RuntimeSituation`（v0.3 Q3.1 五 context），候选池经 `ArtifactReader`（内部 port），输出 `selected` 交 Projection。
- **本轮不实现**，仅定生命周期形态。

---

## Q5 — 与未来 AI Native 中国资本市场认知系统的关系

### Q5.1 结论：**Runtime Kernel = generic decision runtime**（采纳 Review 约束 7）

```
Runtime Kernel  =  generic decision runtime   （领域无关的决策运行内核）
市场认知        =  domain cognition provider   （作为可插拔领域能力接入，不内置）
```

Review 明确：**保持 Generic Decision Runtime，不要做成 Market Trading Runtime**。类比成熟基础设施分层：

```
       Python runtime              ←  Runtime Kernel       （通用基础设施，领域无关）
            ▲                              ▲
   Data Science package           China Capital Market Cognition  （领域能力，装在上面）

Runtime 是基础设施；市场认知是领域能力。
就像 Python runtime 不内置 pandas/numpy 一样，runtime-kernel 不内置股票/公告/行情。
```

> 这保证 ShanHai 的决策内核长期通用：未来既能承载「中国资本市场认知」，也能承载其它决策领域，而不被任何单一领域焊死。

### Q5.2 边界（防止 Kernel 被领域污染）

| 应是 | 不应是 |
|---|---|
| Kernel 装配通用 RuntimeContext（task/intent/experience/policy/constraint） | ✗ Kernel 内置「龙虎榜/连板情绪/Short Signal」等市场语义 |
| 市场认知经 `environment_context`（v0.3 Q3.1）作为**输入信号**注入 | ✗ Kernel 直接调用市场数据源 |
| Market Cognition 作为 **domain cognition provider** 实现为独立能力，受 **DEC-0004 gating**（现在不开发） | ✗ 现在就把市场认知做进 Kernel/Selector |

### Q5.3 接入形态（未来，留位不实现）

```
                       generic decision runtime
                              (Runtime Kernel)
                                    ▲
              ┌─────────────────────┼─────────────────────┐
       domain cognition       domain cognition       domain cognition
       provider: Market       provider: …            provider: …
       (DEC-0004 gating,      (未来)                 (未来)
        现在不接)
            │
        经 environment_context 注入 RuntimeSituation（输入信号，非内核内置）
```

> 战略含义：保持 Kernel 通用，市场认知作为「插件式领域提供方」。这让 ShanHai 既能成为「中国资本市场认知系统」，又不把决策内核焊死在单一领域 —— 与 DEC-0004（短线市场认知仅记未来方向、现在不开发）一致。

### Q5.4 新增设计：Domain Provider Boundary（采纳 Review 约束 8）

Review 新增一条关键边界澄清，回答「领域能力以何种身份接入 Kernel」：**Domain Provider 不是 Runtime Kernel 的 plugin，而是 Context Provider**。

```
❌ 错误模型（领域能力作为 Kernel 插件 → Kernel 被迫理解领域）：
   runtime-kernel
     └── plugin: market-cognition   ← Kernel 需要知道「股票/公告/行情」的存在与接口

✅ 正确模型（领域能力作为 Context Provider → Kernel 只见通用 context）：
   market-cognition-provider
       │  产出
       ▼
   market_state_context / risk_context / industry_context
       │  注入
       ▼
   RuntimeSituation  ──►  ExperienceSelector（推理）／ RuntimeContext（装配）
       （runtime-kernel 全程只看到 *_context 通用结构，不知道它来自股票/公告/行情）
```

| 维度 | plugin 模型（❌） | Context Provider 模型（✅） |
|---|---|---|
| Kernel 是否认识领域 | ✗ 需要知道 market 接口/语义 | ✓ 只见通用 `*_context`，零领域知识 |
| 耦合方向 | ✗ Kernel ↔ 领域双向耦合 | ✓ Provider → context 单向产出，Kernel 只消费 |
| 可替换性 | ✗ 换领域要改 Kernel | ✓ 换领域只换 provider，Kernel 不动 |
| 与 v0.3 Q3.1 一致性 | — | ✓ 注入点就是 RuntimeSituation 的 `environment_context`（market 子项受 DEC-0004 gating） |

> 落点：未来 `market-cognition-provider`（独立领域能力包）产出 `market_state_context / risk_context / industry_context`，作为**输入信号注入 RuntimeSituation**，而**不是**让 `runtime-kernel` 知道股票、公告、行情。本轮**只确立边界，不实现 provider**（DEC-0004 gating）。

---

## D. 当前完整架构收敛（采纳 Review §8，标注本轮工程落点）

```
Human Cognition
      │
      ▼
Context Foundation         （Meta / DEC-0002，单向只读经 ContextProjection，永不进 Runtime schema）
  Decision / Cognition / ContextEvent
      │
      ▼
Experience Evolution       （services/experience-evolution + experience-artifact，生产侧）
  Candidate → Promotion → ArtifactBuilder → Artifact
      │
      ▼
Experience Intelligence    （services/experience-runtime，消费侧，Q1/v0.3 约束 6）
  ArtifactReader（内部 port）→ ExperienceSelector（stateless reasoning, Q4）→ ExperienceProjection（per-run）
      │
      ▼
Runtime Kernel             （services/runtime-kernel，独立 package，Q1）
  create_runtime → assemble→ RuntimeContext（immutable）→ execute → collect → close（Q2）
      │
      ▼
  AgentContext → AgentRunner（既有 agent-runtime，不接管执行）
      │
      ▼
RuntimeEvent（= RunResult/RunStore, Q3）
      │
      ▼ （Evaluation only，禁止入 Selector）
ExperienceEvent
      │
      ▼
Experience Evolution（闭环回流，仅在 Artifact 处与消费侧交汇）
```

三条线（Context Foundation / Runtime Execution / Experience Evolution）+ 消费侧 Experience Intelligence 已闭环；唯一交汇点是 **Artifact**（稳定资产），运行事实不短路进消费。

---

## E. 待决项（明确延期，逐项再 Review）

| 待决项 | 依赖前置 | 倾向 |
|---|---|---|
| `services/runtime-kernel` 包骨架（仅结构，不含逻辑） | 本 v0.4 方向获批 | 独立包，依赖 agent-runtime + experience-runtime |
| `run_id` 生成点前移 + `RunStore.save_run(result, run_id=...)` 兼容扩展 | Schema 定稿 + 兼容验证 | 外部传入，默认不传仍内部 mint（向后兼容） |
| RuntimeContext / RuntimeSituation 字段定稿 | v0.3 Q1/Q3 草案 → 冻结 | 专项 schema review |
| `services/experience-runtime` 包（Selector/Projection 骨架） | RuntimeSituation 定稿后 | 消费侧新包（v0.3 约束 6） |
| ArtifactReader 接口形态（Commit 7 前置） | Selector 查询形态冻结后 | `find_by_context/find_applicable`，非 `list()` |
| `AgentRunner.run(input, runtime_context)` 接口扩展 | RuntimeContext 定稿 | 可选入参，默认 None=现行为 |
| RuntimeEvent 是否物化为离散事件流 | 出现 RunResult 粒度不够的需求 | 默认复用 RunStore，按需扩展 |
| domain cognition provider（市场认知） | 远期，DEC-0004 gating | 现在不做 |

---

## F. 非目标 / 约束（继续遵守，保持 Review Gate）

- **本阶段只设计、不编码**：不建 `runtime-kernel` / `experience-runtime` 包、不实现 Selector/Projection/RuntimeContext、不改 RunStore、不接 Memory、不解冻 Commit 7。
- 不引入 Vector / Graph / Retrieval / embedding / 市场 regime / 用户偏好建模 / Memory 持久化写入。
- 不破坏冻结不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）、身份原则（DEC-0005）、市场认知 gating（DEC-0004）、agent-runtime v0.2.0 契约。
- ADR 0018 维持 **MVP Contract Established**，**不 Finalize**。

---

## G. 下一步（v0.4 方向已获批 → 进入 v0.5 Contract Freeze）

v0.4 五问方向 + 8 条约束已获 Review 批准（见 §0.A）。Review 批准**进入 [Runtime Kernel v0.5 — Contract Freeze Review](runtime-kernel-v0.5-contract-freeze.md)**，仍 **Design Only**，目标是**冻结契约**（非写代码）：

1. **Q1** Runtime Kernel public contract（`create()` / `assemble()` / `execute()` / `close()`）。
2. **Q2** RuntimeContext v1 schema。
3. **Q3** RuntimeEvent schema。
4. **Q4** ExperienceSelector interface。
5. **Q5** Package dependency graph。

完成 v0.5 契约冻结后，**才考虑**（仍需逐项解冻批准）：

- `services/runtime-kernel` package skeleton；
- `RunStore` identity migration（run_id 前移）；
- ExperienceSelector MVP；
- RuntimeContext implementation。

ArtifactReader（Commit 7）仍冻结，待 Selector 查询形态在 v0.5 Q4 定稿。

> 当前完成状态：✅ Context Foundation Frozen｜✅ Conversation Ingestion｜✅ Experience Artifact Production Chain｜✅ RuntimeContext Direction Approved｜✅ **Runtime Kernel Architecture v0.4 Direction Approved（含 8 约束）**｜⏳ **Runtime Kernel v0.5 Contract Freeze Review**。

> v0.4 方向获批（含 8 约束），已**冻结进入 [v0.5 Contract Freeze](runtime-kernel-v0.5-contract-freeze.md)**，仍 Design Only。不编码、不建包、不改 RunStore/AgentRunner、不解冻 Commit 7。

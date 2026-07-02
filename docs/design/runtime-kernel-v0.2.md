# Runtime Kernel Design Review v0.2（设计稿，仅讨论，不编码）

> 状态：**✅ Direction Approved（v0.2 架构方向获批）→ 细化进入 [v0.3](runtime-context-api-v0.3.md)** — Review 确认三类 Event 分层、Experience Selection、RuntimeContext≠AgentContext、Memory=访问接口层、ADR0018 保持 MVP Contract Established。仍 Design Only，不进入 Commit 7 / ArtifactReader / RuntimeContext API。
> 状态（历史）：Principle Approved（v0.1）→ Detailing（v0.2）— 本文件在 v0.1 原则获批基础上补充三章细化设计，仍不写代码、不新增模块、不创建 Reader、不接 Agent/Memory。
> 阶段：Phase 1 — Agent Runtime / Runtime Kernel Design。
> 前置：[Runtime Kernel Design v0.1](runtime-kernel-v0.1.md) ✅ Principle Approved（Q1 定位 / Q2 Meta 分离 / Q3 Projection 方向 / Q4 Memory≠Experience / Q5 不发 ContextEvent 均已确认）。
> 本轮 Review 增量：① **Experience Selection** 中间概念；② **RuntimeEvent** 作为独立事件类型（修订 v0.1 §8）；③ **Memory = 访问接口层** 精确定位；④ 升级三线架构图。
> 关联：[ADR 0000](../架构决策记录/0000-项目元上下文架构.md)、[ADR 0012 Memory]、[ADR 0014 Experience]、[ADR 0018 Artifact](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0005](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

---

## 0. v0.1 → v0.2 变更摘要（保持设计诚实）

| 项 | v0.1 主张 | v0.2 修订 | 触发 |
|---|---|---|---|
| 运行事件 | Kernel 在运行边界**直接发 ExperienceEvent**，不造 RuntimeEvent | **Kernel 只发 RuntimeEvent**；ExperienceEvent 由评估/演化链**派生**，Runtime 不直写 Experience | Review §5：避免 Runtime↔Experience 强耦合 |
| Artifact 消费 | `Artifact → Projection → RuntimeContext` | 中间插入 **Experience Selection**：`Artifact → Reader(port) → Selector → Projection → RuntimeContext` | Review §3：核心问题是「选哪些」不是「怎么读」 |
| Memory 定位 | Memory 是访问门面（已述） | 强化为 **Runtime 查询接口层**（repo≠git command 类比） | Review §4 强批准 |

v0.1 其余原则（Q1/Q2/Q4 方向、身份原则、非目标）继续有效，不重复。

---

## A. RuntimeEvent Boundary（运行事件边界）

### A.1 三种 Event 的语义分层（关键澄清）

ShanHai 现在需要**三条不混用**的事件语义：

| 事件 | 语义 | 所属层 | 典型内容 | 现状 |
|---|---|---|---|---|
| **ContextEvent** | 系统**认知**变化 | Meta（DEC-0002） | 新决策规则形成 / 认知状态变化 | 已实现（`tools/context/schema.py`） |
| **RuntimeEvent** | 一次**运行**发生了什么 | Runtime | 用户请求 / Agent 执行 / Tool 调用 / 模型响应 / 最终结果 | **已隐式存在**（见 A.3） |
| **ExperienceEvent** | 一次运行产生了**可学习经验** | Experience | decision / outcome / lesson（事实链） | 已实现（`services/experience`） |

铁律链路（Review §5 确认）：

```
Runtime ─► RuntimeEvent ─(评估 Evaluation)─► ExperienceEvent ─(演化 Evolution)─► Artifact
```

**禁止** `Runtime ──► ExperienceEvent`（直写会让 Runtime 与 Experience 强耦合）。

### A.2 RuntimeEvent 是否存在？——**是，但不新造存储**

RuntimeEvent 作为**语义概念**确立。但落到工程，必须先看现状，避免重复造层。

### A.3 与既有代码的对账（RuntimeEvent ≈ 已有运行记录）

现状里「一次运行发生了什么」**已经被结构化捕获**：

- `services/agent-runtime`：`RunResult` + `Step`（think/act/observe，含 `tool` / `tool_args` / `tool_result`）—— 这正是 RuntimeEvent 的内容载体。
- `AgentRunner._persist → RunStore`（sqlite/postgres）—— 这正是 RuntimeEvent 的事实日志（best-effort 落库）。
- 既有完整管线 `Run → RunStore → Evaluation(services/evaluation) → Feedback → ExperienceEvent`，**已经实现了 A.1 的铁律链路**。

> 结论：RuntimeEvent **不是新东西**，它就是「运行执行记录」的语义命名。`RunResult/Step` 是其形态，`RunStore` 是其日志。

### A.4 是否需要 Event Store？——**复用 RunStore，不新建**

| 方案 | 评价 |
|---|---|
| 新建 `RuntimeEventStore` | ✗ 与 `RunStore` 职责重叠，制造平行存储与同步负担 |
| **复用 `RunStore`（RunResult/Step）作为 RuntimeEvent 日志** | ✓ **推荐**：零新存储，沿用已稳定的 ADR 0008/0009 落库 |
| 仅当需要「更细粒度离散事件流」（如把 user-request / tool-call / model-response 拆成独立事件）时再扩展 | 属 `Step` 捕获的**扩展**，仍在 RunStore 域内，按需再 Review |

### A.5 一个需要显式记录的语义缝（decision 直录路径）

现状 `ExperienceRecorder: RunRecord → type=decision` 是从运行记录**较直接**地写入 ExperienceEvent。按 A.1 的严格分层，这属于「事实锚点录入」而非「可学习经验」：

- `decision` / `outcome` = **事实锚点**（支撑 decision→outcome→lesson 事实链）。
- `lesson` = 真正「学到的经验」（经 Evaluation/Feedback 产出）。

**v0.2 设计取向**：Runtime Kernel **只**负责发 RuntimeEvent（写 RunStore）；把「哪些运行事实晋升为 ExperienceEvent」交给既有 **experience ingest / evaluation** 链，Kernel 不直接调用 `ExperienceStore.append`。是否将 `decision` 录入也统一收到「评估后」的边界之后，列为待决项（见 §E）。

### A.6 Runtime Kernel 的事件边界职责（收敛）

```
Run Boundary（Runtime Kernel 持有）：
  进入：装配 RuntimeContext（见 C）
  退出：产出 RunResult → 经 RunStore 记为 RuntimeEvent（复用既有 _persist）
  不做：不写 ExperienceEvent、不写 ContextEvent、不跑评估（评估属 services/evaluation）
```

---

## B. Experience Selection Design（经验选择设计）

### B.1 为什么 Reader 不是核心（Review §3 的洞察）

真正的问题不是「怎么读 Artifact」，而是「**哪些 Artifact 对当前运行有价值**」。

举例（未来股票分析）：当前任务「分析新能源板块」，资产库有 A 新能源历史行情模式 / B 消费行业策略 / C 宏观周期经验 / D 用户交易习惯。**不能** `reader.get_all()` 全塞给 Agent——必须按相关性、置信度、适用性**策展**。所以：

> Reader 只是基础读能力；**Selection Policy 才是核心**。

### B.2 四职责分离（消费侧链路）

```
ExperienceArtifact（资产，experience-artifact 拥有）
        │  read（机械读取）
        ▼
ArtifactReader（内部 read port，非 Runtime 直接 API）
        │  select（策略：选哪些、排序、截断）
        ▼
ExperienceSelector（Selection Policy，可插拔）
        │  shape（投影：裁成 Runtime 可消费的只读视图）
        ▼
ExperienceProjection
        │
        ▼
RuntimeContext.selected_experience（见 C）
```

每一层职责单一：

| 组件 | 职责 | 明确不做 |
|---|---|---|
| ArtifactReader | 按结构化条件读取 Artifact（**内部 port**） | 不判断相关性、不排序业务语义、不面向 Runtime |
| ExperienceSelector | **相关性/价值判定**（context 匹配 / confidence 阈值 / applicability / recency），策略可换 | 不读存储细节、不裁剪呈现格式 |
| ExperienceProjection | 把选中的 Artifact **投影**为只读 ExperienceContext（引用/摘要视图，非原始存储对象） | 不做选择、不持久化、不回写 Artifact |

### B.3 Selector 是否独立模块？

- **是独立职责**，**模块归属待定**（§E 待决）。倾向：消费侧新模块（如未来 `services/experience-projection`），**不放进 `experience-artifact`**——后者已被 Review 冻结为 *storage boundary*（ADR 0018），加入 Selection 会让它退化为 Intelligence Service。
- Selection Policy 用**策略模式**：MVP 可先有一个确定性 Selector（按 context 关键字 + min_confidence + limit），未来可换 ranking / embedding（embedding 属更后期，**现在不引入**）。

### B.4 ArtifactReader 的最终定位（回答「是否只是内部 port」）

- **是**：ArtifactReader = ExperienceSelector 面向存储的**内部只读端口**，不是给 Runtime/Agent 的 API。
- 其接口由 Selector 的**选择需求反向决定**（如 `find_by_context(...)` / `find_applicable(type, min_confidence, limit)`），**不是**裸 `list()` / `get_all()`。
- **因此 Commit 7（ArtifactReader）现在仍不做**——必须等 Selector 的查询形态冻结后，才能定义 Reader 接口（否则先验锁死成通用列举）。

### B.5 Projection 输入 / 输出契约（草案）

```
输入  RuntimeSituation（当前情境）：task / domain / agent / goal
        │
        ▼  ExperienceSelector.select(situation) → 选中 + 排序的 Artifact 引用集
        ▼  ExperienceProjection.project(selected) →
输出  ExperienceContext（只读）：
        - items: 经投影的经验视图（rule / expected_outcome / confidence / provenance 的只读裁剪）
        - 不含 Artifact 内部存储结构、不含可写句柄
```

---

## C. RuntimeContext Contract（运行上下文契约）

### C.1 与既有 AgentContext 的区分（必须澄清，否则冲突）

代码里**已有** `AgentContext`（`services/agent-runtime/context.py`）：它是**执行期能力句柄**——持有 `router`（模型）、`tool_registry`（工具）、`memory`、`observations`，由 `AgentRunner` 在运行中创建。

`RuntimeContext` 是**不同的东西**：它是 Runtime Kernel 在**运行前装配**的**情境输入数据**（task + 策展好的经验 + 策略），只读、不含能力句柄。

| | RuntimeContext（本设计新增概念） | AgentContext（已存在） |
|---|---|---|
| 性质 | 装配好的**输入数据** | 执行期**能力句柄** |
| 谁创建 | Runtime Kernel（运行前） | AgentRunner（运行中，`new_context`） |
| 含模型/工具句柄 | ❌ 否 | ✅ 是（complete / use_tool） |
| 含经验投影 | ✅ 是（selected_experience） | ❌ 否 |
| 可写 | ❌ 只读 | 部分（observations 累计） |

二者**协作不替代**：Kernel 装配 `RuntimeContext` → 作为情境输入交给运行 → `AgentRunner` 仍按既有方式建 `AgentContext` 提供能力 → Agent 同时拿到「情境数据(RuntimeContext)」与「执行能力(AgentContext)」。**不改 agent-runtime 既有契约。**

### C.2 RuntimeContext 字段（设计草案，非代码）

```python
# 仅为契约示意，本阶段不实现
RuntimeContext(
    run_id,               # 身份（DEC-0005：稳定标识符，非可变信息）
    task,                 # 本次运行的任务/目标
    user_context,         # 用户/外部触发带入的情境（非 Meta cognition）
    selected_experience,  # ExperienceContext：经 Selection+Projection 的只读经验视图（见 B）
    policies,             # 运行策略（如选择阈值、步数上限等运行级约束的投影）
    constraints,          # 运行约束（只读；若未来来自 Meta，必须经单向 ContextProjection，见 v0.1 §5）
)
```

### C.3 边界铁律（RuntimeContext 必须遵守）

- **不含 Meta 数据**：`user_context` / `constraints` 不得直接塞 `cognition.json` / `DecisionRecord`（DEC-0002）。若未来确需治理约束到达运行期，只能经**单向只读 ContextProjection**（Meta→Policy），永不共享 schema。
- **不含原始 Artifact 存储对象**：`selected_experience` 只放**投影后的只读视图**，Runtime 不触达 Artifact 内部结构（B.2）。
- **不含模型/工具句柄**：那是 `AgentContext` 的职责（C.1）。
- **只读 + 身份合规**：`run_id` 为身份；时间/状态等可变信息入 metadata（DEC-0005），不编码进标识符。

---

## D. 升级后的三线架构图（采纳 Review §6）

```
                 User / External Trigger
                          │
                          ▼
                   Runtime Kernel
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
 Context Assembly   Execution Boundary   RuntimeEvent
        │                 │                 │ (→ RunStore，复用既有 _persist)
        ▼                 ▼                 │
 Experience Selection     │                 │
        │                 │                 │
        ▼                 ▼                 │
 Experience Projection    │                 │
        │                 ▼                 │
        ▼            Agent Runtime          │
 Runtime Context  ── (Agent Loop / Tool / Model：既有，不接管) ──┐
                          │                                      │
                          ▼                                      │
                       Outcome ◄─────────────────────────────────┘
                          │
            (Evaluation services/evaluation)
                          │
                          ▼
                 Experience System
              ExperienceEvent
                     │
                  Candidate
                     │
                PromotionGate
                     │
               ArtifactBuilder
                     │
              ExperienceArtifact ──(读回，经 Selection/Projection 回到顶部 Context Assembly)
```

三条线被显式分开（Review §6 目标）：

1. **Context Foundation**（Meta，DEC-0002，不进 Runtime）。
2. **Runtime Execution**（Runtime Kernel + Agent Runtime + RuntimeEvent/RunStore）。
3. **Experience Evolution**（ExperienceEvent → Candidate → Promotion → Artifact，回流经 Selection/Projection）。

Memory 的位置（Review §4）：**Runtime 查询接口层**，不是数据库——

```
Runtime ─► Memory Interface ─┬─ Conversation Memory
                             └─ Experience Memory ─► Experience Projection ─► ExperienceArtifact
（Memory = 访问方式；Artifact = 资产。类比 git command ≠ repo）
```

---

## E. 待决项（明确延期，逐项再 Review）

| 待决项 | 依赖前置 | 倾向 |
|---|---|---|
| ExperienceSelector 模块归属（新 `experience-projection` 包？） | Runtime Context API 专项设计后 | 消费侧新模块，不污染 `experience-artifact` |
| ArtifactReader 接口形态（投影内部 port） | Selector 查询形态冻结后 | `find_by_context/find_applicable`，非 `list()`；恢复 Commit 7 的前置 |
| RuntimeContext / RuntimeSituation 字段定稿 | D-A 方案 2 + Q3 方案 C 已确认 | C.2 草案细化为专项 |
| `decision` 录入是否统一收到评估后边界（A.5 语义缝） | Evaluation 边界确认 | 倾向：Kernel 只发 RuntimeEvent，decision 晋升交 ingest |
| RuntimeEvent 是否需要细粒度离散事件流 | 出现 RunResult 粒度不够的需求 | 默认复用 RunStore，按需再扩展 |
| Memory experience-scope 升级为投影视图 | 投影定型后 | 复用既有门面，不另造路径 |

---

## F. 非目标 / 约束（继续遵守）

- **本阶段只设计、不编码**：不新增 Runtime/Selector/Projection 模块、不创建 ArtifactReader、不接 Agent/Memory。
- 不引入 Vector / Graph / Retrieval / embedding / Memory 持久化写入 / Prompt·Skill 自动生成。
- 不破坏冻结不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）、身份原则（DEC-0005）。
- ADR 0018 调整为 **MVP Contract Established（生产侧契约已立）**，但**不 Finalize**（消费侧 Selection/Projection/Runtime 集成未闭环）。

---

## G. 下一步（待批准，不自行执行）

1. 确认 v0.2 三章方向（A RuntimeEvent 复用 RunStore / B Selection 四职责分离 / C RuntimeContext≠AgentContext）。
2. 批准后进入 **Runtime Context API 专项设计**（定稿 `RuntimeContext` / `RuntimeSituation` / `Selector.select` / `Projection.project` 形态）。
3. 待 Selector 查询形态冻结，再恢复并重定义 **Commit 7 = ArtifactReader（投影内部 port）**。

> 当前停在 **Runtime Kernel Design Review（v0.2）**，Design Only，等待方向批准。不编码、不恢复 Commit 7。

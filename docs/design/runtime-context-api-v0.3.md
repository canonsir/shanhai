# Runtime Context API Design Review v0.3（设计稿，仅讨论，不编码）

> 状态：**✅ Direction Approved（v0.3 方向获批）→ 细化进入 [v0.4](runtime-kernel-architecture-v0.4.md)** — Review 批准四问方向，并补充 7 条架构级约束（见 §0.A），已折入本文。仍 Design Only，不实现 RuntimeContext / ExperienceSelector / ArtifactReader / Memory integration。
> 状态（历史）：Design Review（v0.3）— 回答 Q1 schema / Q2 per-run / Q3 Selector / Q4 插入位置。
> 阶段：Phase 1 — Agent Runtime / Runtime Context API Design。
> 前置：[Runtime Kernel Design v0.2](runtime-kernel-v0.2.md) ✅ Direction Approved（三类 Event 分层 / Experience Selection / RuntimeContext≠AgentContext / Memory=访问接口层 / ADR0018 保持 MVP Contract Established）。
> 本轮聚焦四问：**Q1** RuntimeContext schema｜**Q2** ExperienceProjection 生命周期（per-run vs cached）｜**Q3** Selector 输入来源｜**Q4** Runtime Kernel 插入位置。
> 三条新增 Review 约束（本轮必须落实）：① **ExperienceSelector 是 Intelligence Layer，不是普通 filter**；② **方向为 `RuntimeContext → AgentContext`**（认知装配在前，执行环境在后）；③ **Memory = Access Interface，不拥有资产**。
> 关联：[ADR 0000](../架构决策记录/0000-项目元上下文架构.md)、[ADR 0012 Memory]、[ADR 0014 Experience]、[ADR 0018 Artifact](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0005](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

---

## 0. 本轮要确立什么（与现状对账）

v0.3 把 v0.2 的「概念边界」推进到「契约形态」，但仍**不写代码**。本轮在动笔前盘点了现有 agent-runtime 代码，关键事实：

- `AgentContext`（[context.py](../../services/agent-runtime/shanhai_agent_runtime/context.py)）由 `BaseAgent.new_context(input)` 在 `AgentRunner.run` 内部创建，持 `router / tool_registry / memory / granted_tools / input` + 累计态 `steps / iteration / observations`。**它是执行期能力句柄**。
- `AgentRunner.run(input)`（[runner.py](../../services/agent-runtime/shanhai_agent_runtime/runner.py)）当前**入参仅 `input`**，无「装配好的情境」入口。
- `RunResult / Step`（[types.py](../../services/agent-runtime/shanhai_agent_runtime/types.py)）= RuntimeEvent 的内容载体（v0.2 §A 已对账）。

> 结论：RuntimeContext 是 **AgentRunner 之前**的新装配物，**不改 AgentContext 字段**，而是成为 `AgentRunner.run` 的新情境入口（见 Q4）。

---

## 0.A Review 补充约束（v0.3 获批附带，已折入下文）

Review 批准方向的同时补充 7 条架构级约束，逐条登记并指向落点：

| # | 约束 | 落点 |
|---|---|---|
| 1 | RuntimeContext 字段命名统一为 `*_context` 后缀；**冻结生命周期与边界，不冻结完整字段列表**（字段来自 Task Understanding + Experience Selection + Policy System 三个系统，Policy System 尚不存在） | Q1.2 改为 `*_context` 命名 + 标注「字段不冻结」 |
| 2 | **RuntimeContext 必须 immutable**：`Kernel create → read-only → AgentContext`，禁止 `Agent modify RuntimeContext`（否则退化为共享状态容器） | Q1.3 强化 immutability 铁律 |
| 3 | **Experience Selection ≠ Retrieval**：Selector 是 reasoning component over experience candidates，不是 data retrieval component | Q3.2 增加该判断 |
| 4 | **RuntimeSituation 拆为 5 个 context**：task / user / environment / capability / constraint；market_context 保持 DEC-0004 gating | Q3.1 重构为 5-context |
| 5 | **Memory 正式命名 Memory Access Interface / Boundary**（不再叫 Memory Layer）；Memory 不保存 Artifact/ContextDecision/KnowledgeAsset，只提供 query/retrieve/lookup | Q4.3 命名定稿 |
| 6 | **Projection 是 Runtime 专属对象**：Selection/Projection 落 `experience-runtime`，**禁止进入 `experience-artifact` 包**（否则 Artifact 知道消费方式，违反生产/消费分离） | Q3.3 模块归属定为 `experience-runtime` |
| 7 | **RuntimeEvent 不参与经验选择**：链路只能 `RuntimeEvent → Evaluation → ExperienceEvent → Artifact`，禁止 `RuntimeEvent → Selector`（否则运行过程污染经验消费） | Q4.4 新增该铁律 |

---

## Q1 — RuntimeContext 的 Schema（需要哪些字段？）

### Q1.1 定位：execution initialization snapshot（采纳 Review §3）

RuntimeContext = **运行开始瞬间的认知装配快照**，只读、不可变、不含能力句柄。它回答的是「这次运行**带着什么认知**开始」，而非「这次运行**能调用什么**」（后者是 AgentContext）。

| | RuntimeContext（v0.3 定稿方向） | AgentContext（已存在） |
|---|---|---|
| 性质 | 执行前**认知装配快照**（initialization snapshot） | 执行期**能力环境**（dynamic execution env） |
| 时机 | 运行前（Kernel 装配） | 运行中（AgentRunner 创建） |
| 内容 | task / intent / experience / policy / constraint context | router / tool_registry / memory / steps / observations |
| 可变性 | ❌ 只读不可变 | ✅ 累计可变（steps/observations） |
| 方向 | **上游**：`RuntimeContext → AgentContext` | **下游**：消费 RuntimeContext 装配自身 |

### Q1.2 字段草案（契约示意，非代码；命名采纳 Review 约束 1）

> **冻结的是生命周期与边界，不是完整字段列表**。字段来自三个未来系统 `Task Understanding + Experience Selection + Policy System`，其中 **Policy System 尚不存在**，故字段保持可扩展，本轮不锁死。

```python
# 仅契约示意，本阶段不实现；字段不冻结（见上）
RuntimeContext(
    run_id,                # 身份（DEC-0005：稳定不可变标识符，时间/状态入 metadata）
    task_context,          # 任务理解（做什么）           ← Task Understanding
    intent_context,        # 用户/外部意图（为何做、期望什么）← Task Understanding
    experience_context,    # 经 Selector→Projection 的只读经验视图（Q2/Q3）← Experience Selection
    policy_context,        # 运行策略（步数上限/选择阈值/超时投影）← Policy System（未来）
    constraint_context,    # 运行约束（只读；源自 Meta 必经单向 ContextProjection，见 v0.2 §C.3）
    metadata,              # 可变信息（created_at / status 等，非身份）
)
```

字段语义边界：

| 字段 | 含义 | 明确不放 |
|---|---|---|
| `task_context` | 结构化的「做什么」 | 不放工具句柄、不放 prompt 模板 |
| `intent_context` | 「为何做 / 期望什么」，喂给 Selector 做相关性判定（Q3） | 不放原始对话流（那属 Conversation Memory） |
| `experience_context` | **已策展**的只读经验视图（rule/expected_outcome/confidence/provenance 裁剪） | 不放 Artifact 原始存储对象、不放可写句柄 |
| `constraint_context` | 运行边界（如禁用某工具、风险红线） | 不直接塞 `cognition.json` / `DecisionRecord`（DEC-0002） |
| `policy_context` | 运行级参数（max_steps、selection 阈值等） | 不放业务决策逻辑（那是 Agent/Selector 的事） |
| `metadata` | 时间/状态等可变信息 | 不放身份（身份归 run_id，DEC-0005） |

### Q1.3 边界铁律（继承 v0.2 §C.3，强化；采纳 Review 约束 2 immutability）

- **immutable（强制）**：`Kernel create → RuntimeContext(read-only) → AgentContext`。**禁止 `Agent modify RuntimeContext`**——否则 RuntimeContext 会退化成共享状态容器。运行中产生的状态进 AgentContext（steps/observations），绝不回写 RuntimeContext。
- **不含 Meta 数据**：constraint/intent 不得直接承载 Meta cognition；治理约束到达运行期只能经**单向只读 ContextProjection**（Meta→Policy），永不共享 schema。
- **不含资产原件**：experience_context 只放投影视图（Memory 不拥有资产，Q4.3）。
- **身份合规**：`run_id` 为身份；`created_at`/status 等可变信息入 `metadata`（DEC-0005）。

---

## Q2 — ExperienceProjection 的生命周期（per-run vs cached？）

### Q2.1 结论：**per-run 为默认契约，cache 仅作内部读优化**

```
默认：ExperienceProjection = per-run（每次运行重新策展投影）
例外：仅 ArtifactReader 这一「读原语」内部可缓存（read cache），
      但 Selection 结果与 Projection 视图本身不缓存为跨运行共享状态。
```

理由：

| 维度 | per-run（采纳） | cached context（不作默认） |
|---|---|---|
| 正确性 | ✅ 每次按当前 task/intent/market 重新选择，经验始终贴合此刻情境 | ✗ 缓存的「选中经验」会对新任务失配（新能源任务复用了消费行业经验） |
| 与 Selector 定位一致 | ✅ Selector 是 Intelligence Layer（Q3），其输出本质是「针对此情境的判断」，不可跨情境复用 | ✗ 把智能判断退化为静态快照 |
| 资产新鲜度 | ✅ 新晋升的 Artifact 立即可被下次运行选中 | ✗ 缓存导致经验闭环延迟 |
| 身份/可观测 | ✅ Projection 绑定 `run_id`，可追溯「这次用了哪些经验」 | ✗ 跨运行共享难归因 |
| 性能 | 读放大 → 由 Reader 层 read cache 吸收 | — |

### Q2.2 缓存边界（区分两类 cache，避免混淆）

```
✅ 允许：ArtifactReader 内部 read cache（机械读，缓存「资产数据」本身，跨运行可共享，因资产不可变）
❌ 禁止：把「Selection 结果 / Projection 视图」缓存为跨运行复用的 RuntimeContext
```

因 ExperienceArtifact 是不可变资产（ADR0018 D3 confidence 快照），**资产数据**可安全缓存；但**「选哪些」是情境函数**，必须每运行重算。

### Q2.3 生命周期时序

```
run 开始
  │
  ├─ Selector.select(situation)      ← 针对本 run 的情境，per-run
  │      （内部 ArtifactReader 读资产，可命中 read cache）
  │
  ├─ Projection.project(selected)    ← 针对本 run 投影，per-run
  │
  ├─ 装入 RuntimeContext.selected_experience（绑定 run_id，只读）
  │
run 结束 → Projection 视图随 RuntimeContext 生命周期结束（不留存为共享态）
```

---

## Q3 — Selector 的输入来自哪里？

### Q3.1 输入聚合为 `RuntimeSituation`（情境对象；拆 5 个 context，采纳 Review 约束 4）

Selector 的输入不是单一 task，而是一个**情境聚合**，拆为 5 个 context：

```python
# 契约示意，本阶段不实现
RuntimeSituation(
    task_context,        # [现可得] 当前任务理解（来自 RuntimeContext.task_context）
    user_context,        # [现可得] 用户意图/偏好情境（来自 RuntimeContext.intent_context）
    environment_context, # [未来]   运行环境/市场状态（market_context 子项受 DEC-0004 gating，现在不接）
    capability_context,  # [现可得] Agent 能力（授权工具集 granted_tools，已存在）
    constraint_context,  # [现可得] 运行约束（来自 RuntimeContext.constraint_context）
)
```

关键澄清（避免把候选池当输入）：

| context | 角色 | 现状 |
|---|---|---|
| task_context | 输入信号（做什么） | 现可得（RuntimeContext） |
| user_context | 输入信号（为谁/偏好） | 现可得（RuntimeContext） |
| capability_context | 输入信号（能力相关性：选 Agent 能执行的经验） | 现可得（granted_tools） |
| environment_context | 输入信号（环境/市场） | **未来**，其 market_context 子项受 DEC-0004 gating，现在不接 |
| constraint_context | 输入信号（边界/红线） | 现可得（RuntimeContext） |
| Historical Experience | **候选池**（不是输入，是被筛选对象） | 经 ArtifactReader 提供 |

> 即：`Selector.select(situation) over reader.candidates → selected`。Situation 是「判断依据」，Historical Experience 是「判断对象」，二者角色不同。

### Q3.2 ExperienceSelector 是 Intelligence Layer，不是 filter（采纳 Review §2 强约束）

这是本轮**最重要的设计判断**。Selector 不能被实现成 `[a for a in artifacts if a.context == task]`。

```
普通 filter（❌ 禁止提前简化为此）：
    artifacts.filter(context == task)

Intelligence Layer（✅ 目标形态，可演进维度）：
    score(artifact | situation) = f(
        similarity,           # 任务/意图与经验的语义相似度
        confidence,           # Artifact 晋升置信度快照
        applicability,        # 适用条件是否满足当前 situation
        temporal_relevance,   # 时效（近因/市场周期）
        user_preference,      # 用户偏好（未来）
        market_regime,        # 市场状态（未来，DEC-0004 守门）
        strategy_context,     # 策略上下文（未来）
    ) → rank → select top-k
```

设计要求：

- **策略可插拔（Strategy Pattern）**：`ExperienceSelector` 是接口，背后是可替换的 SelectionStrategy。
- **MVP 不等于 filter**：MVP 即便只实现少数维度（如 context 匹配 + min_confidence + 排序 + top-k），其**结构**必须是「打分 + 排序 + 截断」的可扩展形态，而非布尔过滤——为未来融合 similarity/regime/preference 留位。
- **明确不提前引入**：embedding / 向量检索 / 市场 regime / 用户偏好建模本轮**不做**，但接口形态必须容纳它们（不锁死成 filter）。

#### Q3.2.1 Experience Selection ≠ Retrieval（采纳 Review 约束 3，关键判断）

> **ExperienceSelector is a reasoning component over experience candidates, not a data retrieval component.**

许多系统会把二者混淆。区别：

```
Retrieval（❌ 不是 ShanHai Selector）：        Experience Selection（✅ ShanHai）：
    query                                          RuntimeSituation
      │                                                  │
   vector search                                   ExperienceSelector（reasoning）
      │                                                  │
   top-k                                           Selected Experience
```

Retrieval 只看「query 与文档的相似度」；ShanHai Selector 必须**推理**：当前任务 / 当前阶段 / 当前风险 / 当前环境 / **历史经验有效性**。因此 Selector 未来可融合 `similarity model + rule policy + market regime + confidence model`，而 Retrieval（vector search）至多只是其中**一个候选打分子项**，不是 Selector 本身。

### Q3.3 模块归属：`experience-runtime`（采纳 Review 约束 6，生产/消费分离）

Selection + Projection 落**消费侧新模块 `services/experience-runtime`**，**禁止进入 `experience-artifact` 包**：

```
experience-artifact   负责：Artifact schema / Artifact lifecycle           （生产侧）
experience-runtime    负责：Selection / Projection / Runtime adaptation     （消费侧）
```

理由：若 Projection 进入 `experience-artifact`，则 **Artifact 会知道自己的消费方式**，违反生产/消费分离（Artifact 是被消费的资产，不应耦合「谁、如何消费它」）。`experience-artifact` 已被 ADR0018 冻结为 storage boundary，保持纯净。

---

## Q4 — Runtime Kernel 的插入位置（最终确认）

### Q4.1 确认链路（采纳 Review §下一阶段）

```
User Request
    │
    ▼
Runtime Kernel ──────────────────┐ Context Assembly + Run Boundary（v0.2 §A.6）
    │                            │
    ▼                            │
Experience Selection             │  Selector.select(situation)  [per-run, Q2]
    │                            │
    ▼                            │
Experience Projection            │  Projection.project(selected)
    │                            │
    ▼                            │
RuntimeContext  ◄────────────────┘ 装配完成、只读冻结（Q1）
    │
    ▼
AgentRunner.run(input, runtime_context)   ← 新情境入口（见 Q4.2）
    │
    ▼
AgentContext（由 new_context 创建，消费 RuntimeContext）
    │
    ▼
Execution（think → act → observe，既有，不接管）
    │
    ▼
RunResult → RunStore（= RuntimeEvent，v0.2 §A）
    │
    ▼ （评估 / 演化，既有链路）
ExperienceEvent → Candidate → Promotion → Artifact （回流，供下次 Selection）
```

### Q4.2 与既有 AgentRunner 的接合（方向 `RuntimeContext → AgentContext`，采纳 Review §3）

现状：`AgentRunner.run(input)` → `agent.new_context(input)` → `AgentContext`。

v0.3 设计取向（**不在本轮实现**，仅定方向）：

```
RuntimeContext（Kernel 装配，认知在前）
        │  作为情境入参传入
        ▼
AgentRunner.run(input, runtime_context=...)      # 新增可选情境入口，向后兼容（默认 None=现行为）
        │
        ▼
new_context(input, runtime_context)              # AgentContext 读取 RuntimeContext 装配自身
        │
        ▼
AgentContext（执行环境，认知在后）
```

铁律：

- **方向单向**：`RuntimeContext → AgentContext`，**禁止反向**（AgentContext 不得产出/回写 RuntimeContext）。
- **向后兼容**：`runtime_context` 为可选；不传时 AgentRunner 行为与现状完全一致（不破坏 v0.2.0 冻结契约）。
- **不接管执行**：Kernel 只到「装配 + 交付 RuntimeContext」为止；think/act/observe 仍归 Agent Runtime（v0.2 §A.6）。

### Q4.3 Memory 的位置（采纳 Review 约束 5：Memory Access Interface，不拥有资产）

```
Runtime ─► Memory Access Interface（访问边界，不是资产库）
                 ├─ Runtime Memory Access  → 运行态读写（进程内）
                 ├─ Knowledge Access        → 只读委派 Knowledge System（资产归 Knowledge）
                 └─ Experience Access        → 只读委派 Experience System（资产归 Experience）

Memory 只提供能力：query() / retrieve() / lookup()
Memory 不保存：ExperienceArtifact / ContextDecision / KnowledgeAsset

资产所有权（Memory 不拥有）：
    Knowledge   → Knowledge System
    Experience  → Experience System
    Context     → Meta Context（.shanhai-meta，不进 Runtime）
```

命名定稿：系统级**正式弃用 "Memory Layer"**，统一称 **Memory Access Interface / Memory Access Boundary**。现 `services/memory` 的 MemoryService 已是「按 scope 路由 + 只读 scope 拒写」的访问门面，与此定位一致，**无需改代码**，仅校准语义命名，待 ADR 0012 alignment 时统一回填。

### Q4.4 RuntimeEvent 不参与经验选择（采纳 Review 约束 7）

RuntimeEvent 是「运行过程事实」，**不得直接进入经验消费侧**：

```
✅ 唯一允许：RuntimeEvent → Evaluation → ExperienceEvent → Artifact
❌ 禁止：     RuntimeEvent → Selector
```

理由：若 RuntimeEvent 直供 Selector，则**运行过程会污染经验消费**（未经评估/演化的原始运行事实被当作可选经验）。运行事实必须先经 Evaluation 筛选、Evolution 沉淀为 Artifact，才能回流到 Selection。生产线（RuntimeEvent→…→Artifact）与消费线（Artifact→Reader→Selector→Projection）只在 **Artifact** 这一稳定资产处交汇，不在运行事实处短路。

---

## D. 三条线最终视图（与 v0.2 §D 一致，标注本轮新增物的落点）

```
1. Context Foundation（Meta，DEC-0002，单向只读经 ContextProjection，永不进 Runtime schema）
        ╎（仅 policy/constraints 投影，下游不可逆）
2. Runtime Execution
        User Request → Runtime Kernel ─┬─ Experience Selection（per-run, Intelligence Layer）
                                       ├─ Experience Projection（per-run 只读视图）
                                       └─ RuntimeContext（只读快照）→ AgentRunner → AgentContext → Execution
                                            → RunResult/RunStore（RuntimeEvent）
3. Experience Evolution
        RuntimeEvent →(评估)→ ExperienceEvent →(演化)→ Candidate → Promotion → Artifact
                                                                                    ╎
                                            （回流）Artifact → Reader → Selector → Projection → 回到 Runtime
```

---

## E. 待决项（明确延期，逐项再 Review）

| 待决项 | 依赖前置 | 倾向 |
|---|---|---|
| RuntimeContext / RuntimeSituation 字段**定稿**（从 Q1/Q3 草案 → 契约冻结） | 本 v0.3 方向获批 | 专项 schema review |
| SelectionStrategy 的 MVP 维度集（首版打分用哪几项） | RuntimeSituation 定稿后 | context 匹配 + min_confidence + rank + top-k（结构为打分非 filter） |
| Selector/Projection 模块归属 | 已定：`services/experience-runtime`（约束 6） | 消费侧新包，禁止进 experience-artifact |
| ArtifactReader 接口形态（read 原语 / read cache 边界） | Selector 查询形态冻结后 | `find_by_context/find_applicable`，非 `list()`；恢复 Commit 7 前置 |
| `AgentRunner.run(input, runtime_context)` 接口扩展 | RuntimeContext 定稿 + 兼容性验证 | 可选入参，默认 None=现行为 |
| Memory 语义命名校准（Layer→Interface） | ADR 0012 alignment 统一回填 | 仅命名，不改行为 |
| Market Context 接入 Situation | 远期，受 DEC-0004 守门 | 现在不做 |

---

## F. 非目标 / 约束（继续遵守，保持 Review Gate）

- **本阶段只设计、不编码**：不进入 ArtifactReader / ExperienceProjection code / RuntimeContext implementation / Memory integration（Review 明确清单）。
- 不引入 Vector / Graph / Retrieval / embedding / 市场 regime / 用户偏好建模 / Memory 持久化写入。
- 不破坏冻结不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）、身份原则（DEC-0005）、agent-runtime v0.2.0 契约。
- ADR 0018 维持 **MVP Contract Established**（生产链成立、消费链未闭环），**不 Finalize**。

---

## G. 下一步（v0.3 方向已获批 → 进入 v0.4）

v0.3 四问方向 ✅ 获批，7 条补充约束已折入本文。下一阶段进入 **[Runtime Kernel Architecture v0.4 Review](runtime-kernel-architecture-v0.4.md)**（仍 Design Only），重点不是 API 而是 Kernel 本体的工程形态与生命周期：
1. Runtime Kernel 是否独立 service/package（A: agent-runtime 内子模块 vs B: 独立 `runtime-kernel`）。
2. Runtime Kernel 生命周期状态机（create → assemble → execute → collect → close）。
3. RuntimeEvent Contract（schema / producer / consumer / persistence boundary）。
4. ExperienceSelector 生命周期（per-run instance / stateless service / policy runtime）。
5. Runtime Kernel 与 AI Native 资本市场认知系统的关系（generic decision runtime vs market cognition assembly）。

> 战略备注（采纳 Review 观察）：ShanHai 已从「Prompt→LLM→Tool」传统 Agent 形态，演进为「Human Cognition → Context Foundation → Experience Evolution → Runtime Cognition Assembly → Agent Execution → Experience Accumulation」的**决策智能 AI Native 形态**。RuntimeContext 与 ExperienceSelector 是其架构稳定性的两个关键支点——故继续坚持 Design Only，先定契约、不急落码。

> 当前停在 **Runtime Kernel Architecture v0.4 Review**，Design Only。不编码、不解冻 Commit 7。

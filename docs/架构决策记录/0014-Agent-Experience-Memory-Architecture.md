# ADR 0014：Agent Experience Memory 架构（Event Log Lite）

状态：已采纳
日期：2026-06-23
关系：**ADR 0012 的扩展，而非替代**。ADR 0012 仍然有效，负责定义 Memory 与 Knowledge 的边界、Runtime / Knowledge / Experience 三层概念模型与「Agent 经 Tool/Service 访问、不直连 DB/存储」铁律；本 ADR 只**向下细化 Experience 层的内部结构**，不改动 0012 的边界与另两层。

## 背景

ADR 0012 确立了三层记忆模型，但对 **Experience Memory（经验记忆）** 只给出「复用 `RunStore` + `evaluation`、按需新增经验存储」的占位描述，未决定经验**如何表示、如何关联结果、如何被检索**。这一欠建模直接导致 ADR 0013 不得不临时引入 `ExperienceCandidate` 来填补——缺口的根因在 Experience 层缺乏内部结构。

经 Phase 2 架构探索（候选方案 A Traditional Store / B Knowledge Graph / C Event Sourcing / D Agent Experience / E Vector / F Hybrid），结论是：

- 扁平 `MemoryStore(write/read/search)` 把「Agent 记忆」当缓存建模，**无法表达时间、因果与延迟反馈**——而 A 股投资场景的反馈是**延迟的、基于结果的**（T 日判断，T+N 日才知对错）。
- 完整 Event Sourcing（CQRS / 物化视图 / 重放）能力最强但复杂度过高，**当前阶段过度设计**。
- 取中间路线：**Event Log Lite**——append-only 经验事件日志 + 轻量投影（情景 / 语义），不引入 CQRS、不引入 Vector DB、不引入 Graph DB。

本 ADR 在 ADR 0012 Experience 层之内，落定这条 Event Log Lite 路线的**数据契约与关联关系**。**只设计架构，不实现代码。**

约束（AGENTS.md / 协作协议 / Phase 2 采纳结论）：

- 定位为 ADR 0012 的扩展，不废弃 0012。
- 不引入 Vector DB、不引入 Graph DB、不引入 CQRS。
- 守住铁律：Agent 不直连 DB / 不直连 Experience 存储；经 `MemoryTool → MemoryService → Store`。Experience 不复制 Knowledge 事实来源、不内嵌原始评估度量、不调用模型、不侵入 Agent Runtime。
- 复用既有抽象：`RunStore`（ADR 0008/0009）、`EvaluationResult`（ADR 0010）、`ExperienceCandidate`（ADR 0013）、wiki `Entity`（ADR 0007）。

## 待决问题（评审重点）

1. **经验的原子单位**是什么？用什么不可变记录表达「Agent 经历过的一件事」？
2. **情景（Episode）** 如何界定？它与 `RunStore` 的 `RunRecord` 关系如何（避免双写/职责重叠）？
3. **语义经验（Semantic Experience）** 如何从情景中提炼？与 ADR 0013 的 `ExperienceCandidate` 如何衔接？
4. **延迟反馈**：T+N 日的市场结果如何挂回 T 日的历史决策（A 股核心诉求），且不修改已写入的历史？
5. **与 Knowledge Entity 的引用**：经验如何指向「关于哪家公司/行业/事件」，又不复制知识、不破坏正交边界？
6. **与 Evaluation Feedback 的关联**：评估结果如何成为经验事件的一部分而不双写度量？

## 决定（建议方案，待确认）

### 0. 总览：Experience 层 = 事件日志 + 两类投影

```
ADR 0012 Experience Memory（本 ADR 向下细化）
  │
  ├─ 真相基座：ExperienceEvent（append-only 事件日志，Event Log Lite）
  │     └─ 不可变；新信息（含延迟结果）只追加，永不就地修改历史
  │
  ├─ 投影①：Episode Memory（情景记忆）
  │     └─ 把同一 run / 同一研究主题的事件序列聚合为「一段经历」
  │
  └─ 投影②：Semantic Experience（语义经验）
        └─ 从情景中蒸馏出可复用的「教训 / 模式 / 有效路径」
           （= ADR 0013 ExperienceCandidate 晋升后的持久形态）
```

「投影」在本 ADR 指**对事件日志的只读派生计算**（遍历/聚合/过滤），**不是** CQRS 的物化读模型，不需要独立写库、不需要重放框架。

### 1. ExperienceEvent（经验事件，原子单位）

经验的原子单位是一条**不可变事件**，描述「某 Agent 在某时刻经历/产生了什么」。建议字段（仅定义形态，不实现）：

- `event_id: str` — 唯一标识。
- `episode_id: str` — 所属情景（见第 2 节；通常等于一次 run 的标识或一个研究主题标识）。
- `agent: str` — 产生该事件的 Agent。
- `type: ExperienceEventType` — 事件类型（枚举，见下）。
- `payload: dict` — 事件内容（按 type 解释）。
- `refs: ExperienceRefs` — 对外部对象的**引用而非拷贝**（见第 5/6 节）：`run_id` / `evaluation_ref` / `entity_ids` / `parent_event_id`。
- `occurred_at: datetime` — 业务发生时间（可与写入时间不同，支撑延迟回填）。
- `recorded_at: datetime` — 写入时间。

`ExperienceEventType`（最小集，可扩展）：

| 类型 | 含义 | 典型来源 |
|------|------|---------|
| `decision` | Agent 作出一个判断/结论 | run 过程中的关键决策 |
| `observation` | 记录一项观察/中间发现 | run step |
| `evaluation` | 一次评估产出被关联进经验 | ADR 0010 `EvaluationResult`（经 ref，不内嵌度量） |
| `outcome` | **延迟结果回填**：某历史决策的实际结果 | T+N 日市场结果 / ground truth |
| `lesson` | 蒸馏出的教训/经验（语义经验的事件化记录） | ADR 0013 Feedback 晋升 |

**不可变铁律**：事件一经写入不得修改/删除。修正一律以**新事件追加**（如 `outcome` 指向旧 `decision` 的 `parent_event_id`），保证可复盘、可审计、可重建「Agent 当时知道什么」。

### 2. Episode Memory（情景记忆，投影①）

- **定义**：一个 `episode` 是「一段有边界的经历」——默认对应**一次 run**（`episode_id` 可取 run 标识），也允许**跨 run 的研究主题**（如「对某公司的持续研究」）将多次 run 串成一个长情景。
- **形态**：Episode 不是新存储，而是「按 `episode_id` 聚合 `ExperienceEvent` 序列 + 摘要」的**只读投影**：`episode_id` / `agent` / `events: list[ExperienceEvent]`（按 `occurred_at` 排序）/ `summary`（可选派生）/ `entity_ids`（情景涉及的知识实体并集）。
- **与 RunStore 的边界（关键，避免双写）**：
  - `RunStore` 仍是「**运行过程快照**」的唯一所有者（`RunResult`/`Step`，ADR 0008）——**机械、完整、面向复现**。
  - Episode 是「**面向学习的经历视图**」——**选择性、带业务语义、可跨 run、可挂延迟结果**。
  - Episode 通过 `refs.run_id` **引用** `RunStore`，**不复制** `Step` 明细；需要原始轨迹时按 run_id 回查 `RunStore`。

### 3. Semantic Experience（语义经验，投影②）

- **定义**：从一个或多个 Episode 蒸馏出的**可复用结论**：失败模式 / 有效路径 / 退化信号 / 判断正确性规律。
- **与 ADR 0013 的衔接**：ADR 0013 的 `ExperienceCandidate` 是「候选语义经验」；经其**去重 / 合并 / 晋升阈值**后，晋升结果在本 ADR 中以 `type=lesson` 的 `ExperienceEvent` **事件化落入日志**，并可被投影为「当前有效的语义经验集合」。
- **形态（投影）**：`SemanticExperience`：`dedup_key` / `agent` / `kind`（failure_pattern / effective_path / regression / correctness）/ `summary` / `support_event_ids`（支撑它的事件引用）/ `score` / `occurrences`。**不内嵌**原始度量与原始 step，只引用。
- **确定性优先**：蒸馏规则沿用 ADR 0013「确定性、不调用模型」原则；模型在环的高级蒸馏留待远期、经 Tool/评审 Agent 产出、本层只消费结构化结果。

### 4. Evaluation Feedback 关联

- `EvaluationResult`（ADR 0010）通过 `refs.evaluation_ref`（如 `run_id + evaluator`）被 `type=evaluation` 的事件**引用**进经验日志，**绝不内嵌 metrics**——原始度量仍归 evaluation 所有（呼应 ADR 0013 边界），避免双写漂移。
- 闭环落位：`运行 → RunStore` →（ADR 0010）`Evaluator → EvaluationResult` →（ADR 0013）`Feedback → ExperienceCandidate` →（本 ADR）晋升为 `lesson` 事件 → 投影为 `SemanticExperience` → 经 `MemoryTool` 供后续 run 检索。**写侧链路至此打通且无双写。**

### 5. Knowledge Entity 引用关系

- 经验事件经 `refs.entity_ids` 指向 wiki-engine 的 `Entity`（公司/行业/政策/事件…），表达「这条经验**关于谁**」。
- **只引用 id，不复制 Entity 内容**：知识的事实来源仍唯一属于 Knowledge Engine（ADR 0012 正交边界）。需要实体详情时经 `WikiExtractTool` / Knowledge Service 只读回查。
- 由此自然支撑「公司研究历史」：给定 `company entity_id` → 反查引用它的 `decision`/`outcome`/`lesson` 事件 → 重建「我对这家公司的研究与判断历史」。
- **不建图库**：`entity_ids` 只是引用列表（关系的最小表达）；图遍历/推理留待远期，若需要再另开 ADR 引入 Graph 能力——本 ADR 明确不引入 Graph DB。

### 6. 存储与访问边界

- **存储抽象**：新增 `ExperienceStore`（append-only 语义），沿用 `RunStore` 范式——抽象 + 进程内默认 `InMemoryExperienceStore`（零依赖、local-first）+ 可选 DB 实现（置于 `services/persistence`，惰性导入、可选依赖，Experience 模块**不依赖任何 DB 驱动**）。建议接口形态：
  - `append(event) -> event_id`（只追加，不提供 update/delete）
  - `get_episode(episode_id) -> list[ExperienceEvent]`
  - `query(agent?, entity_id?, type?, since?, limit) -> list[ExperienceEvent]`（keyword/字段过滤，**无向量检索**）
- **与 ADR 0012 `MemoryStore` 的关系**：ADR 0012 的 `MemoryStore` 是 Memory 层的通用抽象；`ExperienceStore` 是 Experience 层在 Event Log Lite 路线下的**专用化**（append-only 事件语义）。实现阶段二选一即可——**建议 Experience 层直接采用 `ExperienceStore`**，`MemoryStore` 中 Experience 相关的通用 search 由 `ExperienceStore.query` 承担，避免两套重叠抽象。Runtime/Knowledge 层不受影响（仍按 ADR 0012）。
- **访问链路（不变，守 ADR 0012 铁律）**：
```
Agent → context.use_tool("experience_*") → MemoryTool → MemoryService
            └─(EXPERIENCE scope)→ ExperienceStore（append-only 事件 + 投影）
            └─(KNOWLEDGE scope) → Knowledge Service（只读回查 Entity 详情）
```
- Agent 不持有 `ExperienceStore` 引用；不直连 DB；不内嵌知识与度量；Experience 模块不调用模型、不侵入 Runtime。依赖单向：`experience → agent-runtime 抽象 + evaluation 抽象 + wiki 抽象`。

### 7. 支撑 A 股投资场景

| 场景 | 机制 |
|------|------|
| **公司研究历史** | 按 `entity_id` 反查相关 `decision`/`observation`/`outcome` 事件，跨 run 串成长情景 |
| **策略复盘** | `decision` 事件 + 延迟 `outcome` 事件配对 → 复盘「判断 vs 实际」；评估经 `evaluation` 事件引用 |
| **判断正确性分析** | `outcome` 回填后，蒸馏 `kind=correctness` 的语义经验，量化「某类判断的历史正确率」 |
| **Agent 能力提升** | `failure_pattern` 让 Agent 避坑、`effective_path` 让 Agent 复用成功路径，形成运行→评估→反馈→经验→改进闭环 |

延迟反馈是关键差异化：`outcome` 作为**新事件追加**并经 `parent_event_id` 挂回历史 `decision`，无需修改历史即可让「过去的判断」获得「未来的结果」，天然契合 A 股「事后才知对错」的特性。

## 原因

- **Event Log Lite 取中间路线**：用 append-only 事件日志拿到事件溯源最有价值的部分（时间、因果、延迟回填、可复盘），又通过「轻量只读投影」避开 CQRS/重放的复杂度——契合「架构正确性 > 长期扩展性 > 开发速度」且不过度设计。
- **扩展而非替代 0012**：边界与三层概念是对的，错的只是 Experience 的存储原语；扩展保留既有共识，降低认知与迁移成本。
- **引用而非复制**：经验只引用 `run_id` / `evaluation_ref` / `entity_ids`，使 RunStore / Evaluation / Knowledge 各自保持唯一事实来源，杜绝双写漂移，呼应 0012/0013 边界。
- **复用既有抽象与范式**：`ExperienceStore` 沿用 `RunStore` 的「抽象 + 进程内默认 + 可选 DB」，local-first、零新依赖即可跑测试。
- **不可变 + 延迟回填**：直接解决 A 股「延迟、基于结果」反馈这一核心场景，是 ShanHai 区别于「炒股机器人」的认知系统基石。
- **明确不引入 Vector/Graph/CQRS**：把这些能力限定为远期、各自另开 ADR 的可插拔增强，防止「Knowledge=RAG+Vector」式的早期简化与重依赖。

## 影响

- 新增模块（实现阶段）`services/experience`（或并入 `services/memory` 的 Experience 子域）：`ExperienceEvent` / `ExperienceEventType` / `ExperienceRefs` / `Episode`（投影）/ `SemanticExperience`（投影）/ `ExperienceStore`（含 `InMemoryExperienceStore`）。依赖单向：`→ agent-runtime + evaluation + wiki 抽象`，不依赖 DB / 模型。
- ADR 0012：保持有效；其 Experience 层「按需新增经验存储」的占位由本 ADR 具体化为 Event Log Lite；Runtime / Knowledge 两层不变。
- ADR 0013：`ExperienceCandidate` 的晋升产物明确落为 `type=lesson` 事件 + `SemanticExperience` 投影，Feedback 闭环写侧自洽；evaluation/feedback 仍不内嵌度量。
- `RunStore` / `evaluation` / `wiki-engine` / `model-router`：**零改动**，仅被引用消费。
- `persistence`：实现阶段可按需新增持久 `ExperienceStore`（复用 SQLite/Postgres，append-only 表），惰性导入、可选依赖。
- local-first：默认 `InMemoryExperienceStore`，无外部依赖即可测试。
- 文档：CHANGELOG / PROJECT_STATE / docs 索引在**实现阶段**同步更新（本 ADR 阶段不写代码）。
- 明确不引入：Vector DB、Graph DB、CQRS、模型在环蒸馏（均为远期、各自另开 ADR）。
- 不触碰本阶段「暂不开发」清单（行情/交易/自动交易/量化/回测）。

## 备选方案（已考虑）

- **维持 ADR 0012 扁平 `MemoryStore`**：无法表达时间/因果/延迟反馈，Experience 仍欠建模，与长期目标错配，不采纳。
- **完整 Event Sourcing（CQRS + 物化视图 + 重放）**：能力最强但复杂度过高、当前过度设计，不采纳；取 Event Log Lite。
- **Knowledge Graph Memory（经验与知识混入一张图）**：破坏 0012 正交边界、污染知识唯一事实来源、需 Graph DB 重依赖，不采纳；改用「`entity_ids` 只读引用」表达关系。
- **立即引入 Vector 检索做语义召回**：把检索实现误当记忆架构、过早引入重依赖，违反「Knowledge≠RAG+Vector」，不采纳；keyword/字段过滤起步，vector 远期另开 ADR。
- **Episode 复制 RunStore 的 Step 明细**：双写、冗余、漂移，不采纳；Episode 经 `run_id` 引用 RunStore。
- **经验事件可就地修改/删除以"更新"结论**：破坏可复盘/可审计、丢失「当时认知」，不采纳；一律以新事件（如 `outcome`/`lesson`）追加修正。

## 增补（Addendum，2026-06-23）：Stage 2-a — Outcome Feedback Foundation

> 背景：本 ADR §1 列出 `decision / observation / outcome` 等事件类型，但未规定其**生产者**，导致 Stage 1 落地后只有 `lesson`（由 ADR 0013 Feedback 写）有真实来源，其余事件类型为设计真空。同时 §6 建议接口 `get_episode` / `query` 与 Stage 1 实际实现（`append / get / list`）尚未对齐，`list` 缺 `episode_id` / `parent_event_id` 过滤，无法支撑「decision → outcome」关联与跨 run 情景聚合。经 Phase 2/3 评审，新增 **ADR 0015** 作为本 ADR 的 **Stage 2-a 实现决策**，本节登记其范围与对本 ADR 的影响，**不重新设计 Event Log**。

### A. 事件生产者定义（引用 ADR 0015）

`decision / observation / outcome` 的生产者由 ADR 0015 定义，均为 **service 层写入编排能力**，落于 `services/experience/shanhai_experience/ingest/`：

| 事件类型 | 生产者 | 来源 |
|---------|--------|------|
| `decision` / `observation` | `ExperienceRecorder` | `RunRecord`（经 RunStore 抽象只读，不改 `AgentRunner`） |
| `outcome` | `OutcomeIngestor` | 外部真实结果（调用方注入，Stage 2-a 不接真实数据源） |
| `lesson` | `Feedback`（ADR 0013，已实现） | `EvaluationResult` |

不变量不变：Agent 不直接写 Experience；`agent-runtime` 不依赖 `experience`；三类生产者互不依赖、均经 `ExperienceStore.append`（service → service）。详见 ADR 0015。

### B. 查询能力要求（修正本 ADR §6 接口形态）

`ExperienceStore` 读接口在 Stage 1 的 `list(agent / type / entity_id / since / limit)` 基础上**增加** `episode_id` 与 `parent_event_id` 过滤，落实本 ADR §6 提出的 `get_episode` / `query` 意图：

- `list(parent_event_id=...)` → 支撑 `decision --parent_event_id--> outcome`（延迟结果回填的关联查询）。
- `list(episode_id=...)` → 支撑 `episode → {decision, observation, outcome, lesson}`（跨 run 情景聚合）。

仅扩展查询：**不修改 `ExperienceEvent` schema、不修改 `append` 契约**（守本 ADR 不可变铁律）。

### C. episode 跨 run 语义（明确本 ADR §2）

明确 `episode_id != run_id`：`episode` 是长期研究主题 / 认知任务，`run` 是一次执行实例，一个 episode 可串联多次 run（如「Tesla 2026 Q1 投资研究」串联 run-001 初次分析 / run-002 财报更新 / run-003 结果验证）。`episode_id` 缺省时回退 `run_id`（兼容 Stage 1），回退逻辑由 ADR 0015 的统一函数 `resolve_episode_id(explicit, run_id)` 收口。

本节不引入 Vector / Graph / CQRS / Episode 物化投影（与本 ADR 既有约束一致）；Stage 2-a 只建「decision → outcome → lesson」事实链。

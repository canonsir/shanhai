# ADR 0015：Agent Experience Outcome Feedback 架构（Stage 2-a：Outcome 回填基座）

状态：已采纳
日期：2026-06-23
关系：**ADR 0014（Event Log Lite）的 Stage 2-a 实现决策**。不替代、不重设计 0014 的事件模型与边界；只补齐「事件生产者 + 延迟结果回填 + 查询能力」。关联 ADR 0012（Memory 访问层边界）、ADR 0013（Evaluation Feedback 写经验）。

## 1. 背景

ShanHai 已打通经验闭环的**后半段**：

- ADR 0014（Event Log Lite）确立 `ExperienceEvent` 为 append-only 不可变事件，含 `event_id / episode_id / agent / type / payload / refs / occurred_at / recorded_at`，以 `refs`（`run_id / evaluation_ref / entity_ids / parent_event_id`）引用而非复制；`occurred_at`（业务发生时间）与 `recorded_at`（写入时间）分离，天然支撑延迟回填。
- ADR 0013 Stage 1（已实现，commit 31609c0）打通 `Run → Evaluation → Feedback → ExperienceEvent(type=lesson)`：`FailurePatternRule → CandidateRegistry → 阈值晋升 → ExperienceStore.append`，并经 `MemoryTool`（`EXPERIENCE` scope 只读）反哺下一次运行。

但 `ExperienceEventType` 定义了 5 类事件（`decision / observation / evaluation / outcome / lesson`），**当前只有 `lesson` 一类有真实生产者（Feedback）**。其后果是：

- Agent 的「**决策（我当时判断了什么）**」没有被记录为事件；
- A 股场景关键的「**T+N 真实结果回填（我的判断后来对不对）**」没有入口；
- 经验目前只能从「运行失败模式」中学习，**无法从「判断 → 真实结果」的事实链中学习**。

本阶段目标不是「如何更好地总结经验」，而是先补齐「**让真实结果进入 Experience Event**」这一事实基座，使系统拥有可验证的事实记忆链：

> **我曾经做过什么判断 → 后来真实发生了什么 → 未来如何利用这个经验。**

本 ADR 定义 **Experience Event 的生产者（Producer）体系**与 **Outcome 回填能力**，落实 `Decision Event → External Outcome → Outcome Event → Feedback/Lesson` 链路。

约束（AGENTS.md / 协作协议 / Phase 3 Review 采纳结论）：

- 属架构变更，先 ADR 后实现（本 ADR）。
- 调用链铁律：所有生产者属 **service 层**，**不得进入 agent-runtime**，**Agent 不直接写 Experience**；`Agent → MemoryTool(read) → Experience` 保持不变。
- 不破坏 ADR 0010 / 0012 / 0013 / 0014 既有单向依赖与边界。
- 本阶段只建「事实链」，不做经验智能化抽象。

## 2. 当前问题

| # | 问题 | 现状 | 后果 |
|---|------|------|------|
| P1 | **事件生产者真空** | 仅 `lesson` 有生产者；`decision / observation / outcome` 无人产出 | 事件类型形同虚设，无法支撑「判断 → 结果」学习 |
| P2 | **无结果回填入口** | 没有任何组件把「外部真实结果」写成 `outcome` 事件 | A 股 T+N 结果无法进入经验闭环 |
| P3 | **查询能力不足** | `ExperienceStore.list(agent / type / entity_id / since / limit)`，**无 `episode_id`、无 `parent_event_id` 过滤** | 无法做 `decision --parent_event_id--> outcome` 关联，无法按 episode 聚合 `{decision, observation, outcome}` |
| P4 | **episode 语义被收窄为单 run** | Stage 1 `FeedbackEngine._promote` 将 `episode_id` 设为 `trigger_run`（单 run） | 与「episode = 研究主题、可跨 run」目标矛盾，跨 run 结果回填无法归属同一 episode |
| P5 | **decision 的 run_id 来源链路待明确** | `RunResult` 无 `run_id`；`run_id` 仅由 `RunStore.save_run` 生成，`runner._persist` 丢弃返回值 | 生产 `decision` 事件需明确「从哪里拿稳定 run_id」——结论：从 `RunStore` 的 `RunRecord` 取，不改 `runner` |

## 3. 决策

### Decision A — 新增 Experience Event Producer 体系（service 层）

Experience 事件由三类生产者写入，三者并列、均为系统编排层，互不依赖、都不进入 agent-runtime：

1. `Feedback`（已存在）：`Evaluation → ExperienceEvent(type=lesson)`。
2. `ExperienceRecorder`（新增）：`RunRecord → ExperienceEvent(type=decision | observation)`。
3. `OutcomeIngestor`（新增）：`外部真实结果 → ExperienceEvent(type=outcome)`，经 `refs.parent_event_id` 挂回对应 `decision` 事件。

保持不变量：

```
Agent → MemoryTool(read only) → Experience
- Agent 不直接写 Experience
- agent-runtime 不依赖 experience
```

### Decision B — 不修改 `ExperienceEvent` 核心模型，保持 append-only

现有模型已具备回填所需的全部字段（`parent_event_id` + `occurred_at / recorded_at` 分离 + 不可变 append）。本 ADR **不新增 / 不改动模型字段、不改动 append 契约**。

### Decision C — `ExperienceStore` 增加查询能力（仅扩展读）

`list(...)` 新增可选过滤参数 `episode_id` 与 `parent_event_id`，支撑两类查询：

- `decision --parent_event_id--> outcome`（按 `parent_event_id` 找某决策的结果回填）；
- `episode → {decision, observation, outcome, lesson}`（按 `episode_id` 聚合一个研究主题的全部事件）。

限制：只增强查询，**禁止修改 `ExperienceEvent` schema、禁止修改 append 契约**。

### Decision D — `episode_id` 语义跨 run

```
episode = 一个长期研究主题 / 认知任务
run     = 一次执行实例
```

例：`episode = "Tesla 2026 Q1 Investment Research"` 串联 `run-001(初次分析) → run-002(财报更新) → run-003(结果验证)`，三次 run 的 `decision` 与最终 `outcome` 全部归属同一 episode，可一次性聚合复盘。明确 **`episode_id != run_id`**，不限定 `episode_id == run_id`。

**默认回退**：`episode_id` 缺省时回退 `run_id`（兼容 Stage 1）。实现注意：**fallback 逻辑统一收口为单一函数 `resolve_episode_id(explicit_episode_id, run_id)`**，不扩散到多处，避免未来 episode 体系变化产生大修改面。

### Decision E — 范围收窄为 Stage 2-a「Outcome 回填基座」

仅建「事实链」，不做经验抽象。明确**不做**（全部延期，见第 7 节）。

### Decision F — Experience 三层演进边界（架构约束，仅声明，不实现）

> 背景：当前实现隐含假设 `ExperienceEvent = Experience`。在引入经验演化（EvoMap 类）理念后，确认该假设存在长期风险——「事实事件」与「可复用经验资产」是不同层次，若不预留边界，未来经验资产化会触发重构。本 Decision **只补架构演进声明，不改动 Stage 2-a 任何代码**。

确立 Experience 三层职责分层（演进方向）：

```
ExperienceEvent          事实记录，不可变事件（已实现）
      │ Candidate Promotion
      ▼
ExperienceCandidate      从事件中发现的候选规律（已存在于 feedback，见 ADR 0013）
      │ 验证 / 复用 / 演化
      ▼
ExperienceArtifact       经过验证、可复用、可演化的经验资产（未来，未实现）
```

| 层 | 职责 | 当前状态 |
|----|------|----------|
| `ExperienceEvent` | 事实记录，不可变事件 | Stage 1 已实现 |
| `ExperienceCandidate` | 从事件中发现的候选规律 | ADR 0013 Stage 1 已实现（feedback 内） |
| `ExperienceArtifact` | 经过验证、可复用、可演化的经验资产 | 延期，本阶段不实现 |

声明（约束未来演进，不改当前行为）：

- **`ExperienceEvent ≠ 最终经验资产**：事件是「发生过的事实」，不是「可信赖的知识」。
- **`lesson` 是事件层反馈，不代表稳定知识**：`type=lesson` 事件是 Feedback 在事件层的即时归因产物，仍属事实流，**不等同于** `ExperienceArtifact`。
- **`ExperienceArtifact` 经 Candidate Promotion 生成**：未来由 `ExperienceCandidate` 经验证/晋升固化为可复用、可演化的经验资产；该层另启 ADR 设计，不在 Stage 2-a。
- **知识投影层在更外侧**：`ExperienceArtifact → Knowledge Projection → WeKnora / llm-wiki` 属**知识投影层**，不属经验产生层；当前 ShanHai 仍处「事实采集 → 经验形成」阶段，WeKnora / llm-wiki 暂不接入（见第 7 节）。

本 Decision 不改动 `ExperienceEvent` schema、`ExperienceStore`、`OutcomeIngestor`、`ExperienceRecorder`、`MemoryTool`、Agent Runtime 边界；当前代码继续作为 Stage 2-a 实现。

## 4. ExperienceEvent Producer 定义

三类生产者的契约（**仅定义；实现见 Phase 4**）：

### 4.1 ExperienceRecorder（新增）— 决策 / 观察事件

- **职责**：把一次运行（及未来的 Research 主题）转写为 `decision` / `observation` 事件。
- **输入来源**：从 `RunStore` 读取 `RunRecord`（**自带稳定 `run_id`**），不依赖 `RunResult`（其无 `run_id`），**不修改 `runner`**（守住 agent-runtime 不依赖 experience）。
- **产出**：
  - `decision` 事件：`agent` = 运行 Agent；`episode_id = resolve_episode_id(explicit, run_id)`；`refs.run_id` = 该 run；`payload` = 决策摘要（结论 / 判断 / 动作），**不复制 Step 全量**。
  - `observation`（可选）：运行过程中的关键观察，归属同一 episode。
- **边界**：service → service；不调用模型；不写 `lesson` / `outcome`；append-only。

### 4.2 OutcomeIngestor（新增）— 结果事件

- **职责**：把**外部真实结果**（T+N 股价 / 事件实际走向 / 人工标注对错）写成 `outcome` 事件，并挂回对应决策。
- **输入契约（Stage 2-a，不接真实数据源）**：

```
OutcomeIngestor.ingest(
    decision_event_id,
    outcome_payload,
    occurred_at,
)
```

  调用方负责提供：`decision_event_id`、`outcome` 数据、结果发生时间。示例：

```python
{
    "decision_event_id": "evt_xxx",
    "outcome": {"return": 0.12, "direction": "up", "correct": True},
    "occurred_at": "2026-07-01",
}
```

- **产出**：`outcome` 事件：`refs.parent_event_id = decision_event_id`；`episode_id` / `agent` 沿用该决策事件；`occurred_at` = 结果真实发生时间（T+N），`recorded_at` = 回填时刻（二者分离正是为延迟回填设计）；`payload` = 实际结果与（可选）对错判定。
- **边界**：service → service；不调用模型；只写 `outcome`；append-only；**不回改 decision 事件**（不可变，靠 `parent_event_id` 关联）。
- **不做**：股票 API 接入、数据同步服务、定时任务、市场数据 pipeline。原因：当前目标是验证 Experience Event 模型，而非建设数据基础设施。

### 4.3 Feedback（已存在）— 教训事件

- 维持 ADR 0013 Stage 1：`Evaluation → lesson`，经 `ExperienceStore.append`。
- **本 ADR 仅做一处微调**：`_promote` 的 `episode_id` 由「强制单 run」改为经 `resolve_episode_id(explicit, run_id)` 解析（Decision D），与跨 run 语义一致；缺省回退 run，保持兼容。
- **未来衔接（不在本阶段实现）**：当 `outcome` 事件存在时，Feedback 可消费 `decision + outcome` 派生「判断正确性」类 lesson —— 本 ADR 只打通数据可得性，规则留待后续。

### 4.4 生产者全景

```
                 ┌──────────── Experience Event Producers (service 层) ────────────┐
RunStore ──read──► ExperienceRecorder ──append──► decision / observation
外部真实结果 ──────► OutcomeIngestor   ──append──► outcome  (refs.parent_event_id → decision.event_id)
Evaluation ───────► Feedback (已存在)  ──append──► lesson
                 └────────────────────────────────────────────────────────────────┘
                                          │ append-only
                                          ▼
                                   ExperienceStore
                                          │ 只读 query (+episode_id / +parent_event_id)
                                          ▼
                            Agent ◄── MemoryTool(EXPERIENCE, 只读)
```

## 5. 数据流

**写侧（事实链建立，本 ADR 范围）**：

```
T 日：  ExperienceRecorder(RunRecord) ─► decision 事件
                                          event_id = D1, episode_id = E, refs.run_id = R1
        (可选) ───────────────────────► observation 事件 (episode_id = E)

T+N：  OutcomeIngestor(decision_event_id=D1, outcome, occurred_at=T+N) ─► outcome 事件
                                          refs.parent_event_id = D1, episode_id = E
                                          occurred_at = T+N(真实), recorded_at = 回填时刻

(后续) Feedback(Evaluation[+ decision/outcome]) ─► lesson 事件 (episode_id = E)
```

**读侧（聚合与反哺，复用既有只读通路）**：

```
查某决策的结果： ExperienceStore.list(parent_event_id = D1)   → [outcome ...]
查一个研究主题： ExperienceStore.list(episode_id = E)         → [decision, observation, outcome, lesson]
Agent 反哺：     Agent → MemoryTool(EXPERIENCE, search/read) → Experience（只读，不变）
```

## 6. 依赖方向

所有新生产者作为 Experience 领域的**写入编排能力**，落于 `services/experience/shanhai_experience/ingest/`（不新增独立 service，避免多个平级 service 都操作 Experience 导致领域边界分散）。依赖单向、无环；**绝不让 agent-runtime / evaluation / experience 反向依赖生产者**：

```
experience.ingest.recorder ──read──► agent-runtime（只读 RunRecord，经 RunStore 抽象）
                           └─append─► ExperienceStore

experience.ingest.outcome  ─append─► ExperienceStore
                           （外部结果由调用方/装配层注入，自身不直连任何外部存储）

feedback (已存在)          ──read──► evaluation
                           └─append─► ExperienceStore
                           └─read──► agent-runtime

# 不变量
- agent-runtime  不依赖 experience / feedback / recorder / ingestor
- ExperienceStore 不依赖任何生产者（被动被写）
- 三类生产者     互不依赖
- Agent          只经 MemoryTool 只读 Experience，无任何写路径（AgentContext 不持有 Store/Producer 引用）
```

落点结构：

```
services/
 ├── experience/
 │    └── shanhai_experience/
 │          ├── models.py
 │          ├── store.py
 │          └── ingest/
 │                ├── recorder.py   # ExperienceRecorder
 │                └── outcome.py    # OutcomeIngestor
 ├── feedback/
 └── evaluation/
```

注：`ingest.recorder` 读 `RunRecord` 引入 `experience → agent-runtime` 依赖。该方向单向合法（agent-runtime 不反向依赖 experience），与既有 `feedback → agent-runtime`、`evaluation → agent-runtime` 同构。

## 7. 不做事项（本阶段明确延期）

```
❌ SemanticExperience          ❌ Episode Projection（仅做 list 过滤，不做投影层）
❌ Vector DB                   ❌ Graph DB
❌ CQRS                        ❌ Event Bus / 常驻服务 / 队列 / 定时任务
❌ EvaluationStore（ADR 0013 Stage 2 前置，另开）
❌ Memory persistence（ADR 0012 Layer 2）
❌ LLM 自动总结 lesson          ❌ 自动正确性归因
❌ 修改 ExperienceEvent schema  ❌ 修改 append 契约
❌ 修改 AgentRunner / RunResult（不为 RunResult 加 run_id）
❌ 由 outcome 自动派生「正确性 lesson」的新 Feedback 规则（仅打通数据可得性）
❌ 股票 API / 数据同步 / 市场数据 pipeline
❌ ExperienceArtifact 层（经验资产化，Decision F 仅声明演进边界，实现另启 ADR）
❌ Knowledge Projection / WeKnora / llm-wiki 接入（属知识投影层，非经验产生层）
```

## 8. 与 ADR 0012 / 0013 / 0014 的关系

| ADR | 关系 | 是否需改动 |
|-----|------|-----------|
| **0014（Event Log Lite）** | 本 ADR 是其 **Stage 2-a 落地**：把「事件类型」补上「生产者 + 回填 + 查询」。复用 `parent_event_id`、`occurred_at / recorded_at` 分离、append-only。 | **追加** Stage 2-a 一节（Producer 引用本 ADR、query 能力要求、episode 跨 run 语义），不重设计 Event Log |
| **0013（Evaluation Feedback）** | Feedback 维持 Stage 1 不变，仅 `episode_id` 解析改为 `resolve_episode_id`（跨 run）。本 ADR 为其未来「判断正确性 lesson」提供 `outcome` 数据基座。Decision F 进一步明确 Feedback 本质产物是 `ExperienceCandidate`、`lesson` 仅为事件层落地形态。 | 本阶段**追加 Addendum 2**（Feedback/Candidate 语义对齐，衍生自 Decision F，不改 Stage 1 代码）；微调点在本 ADR §4.3 |
| **0012（Memory）** | 不触碰 Memory 访问层：`EXPERIENCE` 对 Agent 只读、单 `MemoryTool` 不变；新生产者均为 service 层，Agent 无写路径。 | 本阶段**不改正文**，仅登记后续文档同步：`TODO: ADR0012 implementation alignment update — when: Memory / Experience persistence phase` |

## 原因

- **生产者体系补真空**：把「事件类型」从声明变为可生产的事实，是支撑「判断 → 结果」学习的前置基座；先建事实链，再做经验抽象，契合「架构正确性 > 长期扩展性 > 开发速度」。
- **不动核心模型 + append-only**：现有 `ExperienceEvent` 已为延迟回填备好（`parent_event_id` + 双时间戳 + 不可变），无需改模型即可承载 `decision → outcome`，避免破坏 0014 的事实基座契约。
- **生产者归入 experience.ingest**：两者本质是 Experience 领域的写入编排，紧贴 `ExperienceStore`，避免新增多个平级 service 分散领域边界；依赖仍单向 `experience.ingest → ExperienceStore`，与 `feedback → ExperienceStore` 同构。
- **episode 跨 run + 统一回退函数**：把「研究主题」与「执行实例」解耦，直接支撑 A 股长周期研究的跨 run 复盘；`resolve_episode_id` 收口回退逻辑，控制未来变化的修改面。
- **Outcome 不接数据源**：当前目标是验证事实记忆链而非建数据基础设施，避免过早引入运维复杂度与重依赖。

## 影响

- 新增（实现阶段）`services/experience/shanhai_experience/ingest/`：`ExperienceRecorder`（`RunRecord → decision/observation`）、`OutcomeIngestor`（`外部结果 → outcome`，`parent_event_id` 挂回）、`resolve_episode_id` 工具。`experience` 新增对 `agent-runtime` 抽象的单向只读依赖（读 `RunRecord`）。
- `ExperienceStore`：`list(...)` 增 `episode_id` / `parent_event_id` 过滤；`append` / `get` / schema **零改动**。
- `feedback`：`_promote` 改用 `resolve_episode_id` 解析 `episode_id`；其余不变。
- `agent-runtime` / `evaluation` / `model-router` / `wiki-engine` / `memory`：**零改动**（仅被只读引用 / 不受影响）。
- local-first：默认 `InMemoryExperienceStore`，无外部依赖即可跑测试。
- 文档：ADR 0014 追加 Stage 2-a 节；CHANGELOG / PROJECT_STATE 在实现阶段同步；ADR 0012 正文同步登记为后续 TODO。
- 不触碰本阶段「暂不开发」清单（行情 / 交易 / 自动交易 / 量化 / 回测）。

## 备选方案（已考虑）

- **新增独立 service（experience-recorder / outcome-ingestor 平级）**：导致多个平级 service 都操作 Experience，领域写边界分散，不采纳；归入 `experience.ingest`。
- **为支撑 decision 给 `RunResult` 加 `run_id` / 改 `AgentRunner`**：侵入 agent-runtime、违反「不改 runner」约束，不采纳；从 `RunStore` 的 `RunRecord` 取稳定 `run_id`。
- **可变 outcome：就地更新 decision 事件写入结果**：破坏 append-only 与可复盘性、丢失「当时认知」，不采纳；outcome 以新事件追加 + `parent_event_id` 关联。
- **本阶段即做 Episode Projection / Semantic / Vector**：超出事实链目标、过早复杂化，不采纳；仅做 `list` 过滤起步。
- **OutcomeIngestor 直接接股票 API / 定时任务**：把数据基础设施混入经验验证阶段，引入重依赖与运维成本，不采纳；Stage 2-a 由调用方注入结构化结果。
- **fallback 逻辑各处内联**：episode 体系演进时改动面失控，不采纳；统一收口 `resolve_episode_id`。

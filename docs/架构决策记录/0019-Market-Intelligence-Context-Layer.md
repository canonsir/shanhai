# ADR 0019：Market Intelligence Context Layer（从「可持久化基础设施」进入「认知系统」）

状态：**Contract Accepted（契约已批准）** —— 五项裁决（O1–O5）经 Review Gate 批准；**实现尚未开工**（Implementation 前继续 Review Gate）。
日期：2026-07-01
目标版本：v0.3.0
里程碑：Milestone 3 — Market Intelligence Platform Alpha（M3.4 = Context Layer）

关系：承接 [M3.4 Context Layer Contract Design](../design/m3.4-market-intelligence-context-layer-contract.md)（doc-only 契约稿）。本 ADR 把该稿中的 §10 开放裁决项 O1–O5 与 §2 两处架构观察**固化为决定**。上游 Persistence 契约见 [M3.3 SQLite Implementation](../design/m3.3-sqlite-implementation-plan.md) 与 [Schema Freeze](../design/m3.3-market-persistence-schema.md)（Option C：`knowledge_observation` spine + typed detail）。本 ADR **不**实现 Reasoning Engine / LLM 接入 / Data Provider（分属 M3.6 / M3.7，另立 ADR）。

> **修订 R1（2026-07-01，S1 开工前 Review Gate approved with adjustments）**：Review 在批准进入实现的同时对 5 处做了架构级微调。为遵「记录不覆盖历史」（D8 精神），原始裁决 D1–D8 正文保留，修订以本 R1 与就地 `> 修订` 指针叠加：**(1)** 依赖方向新增 `reasoning-engine` 层，修订为 `runtime-kernel → reasoning-engine → market-intelligence → market-data`，并确立铁律「**market-data 永远不知道 intelligence 存在**」；**(2)** `KnowledgeReadPort` 改名 **`ObservationReadPort`**（market-data 是 Observation Store 不是 Knowledge Store，命名不得暗示其拥有 knowledge）；**(3)** `MarketContextSnapshot` 收紧为 **ref-based** 认知快照，禁成为数据聚合容器；**(4)** `ContextAssembler` 第一版**纯 deterministic**（禁推理/总结/判断/LLM）；**(5)** S1–S4 重排（domain skeleton → ObservationReadPort → SQLite adapter → ContextAssembler）。详见文末 [§修订记录 R1](#修订记录-r1revision-log)。

## 1. 背景（Context）

M3.3 让 ShanHai 第一次拥有「可持久化认知基础设施」：真实 A 股 observation（行情 / 财务 / 公告）经 source-neutral provider 流入 `MarketKnowledgeRepository`，落 append-only `knowledge_observation` spine（默认 SQLite 后端，保留 InMemory reference / Postgres 扩展）。

```
Market Data → Provider → Repository → SQLite        ← 只是「存东西」（Persistence）
```

但「存东西」≠「理解东西」。ShanHai 的差异化资产不是行情获取、不是 LLM 调用、不是 Agent 数量，而是**长期市场认知资产**。若现在直接往 SQLite 里塞公司画像 / 行业知识 / 投资逻辑 / 市场规律，就会重蹈 daily_stock_analysis 的覆辙（`Database = 行情 + 新闻 + AI结果 + 用户行为 + 回测 + memory` 大杂烩）。

daily_stock_analysis 的认知链是「今天看到什么，今天分析什么」：

```
数据 → AnalysisContextPack → LLM → AnalysisHistory
```

ShanHai 的认知链应是「今天看到的数据只是刺激，真正参与决策的是长期认知」：

```
Observation → Knowledge Object → Market Context Snapshot → Decision → Feedback → Knowledge Evolution
```

## 2. 问题（Problem）

1. Persistence 解决「数据怎么保存」；缺一层解决「AI 在某个时间点知道什么」。
2. M3.3 的读投影是 **latest-only / current-truth**（9 方法 Repository 契约），无法回答「在过去某个时间点，一个投资者当时知道什么」（历史认知回放）。
3. 需要一个明确的模块边界，防止 `market-data` 膨胀成 `everything-data`（半年内必失控）。
4. 需要在写代码之前先冻结「AI 到底应该拥有什么市场认知」的形状，避免「有什么 API → 往里塞」的反向设计。

本阶段目标定性：

```
定义 AI 应拥有的市场认知（cognition contract）
    ——而非——
接入更多数据源 / 生成分析（acquisition / reasoning）
```

## 3. 决定（Decision）

### D1（O3）— 新增独立模块 `services/market-intelligence`，`market-data` 守 observation/persistence 边界

认知构建与市场事实存储是两种职责，必须分包：

```
services/
├── market-data            原始事实 / observation / persistence（M3.3，边界冻结）
├── market-intelligence    knowledge object / context / cognition（本 ADR 新增）
└── runtime-kernel         agent 执行
```

依赖方向（冻结）：

```
market-data ─► market-intelligence ─► runtime-kernel
```

> **修订 R1（依赖方向）**：新增 `reasoning-engine` 层，依赖方向修订为
> `runtime-kernel → reasoning-engine → market-intelligence → market-data`（新增 reasoning-engine，插在 runtime-kernel 与 market-intelligence 之间）。**铁律**：`market-data` 永远不知道 `intelligence` 存在——禁止 `market-data import KnowledgeObject`（否则 market-data 的领域模型会被 intelligence 概念污染，重蹈 everything-data）。read 方向仍是 `market-intelligence ──(只读端口)──► market-data`；依赖箭头（谁 import 谁）永远指向 market-data，绝不反向。

- **禁止** runtime 直接调用 market-data（否则 Agent 会逐渐绕过知识层）。Agent 推理应经 market-intelligence 提供的认知产物。
- `market-intelligence` 读 market-data 的**只读端口**（D2），不 import market-data 的存储实现细节。
- 未来 `market-intelligence` 下辖 `knowledge / context / cognition`（并预留 `evolution / reasoning / memory` 子域，本 ADR 不实现）。

### D2（O1）— bitemporal 读能力 = 新增独立 `ObservationReadPort`，不污染已冻结的 9 方法 Repository 契约

> **修订 R1（命名）**：原文命名 `KnowledgeReadPort` 已改名 **`ObservationReadPort`**（落 `services/market-data/shanhai_market_data/ports/observation_reader.py`）。理由：market-data 当前职责是 **Observation Store**，不是 Knowledge Store；`Knowledge*` 命名会暗示「market-data 拥有 knowledge」，污染领域所有权。真正的 `Observation → Knowledge Extraction → KnowledgeObject` 是 market-intelligence 内部的事，届时真正的 `KnowledgeReadPort` 应属 market-intelligence。**关键边界**：端口放在 market-data、返回 market-data 自己的只读 DTO，故其签名只用**基元类型**（`knowledge_at: datetime` 等），**不得**引用 market-intelligence 的 `AsOf`/`Observation`/`KnowledgeObject`（否则违反 R1 铁律「market-data 永不知 intelligence」）。下文出现的 `KnowledgeReadPort` 一律按 `ObservationReadPort` 理解。

M3.3 的 9 方法（5 写 4 读）是 current-truth 读契约，**保持冻结**。Context Layer 做 `as_of` 认知需要「截至某 knowledge_at 的 observation」——这是**新读能力**，落在一个独立只读端口：

```
ObservationReadPort（新增 Protocol，与 9 方法并列；放 market-data/ports/）
  query(subject, *, knowledge_at, effective_at=None, fact_types=())
      -> tuple[Observation, ...]        # Observation = market-data 自己的只读 DTO
```

- 它读 append-only spine（M3.3 已保留历史），按 `captured_at ≤ knowledge_at` 过滤。
- 既有 9 方法 = 「current truth」读；新端口 = 「historical cognition」读。两者并存、互不修改。
- 端口可由现有 SQLite adapter **额外实现**，InMemory reference adapter 同样可实现 → 仍可做 parity 测试（延续 M3.3 Step 2「SQLite == InMemory read-model parity」策略）。
- **不采纳**：(b) 在 `CompanyIntelligence` 读上加可选 `as_of`（会触碰冻结契约）；(c) 在 Context 模块内直接 SQL 读 spine（泄漏存储细节）。

### D3（O4）— 核心产物命名 `MarketContextSnapshot`，避免与既有 `RuntimeContext` 撞名

代码库已有 `RuntimeContext`（runtime-kernel，Agent 执行初始化快照，7 段 `frozen + extra=forbid`）。两者是不同层、不同生命周期、不同 owner：

| | `RuntimeContext`（既有） | `MarketContextSnapshot`（本 ADR） |
|--|--|--|
| 语义 | Agent 运行环境 | 市场认知环境 |
| 回答 | 「一次 Agent 运行如何被装配」 | 「在时间 T，关于某主体，ShanHai 知道什么」 |
| owner | runtime-kernel | market-intelligence |

- **禁止**裸 `Context` / `ContextBuilder`（后者太像 daily_stock_analysis，且与 RuntimeContext 概念混淆）。
- 关系：未来 Agent 推理时，`MarketContextSnapshot` 会成为喂给 `RuntimeContext` 的 task/intent 输入素材之一，但二者不合并。

> **修订 R1（ref-based，防 God Object）**：保持命名 `MarketContextSnapshot`，但**禁止**它变成新的万能对象/数据聚合容器。第一版形状严格收紧为 **ref-based**：
> `{ subject, as_of, observation_refs, knowledge_refs, market_state, cognition_state, data_quality }`。
> **禁止**按数据种类平铺内嵌（如 `{financials:{}, news:{}, technical:{}, chip:{}, ...}`）——那会在半年后又长成 daily_stock_analysis 的 `ContextPack`。定义：Snapshot = 「某个时间点，系统**认为自己知道什么**」，而**不是**「今天有哪些数据」。`identity/financial_state/events` 等按种类分区的旧草图字段（见契约稿 §4.2 与实现设计旧稿 §4）以本条为准废弃。

### D4 — 认知四层分层（Observation ≠ Knowledge ≠ KnowledgeObject ≠ Snapshot）

这是本层骨架，也是与 daily_stock_analysis 最大的架构分水岭：

```
Observation           已存在（M3.3 append-only spine）
  一条不可变记录：「source X 在 captured_at T 报告：主体的某属性 = V」
  带 provenance（SourceRef）/ confidence；可与其它源冲突；保留历史
    ↓（多条同 logical_key observation 调和）
Knowledge             派生的「当前信念」（M3.3 读投影 = latest per logical_key）
    ↓（以 company/industry/event 为中心聚合）
KnowledgeObject       主体聚合画像（M3.5 细化）
    ↓（在指定 as_of 冻结为可推理、可复现的认知态）
MarketContextSnapshot 本层产物
```

不变量：**Observation 是事实输入，Knowledge 是派生信念**。Context Layer 永不修改 observation；它**只读、只投影**。

例（澄清 Observation vs Knowledge 的粒度差异）：

```
Observation：  今天贵州茅台收入增长 15% / 今天新能源板块上涨 3% / 今天某公告发布
Knowledge：    贵州茅台 = 高端白酒消费品、品牌壁垒强、ROE 维持 30%+ 但增速下降、
               市场认知从成长股 → 稳定现金流资产、风险=消费降级/年轻消费迁移
               （非一天生成，需多年积累）
```

### D5 — bitemporal `as_of` 双时间轴进入核心设计

ShanHai 的 fact 模型已自带三时间戳（M2.5 冻结，永不塌缩），直接支撑双轴：

| 时间戳 | 轴 | 含义 |
|--|--|--|
| `occurred_at` | effective / valid time | 事件在世界里真正发生 |
| `published_at` | effective / valid time | 市场可见（披露）时刻 |
| `captured_at` | knowledge / transaction time | ShanHai 学到这件事的时刻 |

```
MarketContextSnapshot.as_of = { effective_at, knowledge_at }
  effective_at：截至世界的哪一刻（用 occurred_at/published_at 过滤/排序事件）
  knowledge_at：系统只采纳 captured_at ≤ knowledge_at 的 observation
```

- `knowledge_at = now` → 退化为「当前认知」（≈ current truth，但带 quality/provenance/历史认知）。
- `knowledge_at` = 过去某刻 → 「**当时 AI 会看到的认知**」（历史认知回放）。因 observation append-only + snapshot 可复现，回放是**确定性**的。

这正是 ShanHai 未来最重要的能力之一：回答「在过去那个时间点，一个投资者当时知道什么」（例：2021-03 当时已知宁德时代利润增长/政策支持/渗透率提升，未知后续估值泡沫与 2022 调整）。**首版只需 `knowledge_at` 过滤 + effective 排序**，不要求完整 SQL:2011 区间 bitemporal。

### D6（O2）— `MarketContextSnapshot` 首版不落库，作为 deterministic view

```
数据库：  facts / knowledge_observation / events        （已持久化）
运行：    ContextAssembler(subject, as_of) → MarketContextSnapshot   （按需计算，不落表）
```

- append-only + 可复现意味着快照可随时重算；落表是**优化而非正确性需求**。
- 避免「生成 Context → 存 Context」滑向「数据库里 100 万个无人知晓为何存在的 snapshot」。
- 未来若需 cache / audit / replay，再新增 `context_snapshot` 表（届时另经 Review），**不改正确性语义**。

### D7 — snapshot 每个数值携带 provenance + confidence + data_quality（「不是 ContextPack」的护栏）

daily_stock_analysis 的 `ContextPack` 只有裸值；ShanHai 的 snapshot 必须让 LLM 能区分「知道且可信 / 知道但存疑 / 不知道」：

- 每个 leaf = `{ value, provenance[], confidence }` 三元组；`provenance[]` 元素即现有 `SourceRef`（**零新造 provenance 词汇**）。
- `data_quality` 面：coverage（缺失显式 `missing[]`，不静默当 0）/ freshness（`max_staleness` + `stale_sections`）/ conflicts（多源不一致列 `competing_sources`）/ trust_floor（本 snapshot 内最低 `trust_level`）。
- `historical_cognition`（previous_analysis / previous_prediction / feedback）**只引用 id/ref，不复制**（受依赖边界约束，见 §5）。

### D8（O5）— 路线调整：M3.4 = Context Layer，M3.5 = Web Platform（记录，不覆盖历史）

原 PROJECT_STATE 把 M3.4 = Web Platform。本轮路线已从「基础平台」演进为「AI Native Market Intelligence Foundation」，故：

```
M3.4 Market Intelligence Context Layer   （本 ADR）
M3.5 Web Platform                        （原 M3.4 顺延）
M3.6 Data Provider（Free → Premium，iFinD/Wind 在此接）
M3.7 Reasoning Engine（AI cognition → feedback loop）
```

- 通过 PROJECT_STATE 更新**记录**此调整并引用本 ADR，**不直接覆盖历史**（保留原 Web Platform 条目为顺延，不删）。

## 4. 非目标（Non-goals，本阶段禁止）

- ❌ 任何实现代码（本 ADR 仅固化契约；实现前继续 Review Gate）
- ❌ 改 M3.3 的 9 方法 Repository 契约 / 改 schema / 落 `context_snapshot` 表
- ❌ 接 iFinD / Wind / akshare / Tushare Pro（属 Acquisition Layer，M3.6）
- ❌ Provider Interface 实现 / `SHANHAI_DATA_MODE` 装配开关（M3.6）
- ❌ ReasoningInput / Prompt / LLM / Agent 接入（M3.7）
- ❌ Knowledge Object 物化 / Industry / Event Intelligence 细化（M3.5）
- ❌ 修改 RuntimeKernel / RuntimeContext / Experience Runtime / Memory / Console 契约

## 5. 依赖方向（Dependency Direction，冻结）

```
market-data ─► market-intelligence ─► runtime-kernel
                     │
                     └─(只读 ref)─► experience（historical_cognition 仅引用 id，不 import）
```

> **修订 R1（依赖方向）**：链条修订为 `runtime-kernel → reasoning-engine → market-intelligence → market-data`（新增 reasoning-engine 层，`import` 箭头永远指向 market-data）。铁律：**market-data 永远不知道 intelligence 存在**（禁 `market-data import KnowledgeObject`）。M3.4 只落地 `market-intelligence → market-data`（经 `ObservationReadPort` 只读）；`reasoning-engine` 本阶段只登记不建。

```
# 不变量（R1 修订后）
- 依赖箭头：runtime-kernel → reasoning-engine → market-intelligence → market-data（永不反向）
- market-data 永不 import intelligence 任何概念（KnowledgeObject / MarketContextSnapshot / AsOf …）
- market-intelligence 读 market-data 经 ObservationReadPort（只读端口，签名仅基元类型），不 import 存储实现
- market-data 现有依赖禁令不变：禁 import runtime/experience/memory/evolution/feedback，禁 trading 术语（AST 校验）
- runtime 不直接调用 market-data（须经 market-intelligence 认知产物）
- Context Layer 对 provider 无感知：禁 `if source == "ifind"`；源信息只在 SourceRef 里
- historical_cognition 只引用 experience 的 id/ref，不 import experience 模块、不内嵌其内容
```

Provider 无感知保证（回答「未来 iFinD/Wind」）：接入 premium provider = 在 Acquisition Layer 多产生带 `SourceRef(provider=ifind, trust_level=…)` 的 observation；`MarketContextSnapshot` 自动经 provenance/trust_floor 反映，**Context 层零改动**。iFinD 未来只是 `iFinD Adapter → Observation`，而非 `iFinD → AI Prompt`。

## 原因

- **补齐认知层**：把散落的 observation 组装成「某个时间点的、可被 AI 推理消费的市场认知状态」，让 ShanHai 从 Persistence 迈向 Cognition。
- **模块分包（D1）**：守住 `market-data = observation/persistence`，防止膨胀成 everything-data。
- **additive 读端口（D2）**：以最小侵入获得 bitemporal 能力，零改冻结的 9 方法契约，仍可 InMemory/SQLite parity。
- **命名（D3）**：`MarketContextSnapshot` 与 `RuntimeContext` 语义分离，避免长期混淆。
- **bitemporal（D5）**：历史认知回放是 ShanHai 差异化的核心能力，`as_of` 双轴复用既有三时间戳，零新建模。
- **deterministic view（D6）**：可复现 → 快照可重算，首版不落表守住简洁性。
- **provenance/quality（D7）**：让认知系统能表达「知道/存疑/不知道」，与数据堆本质区分。

## 影响

- 新增独立包 `services/market-intelligence`（依赖 pydantic + market-data 只读端口）。
- market-data 侧新增 `KnowledgeReadPort` Protocol 与其 InMemory/SQLite 实现（additive，不改 9 方法）。
- PROJECT_STATE 路线表重编号（M3.4=Context / M3.5=Web Platform），以记录方式更新，不删历史。
- 不触碰本阶段「暂不开发」清单（实时行情 / 交易 / 自动交易 / 量化 / 回测）。
- daily_stock_analysis 研究结束：其价值（验证 AI+行情+分析流水线可复制、定位差异点=长期市场认知资产）已兑现，注意力回到 ShanHai。

## 备选方案（已考虑）

- **在 `CompanyIntelligence` 读上加 `as_of`**：触碰冻结的 9 方法契约，不采纳；改用独立 `KnowledgeReadPort`（D2）。
- **Context Layer 放进 `services/market-data`**：受依赖禁令约束且职责越界，会滑向 everything-data，不采纳；独立 `market-intelligence`（D1）。
- **snapshot 首版即落库**：过早引入无价值 snapshot 表，不采纳；首版 deterministic view（D6）。
- **裸 `Context` / `ContextBuilder` 命名**：与 RuntimeContext 撞名、像 daily_stock_analysis，不采纳；`MarketContextSnapshot`（D3）。
- **为保旧 roadmap 强行保留 M3.4=Web Platform**：路线已实质演进，不采纳；重编号并以 ADR + PROJECT_STATE 记录（D8）。
- **现在接 iFinD**：现在还不知道 Context Layer 需要哪些字段，提前接会破坏架构（临时 schema → 未来推倒），不采纳；先定义认知，再定义数据/provider。

## 修订记录 R1（Revision Log）

**R1 — 2026-07-01，S1 开工前 Review（"Review Gate approved with adjustments"）**

Review 批准 M3.4 进入实现，但要求在写第一行代码前落实 5 处架构级微调。裁决 D1–D8 主体不变，以下为增量修订（正文对应处已叠加 `> 修订 R1` 指针）：

| # | 调整 | 决定 | 落点 |
|--|--|--|--|
| R1-1 | **模块布局 + 依赖方向** | 未来四模块 `services/{market-data, market-intelligence, reasoning-engine, runtime-kernel}`；依赖方向修订为 `runtime-kernel → reasoning-engine → market-intelligence → market-data`（新增 reasoning-engine 层）。铁律：**market-data 永远不知道 intelligence 存在**（禁 `import KnowledgeObject`）。 | §1（D1）/ §5 |
| R1-2 | **端口改名** | `KnowledgeReadPort` → **`ObservationReadPort`**（market-data 是 Observation Store 不是 Knowledge Store，命名不得暗示拥有 knowledge）。端口仍放 market-data `ports/observation_reader.py`；签名只用基元类型，绝不 import intelligence 概念。备选名 `FactReadPort` / `ObservationQueryPort`。 | §3（D2） |
| R1-3 | **Snapshot 防 God Object** | 保持命名 `MarketContextSnapshot`，但收紧为 **ref-based**：`{subject, as_of, observation_refs, knowledge_refs, market_state, cognition_state, data_quality}`；禁按数据种类平铺（`financials/news/technical/chip`）。Snapshot = 「某时刻系统认为自己知道什么」，非「今天有哪些数据」。 | §3（D3） |
| R1-4 | **Assembler deterministic** | `ContextAssembler` 第一版**纯 deterministic**：只做查询 / 过滤 / 排序 / as_of 计算 / provenance 合并 / quality 计算；**禁**推理 / 总结 / 判断 / LLM 自动总结。 | 实现设计 §5 |
| R1-5 | **S1–S4 重排** | `S1 Domain skeleton（package + domain models + ports interfaces，不接 DB）→ S2 read contract（ObservationReadPort InMemory，不接 SQLite）→ S3 persistence adapter（SQLite adapter，验证 InMemory==SQLite parity）→ S4 context assembly（ContextAssembler 生成 MarketContextSnapshot，测 same observation + same as_of = same snapshot）`。 | 实现设计 §7 |

**执行节奏（Review 指令，verbatim）**：`Proceed S1 only, stop after commit for next gate.` 保持「一阶段设计 → Review → 单 commit → Review → 下一阶段」。

**iFinD 战略提醒（Review 重申）**：现阶段**不接、不要急着接**。正确顺序 `Context Layer → Knowledge Object → Data Requirement → iFinD Mapping`（先定义「我需要什么知识」，再决定「哪些 iFinD 数据填充它」），而非 `iFinD API → 看看能做什么`。ShanHai 在建「认知操作系统」不是「数据仓库」；提前接 iFinD 易滑向 Wind clone。

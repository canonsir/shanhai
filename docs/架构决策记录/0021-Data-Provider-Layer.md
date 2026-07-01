# ADR 0021：Data Provider Layer（外部数据源接入的可替换 Adapter 边界 + 统一 Observation Contract）

状态：**提议中（Proposed）** —— doc-only，待 Review Gate 批准。本 ADR **不写实现、不接 iFinD/akshare/Wind、不申请任何 token、不改 schema**；实现前继续 Review Gate（下一阶段 = M3.6.0 Provider Contract 实现，仍需批准后开工）。
日期：2026-07-01
目标版本：v0.3.x
里程碑：Milestone 3 — Market Intelligence Platform Alpha（M3.6 = Data Provider Layer）

关系：**additive 扩展** [ADR 0019（Context Layer，Contract Accepted + R1）](0019-Market-Intelligence-Context-Layer.md) 与 [ADR 0020（Knowledge Evolution Layer，Accepted + R4）](0020-Knowledge-Evolution-Layer.md)。ADR 0019 定义认知四层骨架（Observation → Knowledge → KnowledgeObject → MarketContextSnapshot）与 bitemporal `as_of`；ADR 0020 定义 Knowledge Evolution（解释性信念如何演化、LLM 唯一合法入口）。本 ADR 定义**认知链路最上游的入口层**——外部数据源如何进入系统、如何统一成 `Observation`、provider 如何可替换。它是 ADR 0019 **O5 路线**里 `M3.6 = Data Provider` 的正式冻结。本 ADR **不推翻** ADR 0019 的四层分层 / R1 依赖方向 / ObservationReadPort，也 **不推翻** ADR 0020 的「LLM 经 pipeline 而非直连」，而是在最上游补齐「数据从哪里来」的可替换边界。

---

## 1. 背景（Context）

S1–S4.3 已把 ShanHai 的**认知内环**跑通并冻结：

```
Observation（append-only spine，M3.3）
   ↓ ObservationReadPort（InMemory / SQLite parity，M3.4 S1–S3）
Knowledge Evolution（Candidate → Reasoning → RevisionGate → KnowledgeRevision，ADR 0020）
   ↓ KnowledgeResolver.resolve_at（S4.3-1，ref-only，无 current/latest/best）
KnowledgeView（materialized view，S4.3-2）
   ↓ ContextAssembler 经窄只读端口消费（S4.3-2 KnowledgeViewReader）
MarketContextSnapshot（ref-based deterministic view，不落库）
```

这条内环的正确性已被验证：**给定 `knowledge_at`，认知态可确定性回放**。但到目前为止，喂给它的 `Observation` 都来自测试构造 / M3.2 免费采集实验（EastMoney + CNInfo），**尚未有一条稳定的、可替换的「外部世界 → Observation」入口契约**。

M3.2 期间（[ADR 0019 O5 前的路线 pivot](../PROJECT_STATE.md)）已埋下正确的地基雏形：

- `PublicMarketDataProvider`（source-neutral Protocol，5 个 `fetch_*` 返回 `*Record + SourceRef`），EastMoney / CNInfo / Tushare 都是 peer 实现；
- `PublicDataAcquisitionService` 把 `provider.*Record → mapper/fact_mapper → MarketFact/FinancialFact → repository.upsert` 跑通；
- `ObservationReadPort` 两个实现已带 `record()/record_many()` 写方法，append-only、幂等于 `(logical_key, content_hash)`，且**身份由调用方算好后传入**（port 只落库）。

现在进入 M3.6，要回答的是**入口层的边界问题**，不是「写哪个 SDK」：

```
外部数据源结构千差万别（iFinD / Wind / akshare / 自爬公开数据）
        ↓  ← 这一步的契约必须冻结：谁负责归一化？归一化成什么？provider 如何可替换？
Observation（进入 ShanHai 后的唯一事实入口形状）
        ↓
Knowledge Evolution → Context → Decision（对数据源来处必须无感知）
```

## 2. 问题（Problem）

1. **数据源直接驱动 AI 是最容易走偏的地方**：若走 `iFinD → LLM → Knowledge` 或 `iFinD → AI Summary → Snapshot`，LLM 会变成事实来源（database），且系统会被单一 vendor 的数据结构绑死。这与 ADR 0020 D3/D6「LLM 是 reasoner 不是 database」冲突，必须在入口层就堵死。
2. **统一 Provider ≠ 统一 Observation**：若让 iFinD 的 DTO 结构在系统内部到处流通，一旦 iFinD 免费额度没了、要换 Wind/akshare/自爬，Knowledge/Context/Decision 全部受冲击。真正需要统一的是**进入系统后的 Observation 形状**，而非各家 provider 的接口形状。
3. **iFinD 是优先数据源，但不能变成系统依赖**：iFinD 字段丰富（行情 / 财务 / 研报 / 公告 / 资金流 / 行业分类），值得优先接入并借其信息模型校准 Observation；但架构上**不能冻结成 `Observation = iFinD DTO`**，否则等于把系统押在一个商业 vendor 的 schema 上。
4. **归一化职责若分散会失控**：若每个 provider adapter 各自算 `content_hash / logical_key`、各定身份规则，幂等/provenance 语义会在 N 个 adapter 里漂移，换 provider 时身份可能不一致（同一事实被判成两条 observation）。
5. **既有 M3.2 契约与新 spec 有命名/职责张力**：M3.2 的 `PublicMarketDataProvider` 是**读侧 `*Record` 契约**（返回 ShanHai 领域记录，非 Observation）；用户新 spec 要的是**写侧 `fetch_observations() -> Observation`**。且 legacy `MarketDataProvider`（Tushare-shaped，`sync.py` 仍用）已占用 `MarketDataProvider` 这个名字——新契约不能撞名。
6. **配置化缺位**：免费模式（akshare/mock）与增强模式（iFinD，需 credential）必须可切换，且 credential 必须配置化（不硬编码、不入库、不进日志），Context 层对 `SHANHAI_DATA_PROVIDER` 不可见。

本阶段目标定性：

```
定义「外部数据源如何统一成 Observation、provider 如何可替换、边界如何冻结」（provider contract）
    ——而非——
写 iFinD SDK / akshare 接口（provider implementation）
```

## 3. 决定（Decision）

> 本 ADR 的 D5 / D6 / D9 三处涉及与既有代码的取舍，是在 Phase 2 架构探索中识别的**默认收敛方向**（都选最低风险、与已冻结原则一致的选项）；若 Review 不认可可推翻。其余 D1–D4 / D7–D8 直接固化用户 M3.6 方向指令。

### D1 — 文档形式：新增 ADR 0021 + M3.6 设计说明

Data Provider Layer 是认知链路最上游的入口，其边界值得独立 ADR 冻结，不混入 M3.4/S4 的认知层文档。故：

- **本 ADR（0021）** 冻结「层是什么、与 0019/0020 的关系、统一 Observation 原则、Provider Boundary 不变量、子阶段序列」。
- **[M3.6 设计说明](../design/m3.6-data-provider-layer-contract.md)** 承载契约草图：`ObservationProvider` / `DataQuery` / observation 草稿、ingestion pipeline 每一步、providers 目录布局、配置策略细节。
- 二者均 **doc-only**；实现拆步（M3.6.0→M3.6.4），逐步经 Review Gate。

### D2 — 分层定位：Data Provider Layer 是入口层，**不属于** Market Intelligence / Knowledge Evolution

```
External Data Sources（iFinD / Wind / akshare / 自爬公开数据）
        │
        ▼
Data Provider Layer          ← 本 ADR：source-specific adapter，只负责「取数 + 归一草稿」
        │
        ▼
Market Data Observation      ← append-only spine（M3.3），provider 唯一合法产物形状
        │
        ▼
Knowledge Evolution          ← ADR 0020，对 provider 无感知
        │
        ▼
Context Layer                ← ADR 0019，对 provider 无感知
```

- iFinD / Wind / akshare 等**均属于 Data Provider**，不属于 Market Intelligence，不属于 Knowledge Evolution。它们是**可插拔的数据来源**，不是认知资产。
- Provider Layer 物理归属 `services/market-data`（Observation 的所有者），符合 R1 依赖方向（`market-intelligence → market-data`，箭头永不反向）。

### D3 — 统一 Observation，而非统一 Provider（核心裁决）

这是本 ADR 与用户方向指令的核心。**不统一 provider 的接口形状，只统一进入系统后的 Observation 形状**：

```
       iFinD                Wind               akshare              mock
         │                    │                   │                   │
     ifind mapper        wind mapper        akshare mapper       mock mapper
         │                    │                   │                   │
         └────────────────────┴─── Observation ───┴───────────────────┘
                    （进入 ShanHai 后唯一合法的事实形状）
```

- **外部数据源结构可以不同，进入 ShanHai 后必须统一成 `Observation`**。
- 收益：iFinD 免费额度没了 / 换 Wind / 换 akshare / 自爬公开数据，**都不会影响** Knowledge / Context / Decision——它们只见 `Observation`，永不见任何 provider DTO。
- 反面（禁止）：`iFinD 格式 → 系统内部到处使用`。任何 provider DTO 泄漏到 Knowledge/Context 层都是架构违规。

### D4 — Observation ≈ iFinD 信息模型的**稳定子集**，而非 `Observation = iFinD DTO`

用户真实意图是「不要为了兼容免费数据源重新设计一套弱结构」——这个方向对：**优先借 iFinD 丰富的信息模型来校准 Observation 的语义充分性**。但架构上**不冻结成 `Observation = iFinD DTO`**：

```
iFinD 字段全集（行情 / 财务 / 研报 / 公告 / 资金流 / 行业分类 …）
        │  取其稳定、跨源可复现的子集
        ▼
Observation {
    subject          主体（复用 market-data SubjectRef）
    fact_type        事实家族（复用 market-data FactType 分类）
    predicate/value  语义主张 + 值（object_value）
    captured_at      系统视角捕获时刻（knowledge_at 轴）
    occurred_at/published_at   世界视角时刻（effective_at 轴，可选）
    source           provenance（复用 market-data SourceRef，provider 只在此出现）
    content_hash     内容指纹（身份的一半）
    logical_key      逻辑键（身份的另一半）
}
```

- 转换示例：iFinD「最新市盈率 PE_TTM = 15.6 @ 2026-07-01」 → `Observation{subject=600519 对应 surrogate id, fact_type=financial/valuation, predicate="pe_ttm", object_value="15.6", captured_at=2026-07-01, source_ref=SourceRef(provider="ifind")}`。
- **复用现有 `Observation` DTO**（[ports/observation_reader.py](../../services/market-data/shanhai_market_data/ports/observation_reader.py)），不新造一套弱结构、不改其字段树。其字段已是「iFinD 信息模型稳定子集」的合理近似（`logical_key/content_hash/fact_type/subject/predicate/object_value/occurred_at/published_at/captured_at/confidence/source_ref`）。M3.6 接入时若发现语义缺口，经 ADR 修订补字段，而非让 provider DTO 绕过。

### D5 — 归一化位置：Provider 吐**观测草稿**，共享 **ingestion pipeline 定身份**（默认收敛，Q1）

「归一化成 Observation」拆成两段职责，**身份/provenance/幂等规则集中一处**：

```
provider adapter（source-specific）
   │  fetch + mapper：把 vendor payload 映射成「观测草稿」
   │  草稿含：subject / fact_type / predicate / value / captured_at / source(provider) / (occurred/published)
   │  草稿【不含】content_hash / logical_key —— 身份不在 provider 里算
   ▼
Observation Ingestion Pipeline（M3.6.2，共享，source-neutral）
   │  统一计算 content_hash（内容指纹）+ logical_key（逻辑键）
   │  统一幂等语义（append-only，幂等于 (logical_key, content_hash)）
   ▼
ObservationReadPort.record_many（已有写方法，M3.4）→ knowledge_observation spine
```

- 理由：身份规则若分散到 N 个 adapter，换 provider 时同一事实可能被判成两条 observation；集中到 pipeline 后，**换 provider 不影响身份逻辑**，最贴合 D3「统一 Observation 而非统一 Provider」。
- 现状坐实：`ObservationReadPort` 的 `record()/record_many()` 已存在，且**身份由调用方（即 pipeline）算好传入**，port 只 `INSERT OR IGNORE`。pipeline 是身份计算的自然归属，无需改 port。
- 备选（未采纳）：provider 直接产出完整 `Observation`（自带 hash）。契约更「重」，但身份逻辑分散、难保证跨 provider 一致，故不采纳。

### D6 — 与 M3.2 关系：新建 canonical 写侧契约，M3.2 标 legacy 渐迁（默认收敛，Q2）

- **新建写侧契约 `ObservationProvider`（canonical）**，签名 `fetch_observations(query: DataQuery) -> tuple[ObservationDraft, ...]`（草稿见 D5；命名 `ObservationDraft` 以区别落库后的 `Observation`，最终形态见 M3.6 设计说明）。
- **命名裁决**：新契约命名 `ObservationProvider`，**不复用** `MarketDataProvider`——后者已被 legacy Tushare-shaped Protocol 占用（`sync.py` 仍用）。用户 spec 里的 `MarketDataProvider(Protocol)` 概念，在 ShanHai 落地为 `ObservationProvider`，避免撞名。
- **M3.2 的 `PublicMarketDataProvider` + `acquisition.py` + mapper 链保留、标 legacy**：它是已验证的免费采集路径（EastMoney/CNInfo/Tushare），继续可用，逐步迁移到新 canonical 契约；**本轮不动它、不破现有 11 套测试**。
- 备选（未采纳）：直接改造 `PublicMarketDataProvider` 成 Observation 契约。契约唯一但一次性改动大、回归面广（动 EastMoney/CNInfo/Tushare + acquisition），风险高，故不采纳。

### D7 — Data Provider Boundary（6 条冻结不变量）

固化 provider 的能力边界，防止入口层越权污染认知层：

| # | 规则 | 含义 |
|--|--|--|
| B1 | **Provider 只能产生 Observation（草稿）** | provider 的唯一合法产物是喂给 ingestion pipeline 的观测草稿；不产生任何其他系统类型。 |
| B2 | **Provider 不允许产生 Knowledge** | 禁产出 `KnowledgeObject` / `Belief` / `KnowledgeRevision` / `KnowledgeView` 等认知资产（那属 Evolution 层）。 |
| B3 | **Provider 不允许调用 LLM** | 禁 `iFinD → LLM/AI Summary → …`；LLM 唯一合法入口是 Evolution pipeline 的 reasoning 步（ADR 0020 D6）。 |
| B4 | **Provider 不允许访问 Evolution** | 禁 import/读写 `EvolutionStore` / `KnowledgeResolver` / Evolution pipeline；provider 不知道 Evolution 存在。 |
| B5 | **Provider 可替换** | provider 是插件；换 provider 只影响 Data Provider Layer，不触及 Observation 下游任何层。 |
| B6 | **Provider credential 必须配置化** | key/secret 只经环境变量/配置注入，不硬编码、不入库、不进日志、不进 Observation/SourceRef 明文。 |

- 此边界由 AST/依赖校验守护（实现期落地，对齐 ADR 0019 R1 / ADR 0020 D9 的守护模式）：`services/market-data/.../providers/**` 禁 import `shanhai_market_intelligence` 任何符号、禁 import 任何 LLM/model 客户端。

### D8 — 配置策略：免费默认 / 增强可选 / 多 provider 预留

```
免费模式（默认）        SHANHAI_DATA_PROVIDER=akshare   或   =mock
增强模式（可选）        SHANHAI_DATA_PROVIDER=ifind
                       IFIND_APP_KEY=...    IFIND_SECRET=...   （credential 配置化，B6）
多 provider（未来）     按 capability 配 primary/fallback（示意，本轮不实现）：
                       market:      { primary: ifind, fallback: [akshare] }
                       fundamental: { primary: ifind }
                       news:        { primary: [ifind, crawler] }
```

- **Context 层对 `SHANHAI_DATA_PROVIDER` 不可见**：接入 premium = Data Provider Layer 多产生带 `SourceRef(provider=...)` 的 observation；禁认知层出现 `if source == "ifind"`（沿用 ADR 0019 R1-3「provider 无感知」）。
- provider 装配是 application-assembly 关注点，落在 factory（对齐现有 [factory.py](../../services/market-data/shanhai_market_data/factory.py) 的 `SHANHAI_MARKET_STORE` 装配风格）。
- 多 provider primary/fallback 编排本轮**只登记方向、不实现**（M3.6.1 只落单 provider 选择）。

### D9 — 子阶段序列：先 Mock 再 iFinD（默认收敛，Q3 = 本轮只出文档）

```
M3.6.0 Provider Contract        定义 ObservationProvider / DataQuery / ObservationDraft（interface only）
   ▼
M3.6.1 MockProvider             确定性假数据 provider，跑通「provider → 草稿」
   ▼
M3.6.2 Observation ingestion    共享 pipeline：草稿 → 算身份 → record_many → spine（D5）
   ▼   ← 到此验证闭环：真实/假数据 → Observation → Evolution → Context
M3.6.3 iFinD Adapter            第一个优先商业 provider（credential 配置化）
   ▼
M3.6.4 akshare Adapter          免费 provider peer
   ▼
M3.7 Reasoning Engine           （ADR 0020 D3，LLM 接入）
```

- **先 Mock 再 iFinD**：现在最重要的是验证 `真实数据 → Observation → Evolution → Context` **链路**，而不是验证 iFinD SDK。Mock + ingestion pipeline 打通即证明入口层契约成立。
- **本轮（M3.6 设计阶段）只出 ADR + 设计说明，不写实现代码**（符合 Phase 2 禁编码 / Review Gate）。M3.6.0 骨架代码下轮经批准后开工。

## 4. 非目标（Non-goals，M3.6 设计阶段全程禁止）

- ❌ 任何实现代码（本 ADR 与设计说明均 doc-only；实现前继续 Review Gate）
- ❌ 写 iFinD SDK / akshare 接口 / Wind 接入 / 申请任何 token 或 credential
- ❌ 冻结 `Observation = iFinD DTO`（只借其信息模型校准，D4）
- ❌ 让任何 provider DTO 泄漏到 Knowledge / Context 层（D3）
- ❌ 让 provider 产生 Knowledge / 调用 LLM / 访问 Evolution（D7 B2/B3/B4）
- ❌ 改动 M3.2 的 `PublicMarketDataProvider` / acquisition / mapper（本轮保留标 legacy，D6）
- ❌ 改 `Observation` DTO 字段树 / 改 `knowledge_observation` schema / 改 ObservationReadPort 契约
- ❌ 实现多 provider primary/fallback 编排（本轮只登记方向，D8）
- ❌ 推翻 ADR 0019（四层 / R1 / bitemporal / deterministic Assembler）或 ADR 0020（Evolution / LLM 唯一入口）

## 5. 依赖方向（Dependency Direction，冻结，沿用 ADR 0019 R1 / ADR 0020）

```
runtime-kernel ─► reasoning-engine ─► market-intelligence ─► market-data
                                                                  │
                              Data Provider Layer（本 ADR）────────┘ 物理归属 market-data
                                    ▲
              External Data Sources ┘（iFinD / Wind / akshare / crawler，经 adapter 进入）

# 不变量
- 依赖箭头永不反向；provider 属 market-data，永不 import market-intelligence（沿用 R1-1）
- provider 唯一产物 = Observation 草稿 → 经共享 ingestion pipeline 统一定身份 → spine（D5）
- provider 不产 Knowledge、不调 LLM、不访问 Evolution、可替换、credential 配置化（D7 B1–B6）
- 系统内部统一 Observation，禁任何 provider DTO 泄漏到 Knowledge/Context（D3）
- Observation ≈ iFinD 信息模型稳定子集，非 Observation = iFinD DTO（D4）
- Context 层对 SHANHAI_DATA_PROVIDER 无感知；禁 if source == "ifind"（D8，沿用 R1-3）
```

## 6. 暂缓（M3.6 设计阶段不做，留待后续 Stage / ADR）

- `ObservationProvider` / ingestion pipeline / Mock / iFinD / akshare 的**具体实现**（M3.6.0→M3.6.4，逐步经 Review Gate）。
- 多 provider primary/fallback **编排实现**与 per-capability 路由（D8 只登记方向）。
- iFinD 具体字段映射表（研报 / 资金流 / 行业分类 → fact_type 的完整 mapper 规则），接入时随 M3.6.3 细化。
- M3.2 legacy `PublicMarketDataProvider`/acquisition 的**实际迁移**到 canonical 契约（渐迁，非本轮）。
- Reasoning Engine / LLM 接入（M3.7，ADR 0020 D3）。
- Raw snapshot 重存储（data lake / object store），沿用 `SourceRef.raw_snapshot_ref` 仅 locator 的既有裁决。

## 7. 与既有 ADR 的关系

| ADR | 关系 | 本 ADR 是否要求其改动 |
|-----|------|----------------------|
| 0019（Context Layer） | 本 ADR 是其 O5 路线 `M3.6 = Data Provider` 的正式冻结；沿用 R1 依赖方向、R1-3 provider 无感知、四层分层 | 否（实现期在 0019「与既有 ADR 关系」追加前向引用，非本轮） |
| 0020（Knowledge Evolution） | 本 ADR 补齐 Evolution **上游入口**；沿用 D3/D6「LLM 经 pipeline 而非直连」，B3 在入口层再堵一道 | 否 |
| 0011（Model Provider） | provider 可替换 + 不直调具体 vendor DTO，与「Agent 禁直调具体模型、经 Router」同源精神 | 否 |
| 0009（Local-first 持久化） | 免费/mock 默认、无 token 即可跑，延续 local-first；credential 配置化不破坏本地默认 | 否 |
| 0014（Event Log Lite） | Observation append-only、引用而非复制、身份 = (logical_key, content_hash)，本 ADR 沿用 | 否 |

## 原因

- **统一 Observation 而非统一 Provider（D3）**：这是把「数据源直接驱动 AI」这个最容易走偏的地方一次性堵死的关键——下游只认 Observation，vendor 可随时替换。
- **Observation ≈ iFinD 稳定子集而非 = iFinD DTO（D4）**：既借商业 vendor 丰富信息模型校准语义充分性，又不把系统押在单一 vendor schema 上。
- **归一化集中到 pipeline（D5）**：身份/幂等/provenance 规则集中一处，换 provider 不产生「同一事实两条 observation」的漂移；且复用已有 `record_many` 写方法，零 schema 改动。
- **新建 canonical + M3.2 标 legacy（D6）**：契约唯一化的同时保住已验证免费路径与 11 套回归，避免一次性大改动。
- **Provider Boundary 6 条（D7）**：把 provider 的越权（产 Knowledge / 调 LLM / 访问 Evolution）在入口层冻死，守住 ADR 0020 的认知资产可信度。
- **先 Mock 再 iFinD（D9）**：验证的是链路而非 SDK；Mock + ingestion 打通即证明入口契约成立，避免过早陷入 iFinD SDK 细节。

## 影响

- 新增本 ADR（Proposed）+ [M3.6 设计说明](../design/m3.6-data-provider-layer-contract.md)（Contract Design），**不新增/修改任何代码、schema、依赖**。
- 明确认知链路最上游入口的边界，为 M3.6.0→M3.6.4 实现（逐步经 Review）冻结方向。
- 不触碰 ADR 0019/0020 已冻结的认知内环（四层 / bitemporal / deterministic Assembler / Evolution / LLM 唯一入口）。
- 不触碰本阶段「暂不开发」清单（实时行情页 / 交易 / 自动交易 / 量化 / 回测）。

## 备选方案（已考虑）

- **`Observation = iFinD DTO`（vendor DTO 作系统标准）**：把系统押在单一商业 vendor schema，免费额度没了即返工，不采纳；改为 Observation ≈ iFinD 信息模型稳定子集（D4）。
- **provider 各自算身份、直接产出完整 Observation**：身份/幂等逻辑分散到 N 个 adapter，换 provider 易漂移，不采纳；改为 provider 吐草稿、共享 pipeline 定身份（D5）。
- **改造现有 `PublicMarketDataProvider` 成 Observation 契约**：契约唯一但一次性改动大、回归面广，不采纳；改为新建 canonical + M3.2 标 legacy 渐迁（D6）。
- **复用 `MarketDataProvider` 命名**：与 legacy Tushare-shaped Protocol 撞名（`sync.py` 在用），不采纳；新契约命名 `ObservationProvider`（D6）。
- **provider 内直接调 LLM 做 AI Summary 再落 Observation**：`iFinD → AI Summary → Snapshot` 让 LLM 变事实来源，违反 ADR 0020 D3/D6，不采纳；LLM 唯一入口保持 Evolution reasoning 步，入口层 B3 再堵一道（D7）。
- **先接 iFinD 再补 Mock**：会陷入验证 iFinD SDK 而非验证链路，不采纳；先 Mock 再 iFinD（D9）。

# ADR 0021：Data Provider Layer（从「内部认知闭环」进入「真实市场数据接入」，统一 Observation 而非统一 Provider）

状态：**提议（Proposed）** —— 待 Review Gate 批准。**本 ADR 与配套 [M3.6 Data Provider Layer 设计说明](../design/m3.6-data-provider-layer-design.md) 均 doc-only：不写实现、不建 provider 目录、不接 iFinD/Wind/akshare、不改 schema、不申请任何 token；实现前继续 Review Gate（下一阶段 = M3.6.0 Provider Contract Review —— doc-only 冻结 4 条边界；其后 M3.6.1 契约代码骨架仍需批准后才开工）。**
日期：2026-07-01
目标版本：v0.3.0
里程碑：Milestone 3 — Market Intelligence Platform Alpha（M3.6 = Data Provider Layer 设计阶段）

关系：承接 [ADR 0019（Context Layer，Contract Accepted + R1）](0019-Market-Intelligence-Context-Layer.md) 与 [ADR 0020（Knowledge Evolution Layer，Accepted + R4）](0020-Knowledge-Evolution-Layer.md)。S1–S4.3 已验证 ShanHai 的**内部认知闭环**成立：`Observation → ObservationReadPort → Knowledge Evolution → KnowledgeResolver → KnowledgeView → ContextAssembler`（全程 mock/内存事实，不接真实数据）。本 ADR 冻结**认知闭环之前的一层**——真实外部数据如何进入系统、在哪里归一化成 `Observation`、以及 provider 的边界与可替换性。本 ADR **不推翻** ADR 0019/0020 的任何冻结点，只在 Observation 事实源**上游**新增一层；它落实 ADR 0019 R1 与 ADR 0020 §4 已预告的「iFinD 未来只是 `iFinD Adapter → Observation`，而非 `iFinD → AI Prompt`」。

> 关键前情：ADR 0019 D8 / ADR 0020 数据接入顺序均已裁定 `M3.6 = Data Provider`；ADR 0020 §4 Non-goals 明确「接 iFinD / Wind / akshare / Tushare Pro 属 Acquisition Layer，M3.6」。此前「不接 iFinD/Wind/akshare」是 **S4.2/S4.3 阶段禁令**（防止提前用真实数据污染尚未成型的认知层），**不是永久禁止**。内部闭环已在 S4.3 收口，现在解冻数据接入，进入 M3.6 设计。

---

## 修订记录

### R1（2026-07-01）—— 折入外部 Review 反馈：调和「provider 输出类型」分歧、收紧 M3.2 渐迁、新增 M3.6.0 Contract Review

一轮外部架构 Review（GPT）对 M3.6 提出替代路线：`provider 吐分家族 *Record（QuoteRecord/FinancialRecord…）→ 共享 Normalizer 做 Record→Observation → 保留 PublicMarketDataProvider 作正式契约`。经对照，该路线与本 ADR **承重原则完全一致**（归一化/定身份在共享层、统一 Observation 而非统一 Provider、provider 不产 Knowledge/不调 LLM、`Observation ≈ iFinD 子集`），真正分歧仅在 **provider 输出类型的命名**（通用 `ObservationDraft` vs 分家族 `*Record`）。且该替代路线内含一处矛盾：其「same/shared mapper」要成立，`*Record` 必须已被各 provider 归一化成 source-neutral 形状——**那个 source-neutral canonical 草稿正是本 ADR 的 `ObservationDraft`**；否则共享 Normalizer 就要 `if provider == "ifind"` 分支，即双方都反对的耦合。故本 ADR **保留 `ObservationDraft` 路线不变**，仅折入该 Review 的两个有效关切：

- **新增 D4a**：显式调和「语义映射在 provider 内 / 定身份在共享层」的分工边界（见下）。
- **收紧 D3**：`PublicMarketDataProvider` **不立即废弃**；先做 Contract Review 冻结边界，adapter 逐步迁移到 `ObservationDraft` 输出契约，**避免两套 provider 词汇长期并行**。
- **新增子阶段 M3.6.0 Provider Contract Review**（doc-only，冻结 4 条边界：Provider boundary / `ObservationDraft` contract / Normalization boundary / Migration strategy），原契约代码骨架顺延为 M3.6.1（见 D8）。M3.6.0 另附**冻结清单 5 点**（R1 明确，兑现外部 Review 调和）：canonical = `ObservationDraft`（不引入分家族 `*Record`）/ `*Record` 路线与 draft 的等价关系 / source-specific `*Record` 会致 shared normalizer provider coupling / `PublicMarketDataProvider` 仅迁移窗口非未来新增 contract / 商业 provider 仅可配置 adapter 非系统标准（见 D8）。

本 R1 不改任何承重决策（D1/D2/D4/D5/D6/D7），仅追加 D4a、收紧 D3、重排 D8 子阶段序号。

---

## 1. 背景（Context）

到 S4.3 为止，ShanHai 的认知链每一环都已用**内存/mock 事实**验证过可回放、可复现：

```
Observation（内存/mock，append-only spine）
   ↓ ObservationReadPort（InMemory / SQLite parity，截至 knowledge_at 的历史读）
Knowledge Evolution（Candidate → ReasoningPort → RevisionGate → KnowledgeRevision 版本链）
   ↓ KnowledgeResolver.resolve_at(subject, knowledge_at)（ref-only，无 current/latest/best）
KnowledgeView（materialized view：Evolution history 的确定性投影，不拥有 belief 内容）
   ↓ ContextAssembler（纯 deterministic，经窄只读端口消费 KnowledgeView）
MarketContextSnapshot（ref-based，as_of 冻结的认知态）
```

这条链**成立了**，但它一直缺一个真实的起点：**Observation 从哪来？** 目前只有两条真实数据的雏形：

- **M3.2 Data Acquisition Foundation**：`PublicMarketDataProvider`（source-neutral Protocol，5 个 `fetch_*` 返回 ShanHai 自己的 `*Record + SourceRef`）+ 免费实现（EastMoney / CNInfo）+ commercial optional（Tushare）；`PublicDataAcquisitionService` 走 `provider.*Record → mapper/fact_mapper → MarketFact/FinancialFact → repository.upsert`。
- **append-only observation spine**：`knowledge_observation` 表 + typed detail，身份 `(logical_key, content_hash)` 幂等，`ObservationReadPort` 读侧已就绪（`record()` / `record_many()` 写侧 API 已存在于两个 adapter）。

问题是：M3.2 的产物落点是 `MarketFact`（latest 投影领域对象），**不是** append-only 的 `Observation`；而认知层（Evolution）消费的是 `Observation`。两条真实数据雏形之间、以及它们与认知层之间，缺一层**明确冻结的 Provider 契约与归一化边界**。

同时，用户已明确下一阶段战略方向（本 ADR 的 authoritative 上游）：

- **iFinD 是优先数据源，但不是系统依赖**——`iFinDProvider` 只是一个可替换的 Provider Adapter；免费额度没了就换 Wind / akshare / 自己爬公开数据，**不能影响** Knowledge / Context / Decision。
- **统一 Observation，而不是统一 Provider**——外部数据源结构可以不同，但进入 ShanHai 后必须统一成 `Observation`。
- **不为兼容免费数据源重新设计一套弱结构**，但**也不冻结成 `Observation = iFinD DTO`**；正确表述是 `Observation ≈ iFinD 信息模型的稳定子集`。
- **先 Mock，再 iFinD**——现在最重要的是验证 `真实数据 → Observation → Evolution → Context` 链路，而不是验证 iFinD SDK。

## 2. 问题（Problem）

1. **Observation 的「侧」不明**：现有 `Observation`（[observation_reader.py](../../services/market-data/shanhai_market_data/ports/observation_reader.py)）是 spine 一行的**读侧投影 DTO**（身份 `logical_key + content_hash + captured_at`）；用户 spec 的 `fetch_observations() -> list[Observation]` 是 provider **写侧**产物。二者同名不同侧，若混为一谈，会让 provider 承担「算 content_hash / 定 logical_key / 定身份」的职责——身份规则将分散到每个 provider，难保一致、难保幂等。
2. **归一化位置未冻结**：外部数据 → `Observation` 的归一化（算 `content_hash`/`logical_key`、绑 provenance、幂等去重）应发生在**哪一层**？若在每个 provider 内部，则「换 provider」会连带重写身份逻辑，违背「统一 Observation 而非统一 Provider」。
3. **`MarketDataProvider` 名字已被占用**：用户 spec 里的核心接口 `class MarketDataProvider(Protocol)` 与 [provider.py](../../services/market-data/shanhai_market_data/provider.py#L71) 里 legacy Tushare-shaped 的 `MarketDataProvider`（`sync.py` 仍在用）**撞名**。新契约必须另起名，且不得破坏既有 11 套测试。
4. **与 M3.2 的关系未定**：M3.2 已有一套可运行的 source-neutral provider + acquisition 链。M3.6 是**推倒重写**它，还是在其之上新建 canonical 契约、让 M3.2 转 legacy 渐迁？前者回归面大、风险高。
5. **provider 边界易被侵蚀**：若不显式冻结，provider 很容易"顺手"调用 LLM 做摘要、或直接产出 Knowledge、或访问 Evolution——这正是 `iFinD → AI Summary → Snapshot` 这条被明令禁止的返工路径。
6. **配置/凭证策略缺失**：免费模式（akshare/mock）与增强模式（iFinD，需 `APP_KEY/SECRET`）的切换必须配置化，且 credential 绝不能进代码或落认知层。

本阶段目标定性：

```
定义「真实数据如何进入系统、在哪里归一化成 Observation、provider 边界是什么」（provider contract + ingestion boundary）
    ——而非——
写 iFinD SDK 接口 / 接任何真实数据源（provider implementation）
```

## 3. 决定（Decision）

> 本 ADR 的 D1–D8 是在用户 M3.6 方向指令（authoritative）之上，结合 grounding 出的三处既有代码张力（§2.1–2.4）收敛而成。三处方向性裁决（归一化位置 / 与 M3.2 关系 / 本轮交付物）采用推荐方向：**Provider 吐草稿 + 共享 pipeline 定身份 / 新建 canonical 令 M3.2 转 legacy 渐迁 / 本轮只出 ADR + 设计说明（doc-only）**。

### D1 — 新增 Data Provider Layer，位于 Observation 事实源**上游**，不属于 Market Intelligence / Knowledge Evolution

冻结分层与归属：

```
External Data Sources（iFinD / Wind / akshare / EastMoney / CNInfo / 自建爬虫 …）
        │
        ▼   Data Provider Layer（本 ADR 新增；属 services/market-data，adapter 化）
Provider Adapter（每个数据源一个 adapter：client 取数 + mapper 归一化成 ObservationDraft）
        │
        ▼   Observation ingestion pipeline（共享；定身份 content_hash/logical_key + 写 append-only spine）
Market Data Observation（append-only spine，身份 logical_key+content_hash）
        │
        ▼   ObservationReadPort（截至 knowledge_at 的历史读，ADR 0019 D2）
Knowledge Evolution（ADR 0020）
        │
        ▼
Context Layer（ADR 0019）
```

- **iFinD / Wind / akshare 等一律是 Data Provider**，不属于 Market Intelligence、不属于 Knowledge Evolution。它们只是 Observation 的**外部来源**。
- Data Provider Layer 落在 **`services/market-data`**（Observation Store 的所有者），不新建独立 service——它是 market-data「数据从哪来」的补全，与 M3.2 acquisition 同域。
- **禁止**任何绕过本层的路径：`iFinD → LLM → Knowledge`、`iFinD → AI Summary → Snapshot`。真实数据进入系统的**唯一合法形态**是 `外部源 → Provider Adapter → Observation`。

### D2 — 统一 Observation，而不是统一 Provider（本 ADR 的架构核心）

```
   iFinD ──ifind mapper──┐
 akshare ──akshare mapper─┤
    mock ──mock mapper────┼──► Observation（ShanHai 内部唯一事实契约）
EastMoney ──em mapper─────┤
  crawler ──crawler mapper┘
```

- 外部数据源的**结构可以各不相同**（字段名、粒度、时间语义、错误模式都不同）；但**进入 ShanHai 后必须统一成 `Observation`**。系统内部（Evolution / Context / Decision）**只认 `Observation`**，永不认任何 provider 的 DTO。
- 这样未来 **iFinD 免费额度没了 → 换 Wind / 换 akshare / 自己爬** 时，改动被隔离在 Provider Adapter 层内，`Knowledge / Context / Decision` **零改动**——与 ADR 0019 R1「Context 层对 provider 无感知」同源，本 ADR 把它下推到数据入口。
- **不统一 Provider**：不追求所有 provider 实现同一套「富接口」；只要求所有 provider 的**输出**收敛到同一个 `Observation` 契约。provider 之间能力可以参差（某源只有行情、某源只有公告），经优雅降级表达（沿用 M3.2 `NotImplementedError` 降级精神）。

### D3 — 新 canonical 写侧契约 `ObservationProvider`（解决 `MarketDataProvider` 撞名），M3.2 provider 标 legacy 渐迁

用户 spec 的核心接口命名为 `MarketDataProvider`，但该名已被 legacy Tushare-shaped Protocol 占用（§2.3）。故 canonical 新契约改名 **`ObservationProvider`**（语义更准：它产出 `Observation`，不是"市场数据"泛称）：

```python
# contract sketch —— 非实现（详见 M3.6 设计说明 §2）
class ObservationProvider(Protocol):
    name: str
    def fetch_observations(self, query: DataQuery) -> tuple[ObservationDraft, ...]:
        ...
```

- **`ObservationProvider` 是 M3.6 的 canonical 写侧契约**。它取代（在语义上）用户 spec 里的 `MarketDataProvider`，避免与 legacy 撞名。
- **M3.2 的 `PublicMarketDataProvider` + `acquisition.py` + mapper/fact_mapper 链保留为 legacy 已验证路径，不立即废弃**（R1 收紧）。渐迁纪律：
  1. **M3.6.0 先做 Contract Review**（doc-only），冻结 provider boundary / `ObservationDraft` contract / normalization boundary / migration strategy 四条边界后，再谈写任何 adapter。
  2. 其后各免费源（EastMoney/CNInfo）adapter **逐步迁移**到产出 `ObservationDraft` 走新 ingestion pipeline；`MarketFact`-投影路径与 `Observation`-append 路径并存**仅作为迁移窗口**，不作为终态。
  3. **避免两套 provider 词汇长期并行**：迁移窗口须有明确收敛方向（legacy 路径退役时点另经 Review 定，但方向锁定为「收敛到单一 `ObservationDraft` 输出契约」，不允许无限期双轨）。
  理由：M3.2 已跑通 EastMoney/CNInfo/Tushare + 11 套测试，是「让现实撞模型」的既有成果；强行推倒回归面过大。故 additive 新建 + 有纪律渐迁，而非立即废弃或立即重写。
- legacy `MarketDataProvider` / `FinancialDataProvider` / `AnnouncementDataProvider`（`sync.py` 用）**不动**。

### D4 — 归一化到 Observation 发生在**共享 ingestion pipeline**，provider 只吐 `ObservationDraft`

冻结「谁负责定身份」——这是本 ADR 与「统一 Observation」一致性的关键：

```
Provider Adapter（每源一个）
  fetch_observations(query) → tuple[ObservationDraft, ...]
       ObservationDraft = { subject, fact_type, value, occurred_at?, published_at?, captured_at, source_ref }
       —— provider 只负责「取数 + 把源结构映射成语义草稿」，不算身份、不写库
        │
        ▼
Observation Ingestion Pipeline（共享，唯一一处；M3.6.3）
  1. 归一化/校验草稿（fact_type 合法、subject 已解析、时间戳完整）
  2. 定身份：确定性算 content_hash（对语义值）+ logical_key（对 subject+fact_type+predicate）
  3. 幂等写 append-only spine（沿用 record()/record_many()，(logical_key, content_hash) 去重）
        │
        ▼
Observation（读侧投影经 ObservationReadPort 取回，供 Evolution 消费）
```

- **身份规则（`content_hash` / `logical_key` / 幂等）集中在共享 pipeline 一处**，不散落到 provider。换 provider 不触碰身份逻辑——这正是「统一 Observation 而非统一 Provider」在实现上的落点。
- **`ObservationDraft`（写侧草稿）与 `Observation`（读侧投影）显式区分**：draft 是「provider 给出的语义观测」（无身份），`Observation` 是「进入 spine 后的带身份记录」。二者不合并，避免 provider 被迫承担身份职责（§2.1 张力的解法）。
- provenance 经既有 `SourceRef` 携带（`provider` / `trust_level` / `captured_at` / `hash` 字段已在），**零新造 provenance 词汇**；provider 身份只活在 `SourceRef`，绝不进 Observation 的语义字段（沿用 ADR 0019「禁 `if source == "ifind"`」）。

### D4a — 分工边界：语义映射在 provider 内，定身份在共享层（R1 折入外部 Review 调和）

R1 的外部 Review 主张 `provider → *Record → 共享 Normalizer(Record→Observation)`。本 ADR 明确：该主张与 D4 **不是两条路，而是同一条路的两种命名**——只要把「共享 Normalizer」的职责界定清楚，二者收敛为一。故冻结如下分工（这也是 D4 与「统一 Observation 而非统一 Provider」自洽的唯一解）：

```
                     ┌───────────────── 在 provider adapter 内 ─────────────────┐
外部源原始结构  ──►  mapper（source-specific semantic mapping：懂自己字段名/粒度/时间语义）
   （iFinD 字段 /                                    │
    akshare 列 /                                     ▼
    EastMoney JSON …）              ObservationDraft（source-neutral canonical 草稿，有语义、无身份）
                     └────────────────────────────── │ ──────────────────────────┘
                                                      ▼
                     ┌──────────── 在共享 ingestion pipeline 内（provider 无关）──────────┐
                     │  只做 identity assignment + persistence，绝不感知 provider：      │
                     │    · logical_key      （subject + fact_type + predicate）         │
                     │    · content_hash     （对语义值确定性哈希）                       │
                     │    · captured_at       （knowledge time 归位/校验）               │
                     │    · provenance        （经既有 SourceRef 挂载，不新造词汇）        │
                     │    · persistence       （幂等写 append-only spine）               │
                     └──────────────────────────────────────────────────────────────────┘
```

- **语义映射（source → canonical）必须在 provider 内**：只有 iFinD adapter 懂 iFinD 字段名，只有 akshare adapter 懂 akshare 列名。这一步无法上提到共享层——上提就得写 `if provider == "ifind"` 分支，即 R1 Review 与本 ADR **都反对**的耦合。
- **定身份/落库（canonical → 带身份 Observation）必须在共享层**：`logical_key`/`content_hash`/幂等/provenance 挂载/写 spine 只在 pipeline 一处，换 provider 不触碰。
- **`ObservationDraft` 就是 R1 Review 里「已归一化的 `*Record`」**：Review 的「shared mapper 吃 `*Record`」要成立，`*Record` 到达共享层前必须已是 source-neutral——那正是 `ObservationDraft`。故本 ADR 不采纳「分家族 `*Record` + 共享 Normalizer 做语义映射」的命名（会诱导把语义映射误放共享层），而用「统一 `ObservationDraft` + 共享层只定身份」的命名，把边界钉死在正确位置。
- **共享层禁止感知 provider**：ingestion pipeline 不得出现任何 provider 分支/字段判断（AST 守护，D6 延伸；对齐 ADR 0019「禁 `if source == 'ifind'`」）。

### D5 — `Observation ≈ iFinD 信息模型的稳定子集`，而非 `Observation = iFinD DTO`

冻结 Observation 与 iFinD 的关系，兑现用户「不为兼容免费源重设弱结构，但也不锁死成 iFinD DTO」：

```
iFinD 字段全集（股票行情 / 财务指标 / 研报 / 公告 / 资金流 / 行业分类 …，随版本膨胀）
        │  取其稳定、跨源通用的子集
        ▼
Observation { subject, fact_type, value(object_value), occurred_at?, published_at?, captured_at, source_ref, (身份: logical_key, content_hash) }
```

- Observation 是**信息模型的稳定子集**：只保留跨源通用、语义稳定的字段，不随任一 provider 的字段增减而改。iFinD 独有的富字段若需要，经 `SourceRef.raw_snapshot_ref` 定位或后续 typed detail 承载，**不塞进** Observation 顶层。
- 映射示例（iFinD → Observation，见设计说明 §5）：

  ```
  iFinD:  最新市盈率 PE_TTM = 15.6 @ 2026-07-01（600519）
  ──ifind mapper──►
  ObservationDraft:  subject=SubjectRef(security, 600519)
                     fact_type=financial（predicate="valuation.pe_ttm"）
                     object_value="15.6"
                     captured_at=2026-07-01
                     source_ref=SourceRef(provider="ifind", trust_level=OFFICIAL/COMMERCIAL, ...)
  ```
- **不采纳** `Observation = iFinD DTO`：会让整个系统绑死一个商业源的结构，免费额度断供即全线返工——与「iFinD 是优先源但非系统依赖」直接冲突。

### D6 — Data Provider Boundary（6 条冻结点）

冻结 provider 层的硬边界，防止数据入口侵蚀认知层（AST 校验守护，实现期落地）：

```
1. Provider 只能产生 Observation（经 ObservationDraft → ingestion pipeline）。
2. Provider 不允许产生 Knowledge（不得输出 Belief / KnowledgeObject / KnowledgeRevision / KnowledgeView）。
3. Provider 不允许调用 LLM / ReasoningPort（provider 是取数 + 机械映射，非推理）。
4. Provider 不允许访问 Evolution（不 import market-intelligence 任何概念；禁读/写 EvolutionStore / KnowledgeResolver）。
5. Provider 可替换（同一 ObservationProvider 契约下，iFinD/akshare/mock/crawler 平级互换，换源不影响下游）。
6. Provider credential 必须配置化（APP_KEY/SECRET 等经环境变量注入，绝不硬编码、绝不进 Observation/认知层）。
```

- 定性：**Provider 是「事实的搬运工 + 翻译官」，不是「解释者」**。它把外部结构翻译成 Observation 语义草稿，仅此而已。任何"理解/判断/摘要"都属 Knowledge Evolution（ADR 0020）与 Reasoning Engine（M3.7），不属 provider。
- 边界 4 与既有依赖方向一致：Data Provider 在 `market-data` 内，`market-data` 永不 import `market-intelligence`（ADR 0019 R1-1 铁律）——boundary 4 是该铁律在数据入口的具体化。

### D7 — 配置策略：免费模式默认，增强模式可选，多 provider 留口

```
免费模式（默认）：  SHANHAI_DATA_PROVIDER=akshare   或   =mock
增强模式（可选）：  SHANHAI_DATA_PROVIDER=ifind
                   IFIND_APP_KEY=...      # 经环境注入，credential 配置化（D6-6）
                   IFIND_SECRET=...
多 Provider（未来，留口不实现）：
  providers:
    market:      { primary: ifind, fallback: [akshare] }
    fundamental: { primary: ifind }
    news:        { primary: [ifind, crawler] }
```

- **默认免费**（`akshare` 或 `mock`），保证无 token 也能跑通全链路；`ifind` 是 opt-in 增强，缺 credential 时不启用、不报错阻断（优雅降级）。
- provider 选择是**装配层（application-assembly）关注点**，对认知层不可见——沿用 [factory.py](../../services/market-data/shanhai_market_data/factory.py) 的 `SHANHAI_MARKET_STORE` 风格，新增 provider 装配开关，Context / Evolution 零感知。
- 多 provider（per-capability primary/fallback）**本里程碑只登记方向、不实现**，避免过早引入路由复杂度。

### D8 — 子阶段序列：先 Contract Review，再 Mock，最后 iFinD（R1 重排）

```
M3.6.0 Provider Contract Review  （doc-only）冻结 4 条边界：Provider boundary / ObservationDraft contract
   ↓                              / Normalization boundary / Migration strategy —— 不写代码
M3.6.1 Provider Contract 骨架     observation_provider.py：ObservationProvider / DataQuery / ObservationDraft 契约代码 + 契约测试
   ↓
M3.6.2 MockProvider             确定性 mock adapter，产 ObservationDraft
   ↓
M3.6.3 Observation ingestion    共享 pipeline：定身份 + 幂等写 spine（打通 Mock → Observation → Evolution → Context 全链路）
   ↓
M3.6.4 iFinD Adapter            第一个真实优先 provider（client + mapper + config），可替换
   ↓
M3.6.5 akshare Adapter          免费默认源 adapter
   ↓
M3.7  Reasoning Engine          （ADR 0020 D3：LLM 经 ReasoningPort 进认知）
```

- **M3.6.0 = doc-only Contract Review**（R1 新增）：在写任何契约代码前，先冻结 provider/ObservationDraft/normalization/migration 四条边界。这兑现「先补 ADR / contract review 文档，再进代码」，也把 D3 的渐迁纪律钉死在动 adapter 之前。M3.6.0 须冻结下列 **5 点清单**（R1 明确，本 ADR 已裁定，Contract Review 落文档确认）：
  1. **canonical contract = `ObservationDraft`**：M3.6 唯一 canonical 写侧输出契约是 `ObservationDraft`，**不引入分家族 `*Record`（QuoteRecord/FinancialRecord…）作为 canonical contract**。
  2. **`*Record` 路线与 `ObservationDraft` 的关系**：外部 Review 的「provider 吐 `*Record` → shared Normalizer」若成立，`*Record` 到达共享层前必须已是 source-neutral——那即等价于「分家族命名的 `ObservationDraft`」。故不采纳其分家族命名，统一收敛到单一 `ObservationDraft`（见 D4a）。
  3. **source-specific `*Record` 会致 shared normalizer 耦合**：若 `*Record` 保留 source 专有形状进入共享层，shared normalizer 就被迫写 `if provider == "ifind"` 分支——违反 Boundary「共享层禁感知 provider」（D4a / D6）。这是不采纳分家族路线的硬约束理由。
  4. **`PublicMarketDataProvider` 仅迁移窗口，非未来 provider contract**：M3.2 `PublicMarketDataProvider` 保留为 legacy 迁移窗口（D3），**新增 provider 一律实现 `ObservationProvider`，不得以 `PublicMarketDataProvider` 作为未来新增 provider 的契约**。
  5. **商业 provider 仅可配置 adapter，非系统标准**：iFinD / Wind 等商业源仅作为**可配置接入的 adapter**（`SHANHAI_DATA_PROVIDER=ifind` opt-in，D7），**不成为系统标准/依赖**；免费额度断供即换源，Knowledge/Context/Decision 零改动（D2/D5/D6-5）。
- **先 Mock 再 iFinD** 的理由：现在要验证的是 `真实数据 → Observation → Evolution → Context` 这条**链路**是否成立，**不是** iFinD SDK 能否调通。MockProvider 让链路在无外部依赖、确定性、可测的前提下先跑通；iFinD 只是之后接入的第一个真实 adapter。
- 每个子阶段**单独经 Review Gate** 后开工，不一次性实现。

## 4. 非目标（Non-goals，M3.6 设计阶段全程禁止）

- ❌ 任何实现代码（本 ADR + 设计说明 + M3.6.0 Contract Review 均 doc-only；M3.6.1 契约骨架亦需下一轮 Review 批准后才写）
- ❌ 接 iFinD / Wind / akshare / Tushare Pro 真实 SDK；❌ 申请任何 token（含 iFinD APP_KEY/SECRET）
- ❌ 改 M3.3 的 9 方法 Repository 契约 / 改 `knowledge_observation` schema / 动 legacy `MarketDataProvider`
- ❌ 推倒 M3.2 `PublicMarketDataProvider` / `acquisition.py` / mapper 链（只标 legacy 渐迁，不重写）
- ❌ 让 provider 产 Knowledge / 调 LLM / 访问 Evolution（Data Provider Boundary D6）
- ❌ 冻结 `Observation = iFinD DTO`（只取稳定子集，D5）
- ❌ 实现多 provider 路由（primary/fallback per capability）——本轮只登记方向（D7）
- ❌ 推翻 ADR 0019（deterministic Context / ref-based Snapshot）/ ADR 0020（Evolution 版本链 / LLM 唯一入口）任何冻结点

## 5. 依赖方向（Dependency Direction，冻结，沿用 ADR 0019 R1 / ADR 0020）

```
runtime-kernel ─► reasoning-engine ─► market-intelligence ─► market-data
                                                                  │
                                        Data Provider Layer ◄──────┘（在 market-data 内，Observation 上游）
                                                  │
                            External Data Sources ─┘（iFinD/Wind/akshare/EastMoney/crawler）

# 不变量（本 ADR 新增/强化）
- Data Provider 属 market-data；market-data 永不 import market-intelligence（R1-1 铁律，Boundary D6-4）
- 真实数据唯一合法入口：External Source → Provider Adapter → ObservationDraft → ingestion pipeline → Observation
- 禁 iFinD→LLM→Knowledge / iFinD→AI Summary→Snapshot（D1）
- 归一化/定身份只在共享 ingestion pipeline 一处；provider 不算 content_hash/logical_key（D4）
- 系统内部只认 Observation，不认任何 provider DTO；provider 身份只活在 SourceRef（D2/D4）
- Provider 只产 Observation，不产 Knowledge、不调 LLM、不访问 Evolution（D6-1~4）
- Provider 可替换，换源不影响 Knowledge/Context/Decision（D2/D6-5）
- credential 配置化（环境注入），绝不硬编码、绝不进认知层（D6-6/D7）
- Context / Evolution 对 provider 无感知（沿用 ADR 0019 R1「禁 if source == 'ifind'」）
```

## 6. 暂缓（M3.6 设计阶段不做，留待后续 Stage / ADR）

- iFinD / akshare adapter 的具体实现与 SDK 接入（M3.6.4 / M3.6.5，各经 Review）。
- 共享 ingestion pipeline 的 `content_hash` / `logical_key` **具体算法**（M3.6.3 落地；本 ADR 只冻结「在 pipeline 一处、确定性、幂等」原则）。
- 多 provider 路由（primary/fallback per capability）、provider 健康度/限流/重试策略（未来 Market Data Hub）。
- M3.2 legacy 路径的**退役时点**（`MarketFact`-投影路径何时并入 `Observation`-append 路径，另经 Review）。
- typed detail（financial/quote/announcement 观测明细）如何承载 iFinD 富字段（沿用现有 detail 表投影路径，具体映射后续）。
- Reasoning Engine / LLM 接入（M3.7，ADR 0020 D3）。

## 7. 与既有 ADR 的关系

| ADR | 关系 | 本 ADR 是否要求其改动 |
|-----|------|----------------------|
| 0019（Context Layer） | 兑现其「iFinD 只是 `iFinD Adapter → Observation`」与「Context 对 provider 无感知」；本 ADR 在 Observation 上游落地，不碰 deterministic Context / ref-based Snapshot | 否 |
| 0020（Knowledge Evolution） | 落实其数据接入顺序（`Evolution 设计 → Data Provider → 数据接入`）与 §4「iFinD 属 M3.6」；Provider Boundary 呼应其「LLM 唯一入口=Evolution pipeline」（provider 禁 LLM） | 否 |
| M3.2（Data Acquisition Foundation） | 保留 `PublicMarketDataProvider` + acquisition 链为 legacy 已验证路径，新建 canonical `ObservationProvider` 渐迁（D3） | 否（渐迁另经 Review） |
| 0011（Model Provider） | Provider「只搬运不推理、不直调模型」与「Agent 禁直调模型」同源 | 否 |
| 0009（Local-first 持久化） | 免费模式默认（mock/akshare 无 token 可跑）沿用 local-first 精神（D7） | 否 |

## 原因

- **数据源是插件，不是地基（D1/D2）**：ShanHai 的资产是长期认知，不是某个数据供应商。把 provider 隔离为可替换 adapter、系统内部统一 Observation，才能在换源时保护认知资产不受损。
- **归一化集中（D4）**：身份/幂等/provenance 规则只在一处，才能保证「换 provider 不重写身份」；分散到 provider 会让「统一 Observation」名存实亡。
- **新建 canonical 而非改造（D3）**：M3.2 是已验证的免费路径，推倒重写回归面大、收益低；additive 新建 + 渐迁风险最低，且不破坏 11 套测试。
- **稳定子集而非 DTO（D5）**：既避免为免费源重设弱结构，又不把系统绑死在商业源结构上——两个失败模式都规避。
- **Boundary 冻结（D6）**：数据入口是最容易滑向 `数据源直接驱动 AI` 的地方；6 条硬边界把这条返工路径提前堵死。
- **先 Mock（D8）**：验证链路 ≠ 验证 SDK；Mock 让全链路在确定性、可测、无外部依赖下先跑通，再谈接真实源。

## 影响

- 新增本 ADR（Proposed）+ [M3.6 Data Provider Layer 设计说明](../design/m3.6-data-provider-layer-design.md)（doc-only），**不新增/修改任何代码、schema、依赖**。
- 为 M3.6 实现（M3.6.0 Contract Review → M3.6.5，逐段 Review）冻结 provider 契约、归一化边界、Boundary 6 条、配置策略、Observation-iFinD 关系。
- 不触碰 ADR 0019/0020 已冻结的 Context / Evolution 语义；不动 M3.2 legacy 路径与 legacy `MarketDataProvider`。
- 不触碰本阶段「暂不开发」清单（实时行情页面 / 券商交易 / 自动交易 / 量化 / 回测）。
- 解冻 S4.2/S4.3 的「不接 iFinD/Wind/akshare」阶段禁令——但接入仍受 D6 Boundary 与 D8 顺序（先 Mock）严格约束。

## 备选方案（已考虑）

- **`Observation = iFinD DTO`（以 iFinD 结构为标准）**：绑死商业源，免费额度断供即全线返工，不采纳；改用稳定子集（D5）。
- **归一化在每个 provider 内部（provider 直接产完整 Observation）**：身份逻辑分散、幂等难保、换源即重写，违背「统一 Observation」，不采纳；改用共享 ingestion pipeline 定身份（D4）。
- **provider 吐分家族 `*Record` + 共享 Normalizer 做 `Record → Observation`（R1 外部 Review 主张）**：与本 ADR 承重原则一致，但「共享 Normalizer 做语义映射」的命名会诱导把 source-specific 映射误放共享层（触发 `if provider == "ifind"` 耦合）；且若 `*Record` 已预归一化成 source-neutral，它就等价于 `ObservationDraft`。故不采纳其命名，改用「provider 内做语义映射产 `ObservationDraft` + 共享层只定身份」把边界钉死（D4a）。
- **改造 M3.2 `PublicMarketDataProvider` 成 Observation 契约**：动 EastMoney/CNInfo/Tushare + acquisition 链，回归面大，不采纳；新建 canonical `ObservationProvider` 渐迁（D3）。
- **沿用 `MarketDataProvider` 命名（如用户 spec）**：与 legacy Tushare-shaped Protocol 撞名，不采纳；改名 `ObservationProvider`（D3）。
- **先接 iFinD 再补 Mock**：验证目标错位（验证 SDK 而非链路），且真实源不确定性会污染链路验证，不采纳；先 Mock（D8）。
- **Data Provider 独立成 service**：Observation Store 归 market-data，provider 是其「数据从哪来」的补全，独立 service 会割裂所有权，不采纳；落 market-data 内（D1）。
- **provider 内做 AI 摘要/富化再产 Observation**：即被禁的 `iFinD → AI Summary → Snapshot`，让幻觉从入口进认知，不采纳；Boundary D6-2/D6-3 明令禁止。

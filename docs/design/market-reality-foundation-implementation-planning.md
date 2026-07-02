# Milestone 2: Market Reality Foundation Implementation Planning

> 状态：**Implementation Planning Gate — 不实现代码**。
> 前置：Foundation Phase ✅ Completed；Market Reality Foundation Design Review 已形成初稿。
> 目标：冻结连接真实 A 股数据前的实现边界，包括 Market Entity Model、Data Source Adapter、Ingestion Pipeline、Knowledge Schema、Web Console Alpha。

---

## 0. Gate Position

本阶段结束 Runtime contract 继续扩展。

Milestone 2 不再拆 Runtime PR：

```text
不继续 Runtime 抽象
不实现 PR-4.2 Candidate Provider Adapter
不修改 RuntimeKernel
不修改 Experience Runtime
不实现 Memory / Evolution
不实现交易能力
```

本阶段从“通用 AI Runtime Foundation”切换到“Market Reality Foundation”：

```text
真实 A 股数据
    → Market Entity Model
    → Data Source Adapter
    → Ingestion Pipeline
    → Knowledge Schema
    → Company Intelligence Web Console Alpha
```

当前 Gate 只冻结 implementation planning，不写 `services/market-*` 代码、不建表、不接真实数据源。

---

## 1. Implementation Boundary

### 1.1 Allowed Future Implementation Area

后续如经 Review 批准，Milestone 2 implementation 只允许进入：

```text
services/market-data/
    source registry
    source adapter protocol
    raw capture contract
    parser / normalizer contract

services/market-knowledge/
    market entity models
    knowledge schema
    entity resolver contract
    fact / relation writer contract
    query read service contract

apps/web or apps/console/
    Company Intelligence Web Console Alpha
```

### 1.2 Forbidden Implementation Area

Milestone 2 禁止修改：

```text
services/runtime-kernel/
services/experience-runtime/
services/agent-runtime/ AgentRunner
services/memory/
services/experience-evolution/
services/experience-artifact/
services/feedback/
```

禁止实现：

```text
PR-4.2 Candidate Provider Adapter
RuntimeContext execution flow
Memory persistence / Evolution lifecycle
trading / broker / order / portfolio / backtest
real-time quote streaming
```

### 1.3 Dependency Direction

冻结依赖方向：

```text
market-data
    ↓
market-knowledge
    ↓
web-console read model
```

允许未来只读消费：

```text
Agent Tool → Market Knowledge Service
```

但本阶段不实现 Agent Tool。

禁止：

```text
runtime-kernel → market-data
runtime-kernel → market-knowledge
market-data → runtime-kernel
market-knowledge → runtime-kernel
market-knowledge → memory
market-knowledge → experience-runtime
AgentRunner → market database
```

---

## 2. Frozen Boundary A: Market Entity Model

### 2.1 Core Entity Split

冻结四层身份边界：

```text
Company
    经营/法人主体

ListedEntity
    上市公司披露主体

Security
    可交易证券

Listing
    交易所 / 板块 / 上市生命周期
```

禁止简化为：

```text
Company == stock_code
ListedEntity == Company
Security == Company
```

### 2.2 Minimum Entity Model

首版 Market Entity Model 至少包含：

| Entity | Stable ID Example | Notes |
|---|---|---|
| `Company` | `company:<slug-or-registry-id>` | 法人/经营主体，不等于股票代码。 |
| `ListedEntity` | `listed_entity:<exchange>:<disclosure-code>` | 披露主体，可关联 Company。 |
| `Security` | `security:szse:000001` | 可交易证券，带 exchange namespace。 |
| `Listing` | `listing:szse:main:000001` | 记录上市地点、板块、状态、生命周期。 |
| `Industry` | `industry:<taxonomy>:<code>` | 行业体系必须带 taxonomy。 |
| `Announcement` | `announcement:<source>:<external-id>` | 公告是 evidence document。 |
| `FinancialReport` | `financial_report:<listed_entity>:<period>:<type>` | 报告期对象，不直接覆盖 Company。 |
| `MarketEvent` | `market_event:<source-or-hash>` | 事件需引用 evidence。 |
| `PolicyDocument` | `policy:<issuer>:<external-id>` | 政策/监管文档。 |
| `QuoteSnapshot` | `quote:<source>:<security>:<timestamp>` | 仅事实，不构成交易信号。 |

### 2.3 Relationship Model

关系必须支持：

```text
source_ref
confidence
valid_from / valid_to
observed_at
created_at
```

首版关系：

```text
Company --has_listing_identity--> ListedEntity
ListedEntity --issues_or_maps_to--> Security
Security --listed_on--> Listing
Company --classified_as--> Industry
Company --has_supply_chain_role--> SupplyChainRole
Announcement --mentions/discloses--> ListedEntity / Company / Security
FinancialReport --reports_on--> ListedEntity
MarketEvent --affects--> Company / Security / Industry
PolicyDocument --affects--> Industry / Company
QuoteSnapshot --observes--> Security
```

---

## 3. Frozen Boundary B: Data Source Adapter

### 3.1 Adapter Contract Shape

未来实现时，Source Adapter 只负责 source access：

```text
SourceAdapter
    list(...)
    fetch(...)
    checkpoint(...)
```

输出只能是：

```text
RawMarketDocument
RawMarketSnapshot
```

Adapter 禁止：

```text
entity resolution
knowledge writing
agent reasoning
memory writing
runtime context projection
trading decision
```

### 3.2 Source Registry

每个 source 必须注册：

```text
source_id
source_name
source_type
trust_level
license_notes
rate_limit
freshness_expectation
historical_coverage
identifier_scheme
failure_mode
```

### 3.3 First Source Priority

Implementation planning 推荐首批只选公开、可追溯、非交易执行源：

1. 官方公告 / 披露源：巨潮资讯、交易所公告。
2. 公司/证券元数据源：交易所列表、公开公司资料。
3. 日线级行情源：仅用于事实对齐，不做实时交易。

不建议首批接：

```text
分钟行情
Level-2 行情
券商账户
第三方闭源付费源
新闻实时流
```

---

## 4. Frozen Boundary C: Ingestion Pipeline

### 4.1 Pipeline Contract

冻结最小 pipeline：

```text
SourceAdapter
    → Raw Capture
    → Parser
    → Normalizer
    → Entity Resolver
    → Quality Gate
    → Knowledge Writer
    → Read Model Builder
```

### 4.2 Stage Inputs / Outputs

| Stage | Input | Output | Must Preserve |
|---|---|---|---|
| Raw Capture | source response | `RawMarketDocument` / `RawMarketSnapshot` | source metadata, checksum, captured_at |
| Parser | raw object | parsed payload | parser_version, parse diagnostics |
| Normalizer | parsed payload | normalized fact candidates | units, dates, code namespace |
| Entity Resolver | normalized candidates | entity refs / unresolved refs | resolver_version, match confidence |
| Quality Gate | fact candidates | accepted / rejected facts | validation errors, conflict markers |
| Knowledge Writer | accepted facts | facts / relations / evidence links | source_ref lineage |
| Read Model Builder | knowledge store | company intelligence view | derivation version |

### 4.3 Append-Only Raw Rule

冻结：

```text
raw capture is append-only
normalization is reproducible
read model is disposable
```

不允许：

```text
覆盖 raw document
无 source_ref 写入 fact
无 parser_version 写入 normalized output
以 read model 作为事实真源
```

### 4.4 Batch First

首版 implementation 只允许 batch / replay：

```text
historical backfill
daily batch
manual on-demand refresh
```

不允许：

```text
real-time streaming
intraday signal engine
trade execution trigger
```

---

## 5. Frozen Boundary D: Knowledge Schema

### 5.1 Layered Knowledge Model

冻结四层知识存储语义：

```text
Raw Evidence
    原文、快照、checksum、source metadata

Normalized Facts
    标准化事实候选、单位、时间、source_ref

Knowledge Entities / Relations
    Company / Security / Industry / Event / Policy 及关系

Derived Read Models
    Console 查询视图、公司画像摘要、质量面板
```

### 5.2 Logical Tables / Collections

首版 schema planning 至少覆盖：

```text
market_sources
market_raw_documents
market_raw_snapshots
market_entities
market_relations
market_facts
market_events
market_entity_aliases
market_entity_external_ids
company_intelligence_views
ingestion_runs
ingestion_errors
```

### 5.3 Time Fields

所有事实类对象必须区分：

```text
occurred_at
published_at
captured_at
observed_at
valid_from / valid_to
```

字段可为空，但语义不能合并为单一 `timestamp`。

### 5.4 Knowledge Boundary

市场事实属于 Market Knowledge，不属于：

```text
ExperienceEvent
MemoryRecord
RuntimeContext top-level field
ExperienceArtifact
```

未来 Agent 读取市场知识时，路径必须是：

```text
Agent → Tool → Market Knowledge Service → Knowledge Storage
```

---

## 6. Frozen Boundary E: Web Console Alpha

### 6.1 Console Purpose

Company Intelligence Web Console Alpha 只验证认知基础：

```text
公司身份是否正确
证券/上市关系是否正确
公告/财报/事件证据是否可追溯
行业/产业链关系是否可 review
数据质量和冲突是否可见
```

### 6.2 Alpha Screens

冻结 Alpha 最小页面：

```text
Company Search
Company Profile
Evidence Timeline
Knowledge Relations
Source / Quality Panel
```

### 6.3 Console Non-Features

禁止：

```text
交易下单
持仓管理
实时盘口
分钟级行情
策略推荐
自动买卖建议
收益回测
个股评级
```

Console 只读：

```text
Web Console → Market Knowledge API / Service → Derived Read Model
```

不得调用：

```text
RuntimeKernel
AgentRunner
Experience Runtime
Memory
Experience Evolution
```

---

## 7. Proposed Implementation Slices

后续若获批准，建议按以下 slice 实现，每个 slice 单独 Review：

### M2.1 Market Entity Schema

只实现：

```text
market entity pydantic models
identity / external_id / relation value objects
schema contract tests
```

不实现：

```text
source adapter
database persistence
web console
agent integration
```

### M2.2 Source Registry + Raw Capture Contract

只实现：

```text
SourceRegistry
SourceAdapter Protocol
RawMarketDocument / RawMarketSnapshot
in-memory raw capture for tests
```

不实现：

```text
real source crawling
parser
knowledge writer
```

### M2.3 First Public Source Adapter

只实现一个公开源 adapter，建议优先官方公告 / 披露源。

不实现：

```text
multiple source aggregation
quote streaming
trading data
```

### M2.4 Ingestion Pipeline Skeleton

只实现 pipeline interfaces 和 deterministic fixture。

不实现：

```text
LLM extraction
auto entity merge
production scheduler
```

### M2.5 Knowledge Store Alpha

只实现 local-first storage / query。

不实现：

```text
Vector DB
Graph DB
Memory persistence
Experience projection
```

### M2.6 Web Console Alpha

只实现只读公司画像页面。

不实现：

```text
Agent execution
trading workflow
recommendation engine
```

---

## 8. Required Contract Tests

进入 implementation 后，必须先加边界测试：

```text
market entity identity does not collapse Company/Security/Listing
source adapter cannot write knowledge
raw capture is append-only
facts require source_ref
knowledge schema separates raw/fact/entity/read_model
web console does not import runtime-kernel / agent-runtime / memory / experience-runtime
market packages do not import runtime-kernel
```

---

## 9. Final Planning Decision

冻结：

```text
Market Entity Model
Data Source Adapter
Ingestion Pipeline
Knowledge Schema
Web Console Alpha
```

保持禁止：

```text
Runtime contract continuation
PR-4.2 Adapter implementation
RuntimeKernel / Experience Runtime modification
Memory / Evolution implementation
Trading capability
```

当前状态：

```text
Milestone 2 Market Reality Foundation
    ✅ Implementation Planning Gate completed
    🔓 Data Foundation MVP Phase 1 approved for implementation

Approved scope:
    market-data service
    Tushare Provider
    Entity Schema MVP
    10 A-share company sync
    minimal Knowledge Store
    Company Intelligence API
```

仍禁止：

```text
RuntimeKernel / Experience Runtime / RuntimeContext modification
PR-4.2 Adapter implementation
Memory Evolution
Trading strategy / broker execution
```

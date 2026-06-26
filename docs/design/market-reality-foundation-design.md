# Milestone 2: Market Reality Foundation Design

> 状态：**Design Review Gate — 不实现代码**。
> 前置：Foundation Phase — Runtime / Experience Contract Foundation ✅ Completed。
> 目标：用真实中国资本市场数据验证 ShanHai 架构，建立 Market Reality Foundation 的设计边界。

---

## 0. Position

Foundation Phase 已完成的是 AI Runtime / Experience Runtime 的通用基础：

```text
Runtime Kernel
RuntimeContext v1
RunStore Identity
Experience Runtime Contract
```

Milestone 2 不继续抽象 Runtime，也不实现 PR-4.2 Adapter。

Milestone 2 的关注点是：

```text
真实中国资本市场数据
        ↓
市场实体建模
        ↓
数据源接入架构
        ↓
摄取与标准化管线
        ↓
知识存储模型
        ↓
公司智能 Web Console Alpha
```

它是 Market Reality validation layer，不是交易系统。

---

## 1. Design Goals

本阶段用真实 A 股市场数据验证以下架构假设：

1. ShanHai 的知识优先路线能否承载真实市场实体复杂性。
2. 当前 Wiki / Knowledge / Experience 分层是否足以表达公司、证券、行业、公告、政策、事件之间的关系。
3. 数据源接入是否可以保持 source adapter 独立，不污染 Agent / Runtime / Memory。
4. 摄取管线是否可以保留 raw evidence、lineage、时间语义和可重放能力。
5. Web Console 是否能作为认知验证界面，而不是行情软件或交易入口。

---

## 2. Non-Goals

本 Milestone 明确禁止：

```text
继续 Runtime 抽象
实现 PR-4.2 Candidate Provider Adapter
实现 Memory / Evolution
实现交易能力
实现券商接口
实现自动交易 Agent
实现实时行情系统
实现回测系统
```

同时禁止把市场语义塞入：

```text
RuntimeKernel
RuntimeContext top-level schema
AgentRunner
MemoryService
ExperienceArtifact implementation
```

市场能力必须作为 domain data / knowledge capability 存在。

---

## 3. Scope

Milestone 2 Design Review 覆盖五个设计问题：

| Area | Question |
|---|---|
| Market Entity Model | 中国资本市场实体如何建模，避免把公司、股票、上市主体混为一谈？ |
| Data Source Architecture | 真实数据源如何接入、审计、替换和分级？ |
| Ingestion Pipeline | 原始数据如何进入系统并编译为可用知识？ |
| Knowledge Storage Model | Raw / Normalized / Knowledge / Derived View 如何分层存储？ |
| Company Intelligence Web Console Alpha | Alpha Console 展示什么，明确不展示什么？ |

---

## 4. Market Entity Model

### 4.1 Core Principle

A 股现实中：

```text
Company ≠ ListedCompany ≠ Security ≠ StockCode
```

错误建模：

```text
Company(id="000001")
```

推荐建模：

```text
Company
    legal entity / operating entity

ListedEntity
    listed company identity

Security
    tradable instrument

Listing
    exchange + board + code + lifecycle
```

原因：

- 公司可能更名。
- 股票代码可能承载上市证券身份，不等同法人主体。
- 同一集团可能有多个上市平台。
- A/H/B 股、可转债、退市整理、ST 状态均不能简化为公司字段。
- 行业分类存在多套体系：证监会行业、申万行业、中信行业、自定义产业链。

### 4.2 Entity Set

Milestone 2 需要冻结的最小实体集合：

| Entity | Meaning | Example Fields |
|---|---|---|
| `Company` | 经营/法人主体 | company_id, name, aliases, unified_social_credit_code, region |
| `ListedEntity` | 上市公司身份 | listed_entity_id, company_id, listing_name, disclosure_name |
| `Security` | 可交易证券 | security_id, security_type, code, name, currency |
| `Listing` | 上市场所与生命周期 | exchange, board, listed_at, delisted_at, status |
| `Industry` | 行业分类节点 | taxonomy, level, code, name |
| `SupplyChainRole` | 产业链位置 | chain, segment, role, confidence |
| `Announcement` | 公告文档 | title, source, published_at, doc_type, raw_ref |
| `FinancialReport` | 财报报告期对象 | period, report_type, published_at, source_ref |
| `MarketEvent` | 市场/公司事件 | event_type, occurred_at, affected_entities, evidence_refs |
| `PolicyDocument` | 政策/监管文档 | issuer, published_at, scope, evidence_refs |
| `TradingCalendar` | 交易日历 | exchange, trade_date, is_open |
| `QuoteSnapshot` | 行情快照 | security_id, timestamp, price fields, source_ref |

### 4.3 Relationship Set

最小关系集合：

```text
Company -> ListedEntity
ListedEntity -> Security
Security -> Listing
Company -> Industry
Company -> SupplyChainRole
Announcement -> Company / ListedEntity / Security
FinancialReport -> Company / ListedEntity
MarketEvent -> Company / Security / Industry / PolicyDocument
PolicyDocument -> Industry / Company / MarketEvent
QuoteSnapshot -> Security
```

关系必须支持：

- `valid_from / valid_to`：现实关系的有效期。
- `observed_at`：系统观察到该事实的时间。
- `source_ref`：证据来源。
- `confidence`：结构化抽取或来源可信度。

### 4.4 Identity Rule

冻结原则：

```text
stable identity belongs to ShanHai entity id
source identity remains as source-specific external id
```

示例：

```text
company_id = "company:ping-an-bank"
security_id = "security:szse:000001"
source_ref = "cninfo:announcement:<doc_id>"
```

不得把外部代码直接作为全局实体 id，除非加 source / exchange namespace。

---

## 5. Data Source Architecture

### 5.1 Source Categories

Milestone 2 应优先验证公开、可追溯、可重复获取的数据：

| Category | Candidate Sources | Primary Use |
|---|---|---|
| Exchange / disclosure | 巨潮资讯、上交所、深交所、北交所 | 公告、定期报告、监管问询 |
| Regulator / policy | 证监会、交易所监管、财政部、央行、发改委 | 政策与监管事件 |
| Company metadata | 交易所列表、公开公司资料、公告抽取 | 公司/证券/上市状态 |
| Industry taxonomy | 证监会行业、申万行业、中信行业（按可得性） | 行业分类与对比 |
| Market quotes | 日线/分钟线数据源（仅验证，不做实时） | 价格事实与事件对齐 |
| News / event source | 公开新闻源、公告事件抽取 | 事件识别与证据链 |

注意：具体第三方数据源需单独检查授权、频率限制、稳定性和可商用范围。

### 5.2 Source Adapter Boundary

推荐架构：

```text
SourceAdapter
        ↓
RawMarketDocument / RawMarketSnapshot
        ↓
Ingestion Pipeline
```

`SourceAdapter` 只负责：

```text
fetch / list / download / checkpoint
```

不负责：

```text
entity resolution
knowledge graph writing
agent reasoning
runtime context projection
trading decision
```

### 5.3 Source Registry

每个数据源必须登记：

```text
source_id
source_name
source_type
license_notes
rate_limit
freshness_expectation
historical_coverage
identifier_scheme
failure_mode
trust_level
```

这样才能区分：

- 官方披露源。
- 第三方聚合源。
- 网页抓取源。
- 人工导入源。

### 5.4 Source Trust Policy

来源可信度建议分级：

| Level | Meaning |
|---|---|
| L1 Official | 交易所 / 监管 / 公司公告原文 |
| L2 Licensed Aggregator | 有授权或稳定协议的聚合数据 |
| L3 Public Aggregator | 公开网页 / 社区数据源 |
| L4 Derived | ShanHai 解析、抽取、推理或人工标注结果 |

Knowledge 写入时必须保留 source trust，不允许把 L4 派生结论伪装成 L1 事实。

---

## 6. Ingestion Pipeline

### 6.1 Pipeline Shape

推荐最小管线：

```text
SourceAdapter
        ↓
Raw Capture
        ↓
Parser
        ↓
Normalizer
        ↓
Entity Resolver
        ↓
Quality Gate
        ↓
Knowledge Writer
        ↓
Company Intelligence View
```

### 6.2 Stage Responsibilities

| Stage | Responsibility | Forbidden |
|---|---|---|
| Raw Capture | 保存原始文档/快照、source metadata、checksum | 不抽取实体、不覆盖旧 raw |
| Parser | 从 HTML/PDF/JSON/CSV 提取结构化 payload | 不做跨源合并 |
| Normalizer | 单位、日期、代码、字段命名标准化 | 不创造业务结论 |
| Entity Resolver | 匹配 Company / Security / Industry identity | 不写 RuntimeContext |
| Quality Gate | 校验完整性、重复、冲突、来源等级 | 不自动学习权重 |
| Knowledge Writer | 写入 normalized facts / relations / evidence links | 不调用 AgentRunner |
| Company View Builder | 生成 Console 可读视图 | 不改变事实源 |

### 6.3 Raw Evidence Rule

冻结原则：

```text
raw input is append-only evidence
normalized fact is reproducible projection
knowledge view is derived read model
```

任何从真实市场数据得出的知识都必须能追溯到：

```text
source_id
source_url / source_external_id
captured_at
checksum
parser_version
normalizer_version
entity_resolution_version
```

### 6.4 Time Semantics

中国资本市场数据至少需要三种时间：

| Time | Meaning |
|---|---|
| `occurred_at` | 事件实际发生时间 |
| `published_at` | 市场可见时间 / 公告披露时间 |
| `captured_at` | ShanHai 捕获时间 |

禁止只保存一个 `timestamp`。

### 6.5 Batch First

Milestone 2 建议只冻结 batch ingestion：

```text
daily / on-demand / historical replay
```

不冻结：

```text
real-time quote streaming
intraday trading signal
broker execution loop
```

原因：本阶段验证知识与实体建模，不验证低延迟执行。

---

## 7. Knowledge Storage Model

### 7.1 Layered Storage

推荐四层：

```text
Raw Evidence Store
        ↓
Normalized Fact Store
        ↓
Knowledge Graph / Entity Store
        ↓
Derived Read Models
```

### 7.2 Ownership

| Layer | Owns | Does Not Own |
|---|---|---|
| Raw Evidence Store | 原文、快照、checksum、source metadata | 业务实体最终身份 |
| Normalized Fact Store | 标准字段事实、单位、报告期、来源引用 | 推理结论 |
| Knowledge Graph / Entity Store | Company / Security / Industry / Event / Relation | Raw document content |
| Derived Read Models | Console 查询视图、公司画像摘要 | 事实真源 |

### 7.3 Storage Shape

本 Design Gate 不选具体数据库实现，但冻结逻辑模型：

```text
market_raw_documents
market_raw_snapshots
market_sources
market_entities
market_relations
market_facts
market_events
company_intelligence_views
```

若进入实现，建议 local-first：

```text
SQLite / Postgres-compatible schema first
Object storage optional for large raw documents
Vector / Graph DB postponed
```

### 7.4 Knowledge vs Memory vs Experience

必须保持：

```text
Market Knowledge
        = world facts about companies / securities / industries / policies / events

Memory
        = agent runtime access interface

Experience
        = run/evaluation-derived lessons and reusable artifacts
```

禁止：

```text
把市场事实写入 ExperienceEvent
把公司画像写入 RuntimeContext 顶层字段
把行情快照写入 MemoryService 私有存储
让 Agent 直接访问 market database
```

Agent 未来访问路径仍应是：

```text
Agent
  → Tool
  → Market / Knowledge Service
  → Storage
```

---

## 8. Company Intelligence Web Console Alpha

### 8.1 Purpose

Alpha Console 是 Market Reality Foundation 的验证界面。

它验证：

- 实体模型是否能解释真实公司。
- 数据源是否可追溯。
- 公告 / 财报 / 行业 / 事件是否能聚合成公司视图。
- 知识图谱关系是否能被人 review。
- ShanHai 是否真的在积累“认知资产”，而非只展示行情。

### 8.2 Minimum Screens

Design scope 建议冻结五个页面：

| Screen | Purpose |
|---|---|
| Company Search | 按公司名、证券代码、别名搜索 |
| Company Profile | 展示公司主体、上市证券、行业、上市状态 |
| Evidence Timeline | 公告、财报、政策、事件按时间线展示 |
| Knowledge Relations | 公司—行业—政策—事件—产业链关系 |
| Source / Quality Panel | 展示来源、更新时间、冲突、可信度 |

### 8.3 Explicit Non-Features

Alpha Console 不做：

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

允许展示：

```text
事实
证据
关系
来源
冲突
数据质量
```

不允许输出：

```text
buy / sell / hold instruction
broker action
position sizing
```

### 8.4 Console Boundary

Console 调用链应保持：

```text
Web Console
        ↓
Market Knowledge API / Service
        ↓
Knowledge Storage
```

禁止：

```text
Web Console
        ↓
AgentRunner / RuntimeKernel / Memory / ExperienceEvolution
```

Milestone 2 Alpha 先验证 read model，不触发 Agent 执行。

---

## 9. Dependency Boundary

推荐未来包边界：

```text
services/market-data
    source adapters / raw capture / parsers

services/market-knowledge
    entity model / resolver / fact writer / query service

apps/web or apps/console
    Company Intelligence Console Alpha
```

禁止依赖方向：

```text
market-data -> agent-runtime
market-data -> runtime-kernel
market-knowledge -> runtime-kernel
market-knowledge -> memory
market-knowledge -> experience-evolution
runtime-kernel -> market-data
AgentRunner -> market database
```

允许未来只读方向：

```text
Agent Tool -> Market Knowledge Service
Memory Knowledge Adapter -> Knowledge Service read interface
Runtime environment_context <- domain provider projection
```

但这些不在 Milestone 2 Design Gate 实现。

---

## 10. Review Questions

进入实现前必须回答：

1. 最小真实数据集选哪一组公司 / 行业 / 时间窗口？
2. 第一批 source adapter 选择官方公告源还是行情/公司元数据源？
3. 是否将 `Company / ListedEntity / Security / Listing` 四层作为硬边界？
4. Knowledge Storage 首版是否采用 SQLite/Postgres-compatible relational model，而不是 Graph DB？
5. Console Alpha 是否只读，不触发 Agent / Runtime？
6. 是否需要单独 ADR 固化 Market Entity Model？
7. 第三方数据源授权和频率限制如何记录到 Source Registry？

---

## 11. Recommended Milestone 2 Plan

建议 Milestone 2 拆成 Review-first 的子阶段：

```text
M2.1 Market Entity Model Review
M2.2 Data Source Registry + Adapter Boundary Review
M2.3 Ingestion Pipeline Review
M2.4 Knowledge Storage Model Review
M2.5 Company Intelligence Console Alpha Review
```

每个子阶段先 design review，再决定是否 implementation。

---

## 12. Final Decision

当前结论：

```text
Milestone 2: Market Reality Foundation Review
        ✅ Design Review Completed
        🔓 M2 Data Foundation MVP Phase 1 approved for implementation
```

已解冻的实现范围仅限：

```text
market-data service
Tushare Provider
Market Entity Schema MVP
贵州茅台 / 宁德时代等 10 家公司数据同步
最小 Knowledge Store
Company Intelligence API
```

不得进入：

```text
Runtime abstraction continuation
PR-4.2 Adapter implementation
Memory / Evolution implementation
Trading capability
RuntimeKernel / Experience Runtime / RuntimeContext modification
```

# Milestone 2.3: Market Knowledge Expansion Review

> 状态：**Design Review Gate — 不实现代码**。
> 前置：M2.2 Market Data Runtime MVP ✅ Completed。
> 目标：让 ShanHai 从“知道公司存在”进入“理解公司发生了什么”，冻结 Market Knowledge Layer 的核心事实模型。

---

## 0. Stage Position

当前阶段重新定位为：

```text
AI Native Capital Market Cognition Foundation
```

已完成：

```text
PR-1 Runtime Kernel Foundation        ✅
PR-2 RuntimeContext v1                ✅
PR-3 Run Identity Migration           ✅
PR-4.1 Experience Contract            ✅
M2.1 Market Entity Model              ✅
M2.2 Market Data Runtime MVP          ✅
```

M2.3 不继续 Runtime，不实现 PR-4.2 Experience adapter。

M2.3 的核心问题是：

```text
QuoteSnapshot / Company metadata
        ↓
MarketFact schema v1
        ↓
FinancialFact / AnnouncementFact / NewsFact
        ↓
Entity linking
        ↓
Company facts timeline
        ↓
Company Intelligence read model
```

---

## 1. Goals

M2.3 Design Review 需要冻结：

1. `MarketFact` schema v1。
2. `FinancialFact` 边界。
3. `AnnouncementFact` 边界。
4. `NewsFact` 边界。
5. Entity linking strategy。
6. Timeline model。
7. Company Intelligence Console 对 fact timeline 的只读展示边界。

---

## 2. Non-Goals

本阶段禁止：

```text
写 M2.3 实现代码
继续 Runtime 抽象
实现 PR-4.2 Candidate Provider Adapter
修改 RuntimeKernel
修改 RuntimeContext
修改 Experience Runtime
修改 AgentRunner
实现 Memory Evolution
实现 Trading Strategy
接券商 / 下单 / 持仓 / 回测
做新闻 NLP 自动抽取
做 AI Summary 真实生成
```

M2.3 是 Market Knowledge Layer 的 Design Gate，不是交易系统，也不是 Agent 执行系统。

---

## 3. MarketFact Schema v1

### 3.1 Core Principle

`MarketFact` 是 ShanHai 对资本市场世界的最小认知单元。

它不是：

```text
一条行情记录
一个 UI 卡片
一次 Agent 记忆
一个 ExperienceArtifact
```

它应该表达：

```text
某个主体
在某个时间
发生或披露了某个可追溯事实
该事实来自某个证据源
并带有置信度、来源等级、时间语义和实体链接
```

### 3.2 Proposed Base Shape

```text
MarketFact
    fact_id
    fact_type
    subject_ref
    predicate
    object_value
    object_ref
    occurred_at
    published_at
    captured_at
    source_ref
    evidence_refs
    confidence
    entity_links
    attributes
    schema_version
```

### 3.3 Required Semantics

| Field | Meaning |
|---|---|
| `fact_id` | ShanHai stable fact id，可由 source + subject + predicate + time + hash 生成。 |
| `fact_type` | `QUOTE` / `FINANCIAL` / `ANNOUNCEMENT` / `NEWS` / `POLICY` / `ANOMALY` 等。 |
| `subject_ref` | 事实主体，通常指向 Company / ListedEntity / Security / Industry。 |
| `predicate` | 事实谓词，如 `reported_revenue`, `announced_dividend`, `price_changed`。 |
| `object_value` | 字面值或结构化值，如金额、比例、文本摘要。 |
| `object_ref` | 可选，被指向的实体，如 Industry / PolicyDocument / Institution。 |
| `occurred_at` | 事件实际发生时间，可空。 |
| `published_at` | 市场可见时间 / 披露时间。 |
| `captured_at` | ShanHai 捕获时间。 |
| `source_ref` | 事实来源，不允许为空。 |
| `evidence_refs` | 原始公告、财报、网页、行情记录等证据引用。 |
| `confidence` | 来源或抽取置信度。官方结构化源可接近 1.0，NLP 抽取需更低。 |
| `entity_links` | fact 关联到的实体链接及匹配原因。 |
| `attributes` | 保留 domain-specific payload，不能替代顶层语义字段。 |
| `schema_version` | 首版建议 `market_fact.v1`。 |

### 3.4 Fact Type Taxonomy

首版建议冻结：

```text
QUOTE
FINANCIAL
ANNOUNCEMENT
NEWS
INDUSTRY
POLICY
ANOMALY
CAPITAL_FLOW
SHAREHOLDER
```

其中 M2.3 implementation 第一优先不是 News，而是结构化事实：

```text
FINANCIAL
SHAREHOLDER
CAPITAL_FLOW
INDUSTRY
ANNOUNCEMENT
```

---

## 4. FinancialFact

### 4.1 Scope

`FinancialFact` 来自结构化财务数据或公告财报抽取。

第一优先数据源仍建议 Tushare：

```text
income
balancesheet
cashflow
financial_indicator
```

### 4.2 FinancialFact Shape

```text
FinancialFact extends MarketFact
    report_period
    report_type
    metric_name
    metric_value
    unit
    currency
    yoy
    qoq
    restated
```

示例：

```text
type: FINANCIAL
subject: security:cn-a:600519.sh
predicate: reported_revenue
object_value: 2026 Q1 revenue increase
published_at: 2026-04-28
source: announcement / tushare
confidence: 0.98
```

### 4.3 Boundary

FinancialFact 不负责：

```text
估值模型
买卖建议
盈利预测
AI 结论
```

它只表达已披露或结构化来源中的事实。

---

## 5. AnnouncementFact

### 5.1 Scope

公告优先级高于新闻。

候选来源：

```text
巨潮资讯
上交所
深交所
北交所
```

### 5.2 AnnouncementFact Shape

```text
AnnouncementFact extends MarketFact
    announcement_id
    announcement_type
    title
    published_at
    document_url
    document_hash
    extracted_summary
    mentioned_entities
```

### 5.3 Announcement Type

首版建议：

```text
PERIODIC_REPORT
EARNINGS_PREVIEW
DIVIDEND
MAJOR_CONTRACT
MERGER_ACQUISITION
REGULATORY_INQUIRY
RISK_WARNING
SHAREHOLDER_CHANGE
OTHER
```

### 5.4 Boundary

AnnouncementFact 可以存：

```text
公告原文引用
标题
公告类型
披露时间
主体实体链接
抽取摘要
置信度
```

不存：

```text
投资评级
交易建议
未经证据支持的 AI 推论
```

---

## 6. NewsFact

### 6.1 Scope

NewsFact 后置于公告和结构化数据。

原因：

```text
新闻需要 NLP
新闻来源可信度差异大
新闻实体链接容易误判
同一新闻可能是二次传播
```

### 6.2 NewsFact Shape

```text
NewsFact extends MarketFact
    news_id
    title
    publisher
    author
    url
    published_at
    extracted_claims
    sentiment
    mentioned_entities
```

### 6.3 Boundary

NewsFact 初期应只做：

```text
来源登记
标题 / 正文引用
实体链接候选
人工或规则确认后的 claim
```

禁止初期直接做：

```text
自动交易信号
未验证情绪分数
新闻驱动策略
LLM 自动事实入库且无 evidence
```

---

## 7. Entity Linking Strategy

### 7.1 Principle

Entity linking 必须保留匹配过程，而不是只保留最终实体。

```text
mention
    ↓
candidate entities
    ↓
resolver decision
    ↓
confidence + reason
```

### 7.2 Link Shape

```text
EntityLink
    mention_text
    entity_id
    entity_type
    resolver
    confidence
    reason
    source_span
```

### 7.3 Resolver Priority

推荐优先级：

1. Exact `ts_code` / exchange code。
2. Official disclosure name。
3. Known alias。
4. Industry taxonomy code。
5. NLP mention matching。

### 7.4 Ambiguity Rule

如果实体链接置信度不足：

```text
写 unresolved mention
不强行绑定 Company
不进入高置信 MarketFact
```

---

## 8. Timeline Model

### 8.1 Purpose

Company Intelligence 不应只是：

```text
company name
latest price
industry
```

而应是：

```text
Company
    ↓
Facts Timeline
    ↓
Financial / Announcement / Quote / Industry / Policy / News
```

### 8.2 Timeline Event Shape

```text
CompanyTimelineEvent
    event_id
    company_id
    event_time
    event_time_type
    fact_refs
    title
    summary
    event_type
    source_refs
    confidence
```

### 8.3 Time Ordering

Timeline 默认按 `published_at` 排序。

可切换：

```text
occurred_at
published_at
captured_at
```

禁止只保留单一 `timestamp`。

### 8.4 Read Model Boundary

Timeline 是 read model：

```text
MarketFacts
    ↓
CompanyTimelineEvent
```

不是事实真源。

---

## 9. Company Intelligence Console Direction

Console Alpha 页面建议从：

```text
/console/companies
```

演进到：

```text
/companies/600519.SH
```

页面结构：

```text
贵州茅台

Entity
    基本信息
    Company / ListedEntity / Security / Listing

Market Facts
    财务
    公告
    行情
    行业

Timeline
    2026-06-01 公告
    2026-06-10 股价异动
    2026-06-15 行业事件

AI Summary
    当前市场认知
```

M2.3 Review 只冻结结构，不实现 UI。

---

## 10. Recommended Implementation Order After Review

如果 M2.3 Review 通过，建议后续实现顺序：

```text
M2.3.1 MarketFact schema v1
M2.3.2 FinancialFact from Tushare structured APIs
M2.3.3 EntityLink model + resolver audit trail
M2.3.4 CompanyTimeline read model
M2.3.5 AnnouncementFact design-to-implementation gate
```

不要优先接新闻。

第二数据能力优先级：

```text
1. Tushare structured financial / shareholder / moneyflow / industry / concept
2. Official announcement providers
3. News providers
```

---

## 11. Final Decision

当前状态：

```text
Milestone 2.3 Market Knowledge Expansion
    ⏳ Design Review Gate
    ❌ Not approved for implementation
```

冻结目标：

```text
MarketFact schema v1
FinancialFact
AnnouncementFact
NewsFact
Entity linking strategy
Timeline model
```

继续禁止：

```text
RuntimeKernel / RuntimeContext / Experience Runtime / AgentRunner modification
PR-4.2 Candidate Provider Adapter implementation
Memory Evolution
Trading Strategy
```

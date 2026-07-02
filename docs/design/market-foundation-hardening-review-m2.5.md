# Milestone 2.5: Market Foundation Hardening Review

> 阶段定位：暂停 PR-4.2 / Experience Runtime 扩展，进入「真实数据撞模型」后的修正阶段。
> 本文件只做 **Design Review + Migration Plan + Implementation Plan**，**不写实现代码**。
> 触发来源：2026-06-26 Market Data MVP（commit `50073f4`）接入真实 A 股数据后，
> 暴露 Entity Identity / Storage source-of-truth / Fact schema 三处地基问题。

---

## 0. 状态与边界

```
Gate 类型：Design Review only
代码改动：❌ 本阶段不写实现
允许产出：本设计文档 + PROJECT_STATE 更新
```

禁止范围（本阶段不触碰）：

- ❌ 不继续 Experience Runtime（PR-4.1 契约层冻结，不删除）
- ❌ 不实现 PR-4.2 Candidate Provider Adapter
- ❌ 不接 Memory / Evolution / Feedback
- ❌ 不接 Trading Strategy
- ❌ 不修改 RuntimeKernel / RuntimeContext / AgentRunner

核心原则（本阶段的两条铁律）：

1. **外部代码（ts_code / symbol）永远是 attribute，不是 identity。**
2. **数据库是 source of truth，cache 是 decorator，不是 Repository 的父类。**

---

## 1. 问题确认（Design Review）

### P0-1　Entity Identity 与 ts_code 同构（假四层）

现状 [identity.py](../../services/market-data/shanhai_market_data/identity.py)：

```python
company_id        = f"company:cn-a:{ts_code.lower()}"
listed_entity_id  = f"listed_entity:cn-a:{ts_code.lower()}"
security_id       = f"security:cn-a:{ts_code.lower()}"
listing_id        = f"listing:cn-a:{ts_code.lower()}"
```

四个 ID 都是 `f(ts_code)`，四层结构在身份上塌缩成一层。

未来必爆场景（A+H 双重上市）：

```
比亚迪 BYD Co Ltd
   ├── Security 002594.SZ   → 当前生成 company:cn-a:002594.sz
   └── Security 1211.HK     → 当前生成 company:cn-a:1211.hk
```

同一家公司被拆成两个 `company_id`，导致 AI 把「A 股上涨 + 港股上涨」当成两家企业的两个事件，污染新闻聚合 / 财报分析 / 舆情 / 行业关系。

判定：**P0，必须修。**

---

### P0-2　Postgres Store 被内存缓存遮蔽（source of truth 反转）

现状 [postgres_store.py](../../services/market-data/shanhai_market_data/postgres_store.py)：

```python
def list_company_intelligence(self, limit=50):
    cached = super().list_company_intelligence(limit=limit)
    if cached:        # 本进程写过任意一条即返回，永不回查 Postgres 全量
        return cached
```

问题：

- 进程内存视图压制数据库全量 → 多 worker 数据不一致。
- 继承关系把 cache 当 Repository 父类，依赖方向反了。
- `upsert_quote` 每写一条行情全表重算 JSON，数据量起来即退化。

正确依赖方向：

```
        MarketKnowledgeRepository (interface)
                  |
        +---------+---------+
        |                   |
 PostgresRepository    CacheDecorator(optional, wraps Postgres)
   (source of truth)
```

判定：**P0，必须修。比 Entity 更危险（静默返回错误数据）。**

---

### P1-1　MarketFact schema 是 demo 形态（key-value）

现状 [models.py](../../services/market-data/shanhai_market_data/models.py) `MarketFact`：

```python
entity_id: str
fact_type: str
value: str        # 金融事实被压成字符串
```

金融事实不是 key-value，而是带主语 / 谓语 / 客体 / 时间 / 来源 / 置信度的结构化断言：

```
subject:    company:uuid
predicate:  financial.revenue
object:     { value: 45_000_000_000, currency: CNY }
occurred_at: 2026-03-31
source:     announcement
confidence: 0.99
```

当前 mapper 已经在写 region / industry 两类 MVP fact。若不前置 v1，数据量起来后面临破坏性迁移。

判定：**P1，M2.5 直接定义 MarketFact v1，避免二次迁移。**

---

### P1-2　Ingestion 安全与效率

- [tushare.py](../../services/market-data/shanhai_market_data/tushare.py) `stock_basic` 不带 ts_code 过滤，每次拉全 A 股 ~5000 行再客户端筛 10 家；`daily` 拉全历史只取最新一行。
- [main.py](../../apps/api/shanhai_api/main.py) `POST /market/ingestion/tushare/run` 无鉴权，任意调用即触发外部 API + 写库。

判定：**P1，批量过滤 + endpoint dev-only/鉴权。**

---

### 方向问题　Experience Runtime 节奏

PR-4.1 是纯契约层（Protocol + frozen types，零真实 caller）。在没有真实 candidate 的真空里冻结契约，存在过度设计风险。

依赖顺序修正：

```
旧（错）: Experience Runtime → Market Data
新（对）: Market Data → Market Knowledge → 真实 Candidate → Experience Runtime
```

判定：**不删除，降优先级，PR-4.1 契约层进入冻结待验证状态。**

---

## 2. 目标实体模型（Design Freeze）

```
Company            身份与代码无关的代理键
{
  company_id: company:<uuid>        # 代理键，永不等于 f(ts_code)
  name:       贵州茅台股份有限公司
  aliases:    (...)
  external_ids: { cn_company_code, tushare_company_id, ... }
}

ListedEntity
{
  listed_entity_id: listed_entity:<uuid>
  company_id:       company:<uuid>   # 外键指向 Company
  exchange:         SSE
}

Security
{
  security_id:      security:<uuid>
  listed_entity_id: listed_entity:<uuid>
  ts_code:          600519.SH        # 外部代码 = attribute
}

Listing
{
  listing_id:  listing:<uuid>
  security_id: security:<uuid>
  market:      CN-A
}
```

关键约束：

- `company_id` / `listed_entity_id` / `security_id` / `listing_id` 互不派生。
- ts_code 仅存在于 `Security.ts_code` 与 `external_ids` 映射。
- M2.5 的 resolver v0.1 **可以暂不实现跨证券（A+H）合并**，但 ID 生成不得等于 `f(ts_code)`，为未来合并预留空间。

---

## 3. MarketFact v1（Design Freeze）

```
MarketFact v1
{
  fact_id:     fact:<uuid>
  subject_ref: { entity_type, entity_id }   # 指向 Company / Security / Industry
  predicate:   str                           # 命名空间化，如 financial.revenue
  object_value: JSON                         # { value, unit/currency, ... }
  occurred_at: datetime                      # 事实发生时间（非采集时间）
  source_ref:  SourceRef                     # 复用现有 SourceRef
  confidence:  float                         # 0..1
  valid_from / valid_to: date | None
}
```

派生类型（M2.5 Phase 2 仅落 FinancialFact 与结构化 Tushare 事实，公告 / 新闻留接口）：

- `FinancialFact`：predicate = `financial.*`，object = 金额 + 币种 + 报告期。
- `AnnouncementFact`：predicate = `announcement.*`（接口预留，不爬）。
- `NewsFact`：predicate = `news.*`（接口预留，需 NLP，归 Cognition 阶段）。

约束：MVP 的 region / industry fact 要么升级为 v1 predicate，要么明确不持久化（只作 UI 占位）。

---

## 4. Storage 架构（Design Freeze）

```
MarketKnowledgeStore (Protocol / interface)
    │
    ├── InMemoryMarketKnowledgeStore   # 测试 / 本地
    ├── PostgresMarketKnowledgeStore   # source of truth，读路径直查库
    └── CachedMarketKnowledgeStore     # 可选 decorator，包装 Postgres（非继承）
```

约束：

- Postgres 实现**不继承**内存实现。
- cache 失效语义明确：写穿失效，不得「内存非空即返回」。
- 后续 Redis 也只能作为 `Postgres ← Cache` 的装饰层。

---

## 5. Migration Plan

> 原则：契约先行、可回滚、测试断言修正同步进行。本节描述「怎么迁」，不含代码。

### M-1　Entity Identity 迁移

| 步骤 | 动作 | 风险控制 |
|---|---|---|
| 1 | identity.py 新增 `new_company_id()` 等代理键生成（uuid / 注册表分配），保留旧函数但标记 deprecated | 不破坏现有调用 |
| 2 | models.py `Company.external_ids` 升级为结构化映射（dict / tuple of (scheme, value)） | frozen 模型字段扩展 |
| 3 | resolver.py 改为「先查注册表，命中复用 company_id，未命中分配新代理键」 | A+H 暂不合并但不再硬绑 |
| 4 | store.py 移除硬编码 `security:cn-a:{ts_code}`，统一走 identity 函数 | 单一事实源 |
| 5 | 修正 test_runtime_mvp.py 的「四 ID 不相等」断言为「四 ID 语义独立 + ts_code 仅在 Security」 | 消除假阳性 |

数据迁移：当前仅 10 家内存/本地数据，无历史持久化包袱 → 一次性重建，无需在线迁移脚本。

### M-2　Storage 迁移

| 步骤 | 动作 |
|---|---|
| 1 | 抽出 `MarketKnowledgeStore` Protocol（list / get / upsert 读写分离签名） |
| 2 | Postgres 实现去继承，读路径直查库 |
| 3 | 如需 cache，新增 `CachedMarketKnowledgeStore` decorator |
| 4 | 删除「内存非空即返回」逻辑，补多源一致性测试 |

### M-3　MarketFact 迁移

| 步骤 | 动作 |
|---|---|
| 1 | 定义 MarketFact v1 模型 + FinancialFact |
| 2 | mapper 的 region/industry fact 升级为 v1 predicate 或降级为非持久占位 |
| 3 | 补 fact timeline 查询契约（按 occurred_at 排序） |

---

## 6. Implementation Plan（M2.5 分阶段，逐阶段 Gate）

```
Phase 1  Entity Hardening
  identity.py / resolver.py / models.py / tests
  目标：Company/ListedEntity/Security/Listing 身份真正分离

Phase 2  Knowledge Model
  MarketFact v1 + FinancialFact（Tushare 财务）
  目标：Tushare → Fact → Timeline，形成公司时间线
  不做新闻爬虫

Phase 3  Storage Refactor
  Store interface / Postgres impl / Memory impl / Cache decorator
  目标：source of truth = Postgres，cache 是装饰器

Phase 4  Web Console (apps/console, Next.js)
  Company Intelligence Page：Identity / Financial / Events / Industry / Timeline / AI Summary
  目标：用页面反向验证数据模型（页面展示不出 = 模型有问题）
```

顺序约束：Phase 1 → 2 → 3 必须串行（身份是事实的前提，事实是存储的前提）。Phase 4 可在 Phase 2 后并行启动。

数据源策略：Tushare 是 **Adapter 之一**，不是最终数据源。未来 Market Data Hub 汇聚东方财富 / 巨潮 / 财联社 / 同花顺 / 交易所公告，统一过 Entity Resolver。Tushare Skill **不用** —— ShanHai 是持续运行的 ingestion pipeline，不是临时 tool call。

---

## 7. 验收标准

- [ ] `company_id` 不再等于 `f(ts_code)`，单元测试断言语义独立。
- [ ] A+H 用例（设计层）：两个 security 可挂同一 company_id（即使 v0.1 暂不自动合并，模型也不阻止）。
- [ ] Postgres 为 source of truth，多进程一致性测试通过。
- [ ] MarketFact v1 落地，公司时间线可按 occurred_at 输出。
- [ ] ingestion endpoint 受控（dev-only / 鉴权），stock_basic 批量过滤。
- [ ] Experience Runtime / PR-4.2 / Memory / Trading 未被触碰。

---

## 8. Final Decision

```
Milestone 2.5 Market Foundation Hardening
    ⏳ Design Review Gate
    ❌ Not approved for implementation yet

下一步：等批准后进入 Phase 1 Entity Hardening Implementation
```

下一阶段最大的架构评审者不是 GPT / Claude，而是**真实 A 股数据**。

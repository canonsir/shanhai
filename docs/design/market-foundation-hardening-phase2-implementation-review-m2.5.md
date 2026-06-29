# Milestone 2.5 — Phase 2 Market Knowledge Foundation Implementation Review

> 对 Phase 2 Market Knowledge Foundation 实现结果的评审（Implementation Review）。
> 本阶段按用户指令取消 design gate，改为「实现优先 + 单一 review 文档」。
> 上游冻结依据：`docs/design/market-knowledge-expansion-review-m2.3.md`（MarketFact schema v1 蓝本）、
> `docs/design/market-foundation-hardening-phase1-closure-review-m2.5.md`（Phase 1 Closure，Entity Identity 已解耦）。
> 评审对象：working tree（base `b41ca53`，develop），未提交。

---

## 0. 评审范围与方法

```
Gate 类型：Implementation Review（Phase 2，非 design gate）
代码改动：✅ 本阶段写实现 + 测试 + 文档（一个实现配一个 review 文档）
评审输入：services/market-data/shanhai_market_data/{models,fact_mapper,timeline,store,sync,tushare,api,provider,resolver,__init__}.py
          apps/api/shanhai_api/main.py（Console Alpha /company/:id）
          tests/market_data/test_market_knowledge_facts.py（新增）
          tests/market_data/{test_runtime_mvp,test_data_foundation_mvp}.py（v1 兼容）
```

用户批准范围（5 项）逐项核验，外加 Console Alpha 与边界禁止项确认。
本阶段坚持「真实数据优先 / Schema 由实际 ingestion 数据驱动 / 不新增大量 design gate 文档」。

---

## 1. 范围 1 — MarketFact v1 实现

**结论：✅ 完成。**

证据：

- [`MarketFact`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L249-L276) 从 M2.1 demo 形态（`fact_type` + `value:str`）升级为认知单元 v1：`subject_ref`（指向代理键，非外部码）+ `predicate` + `object_value` / `object_ref` + 三时间戳 `occurred_at` / `published_at` / `captured_at` + `source_ref` / `evidence_refs` / `confidence` + `entity_links` + `attributes`，`schema_version="market_fact.v1"`。
- frozen-hashable 约束：[`FactAttribute`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L222-L230) 与 [`EntityLink`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L233-L246) 用 tuple-of-FrozenModel 代替不可 hash 的 dict，保持 `frozen=True + extra="forbid"`。
- 真实派生而非手写：[`build_company_profile_facts`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L47-L94) 从 `stock_basic` 行产生 PROFILE(region/listing) + INDUSTRY fact；[`build_quote_fact`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L97-L128) 从 `QuoteSnapshot` 产生 QUOTE fact。
- 身份不塌缩：[`test_market_fact_v1_from_sync`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_market_knowledge_facts.py) 断言 `subject_ref.entity_id` 不含 `600519`、等于 `company_id`/`security_id`，predicate=`classified_in_industry`/`closing_price`，`schema_version=="market_fact.v1"`。

铁律确认：外部码 `600519.SH` 永远是 `SourceRef.external_id` 或 attribute，从不进入 `subject_ref.entity_id`。

---

## 2. 范围 2 — FinancialFact 基础 schema

**结论：✅ 完成（独立模型，未塞进 MarketFact）。**

证据：

- [`FinancialFact`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L279-L304) 独立于 MarketFact：结构化字段 `report_period` / `report_type` / `metric_name` / `metric_value` / `unit` / `currency` / `yoy` / `qoq` / `restated` + 三时间戳，`schema_version="financial_fact.v1"`。
- 由实际 ingestion 拆分：[`map_financial_indicator`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L131-L165) 把一条 `fina_indicator` 行按 [`_FINANCIAL_METRICS`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L37-L44) 拆成「每指标一条 FinancialFact」（revenue/net_profit/roe/eps/gross_margin），yoy 从 `or_yoy`/`netprofit_yoy` 取。`report_period` 由 [`_report_period`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L232-L235) 渲染（如 `2025Q4`）。
- 验证：[`test_financial_fact_via_fina_indicator`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_market_knowledge_facts.py) 断言 5 个 metric、`report_period=="2025Q4"`、`report_type=="fina_indicator"`、`yoy==15.0`、`financial_fact_count==5`。

设计判断符合用户要求：财报是结构化数据，不应被压扁成 MarketFact 的 `object_value` 字符串。

---

## 3. 范围 3 — AnnouncementFact 基础 schema

**结论：✅ 完成（独立模型）。**

证据：

- [`AnnouncementFact`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L307-L330)：`announcement_id` / `announcement_type` / `title` / `published_at` / `document_url` / `document_hash` / `extracted_summary` / `mentioned_entities`，`schema_version="announcement_fact.v1"`。只存公告引用与元数据，不存评级/交易建议/无依据推断。
- 由 `anns_d` 派生：[`map_announcement`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L168-L191)，类型走启发式规则 [`_announcement_type`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/fact_mapper.py#L207-L223)（定期报告/业绩预告/分红/重大合同/并购/问询/风险/股东变动），`document_hash` 用 content sha256，`announcement_id` 用 `ts_code|ann_date|title` sha1 去重。
- 验证：[`test_announcement_fact_via_anns_d`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_market_knowledge_facts.py) 断言 `announcement_fact_count==2`、类型 PERIODIC_REPORT + DIVIDEND、`document_hash` 有值、`document_url` 结尾 `annual-2025.pdf`。

---

## 4. 范围 4 — Market Knowledge Timeline（read model，非超级表）

**结论：✅ 完成。**

证据：

- [`CompanyTimelineEvent`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L333-L350) 是 read model，明确「a read model, not a fact source」；记录 `event_time` + `event_time_basis` + `fact_refs`（指回源 fact id，不复制事实真源）。
- [`build_company_timeline`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/timeline.py#L28-L102) 把三类事实家族（MarketFact / FinancialFact / AnnouncementFact）投影到一条有序时间线；默认 `published_at` + `latest_first`，可切 `OCCURRED_AT` / 升序。
- 三时间戳永不塌缩：[`_pick_time`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/timeline.py#L105-L121) 按 `preferred → published_at → occurred_at → captured_at` 回退，`_MIN_TIME` 兜底缺失，事实不会静默消失。
- 验证：[`test_timeline_unifies_all_fact_families_and_orders`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_market_knowledge_facts.py) 断言 timeline 含 FINANCIAL/ANNOUNCEMENT/QUOTE event_type、默认 published_at 降序、`fact_refs` 非空且 `event_id` 以 `event:` 开头、切 OCCURRED_AT+升序验证排序翻转。

设计判断符合用户要求：统一进入「Market Knowledge Timeline」而非「一个超级 Fact 表」——三类事实在各自存储桶中独立沉淀（[store.py](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/store.py#L38-L40)），Timeline 仅在读侧组装。

---

## 5. 范围 5 — Tushare 作为第一个 source adapter

**结论：✅ 完成（能力探测式接入，不破坏既有 provider 契约）。**

证据：

- Provider 扩能：[`TushareProvider.fina_indicator`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/tushare.py#L92-L108) 与 [`anns_d`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/tushare.py#L110-L123)，配套 `_fina_indicator_record` / `_announcement_record` 解析，复用既有 stdlib HTTP + 可注入 transport（测试零网络）。
- 可选 Protocol：[`FinancialDataProvider`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/provider.py#L34-L47) / [`AnnouncementDataProvider`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/provider.py#L50-L59) 与 `MarketDataProvider` 并列；sync 用 `getattr(provider, "fina_indicator"/"anns_d", None)` 探测（[sync.py](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/sync.py#L131-L166)），provider 不实现时优雅降级。
- 优雅降级验证：[`test_optional_capability_absent_yields_no_financial_or_announcement`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_market_knowledge_facts.py) 用 `_BasicOnlyProvider`（只有 stock_basic/daily）断言 `financial_facts==()` / `announcement_facts==()` / count==0，但 MarketFact 与 timeline 仍存在。
- 一致性：[`AShareCompanySyncService`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/sync.py#L50-L129) 注入单一 resolver，bundle 与 quote 的 `security_id` 一致（沿用 Phase 1 修复）。

---

## 6. Console Alpha — `/company/:id` 数据模型验证页

**结论：✅ 完成（数据模型验证工具，非产品 Dashboard）。**

证据：

- 路由 [`company_detail_console`](file:///Users/bytedance/Documents/代码仓库/shanhai/apps/api/shanhai_api/main.py#L104-L112)，纯前端页消费既有端点 `/companies/{ts_code}` 与 `/companies/{ts_code}/timeline`（[main.py](file:///Users/bytedance/Documents/代码仓库/shanhai/apps/api/shanhai_api/main.py#L83-L94)），分区呈现：基本信息 / 证券关系（Company→ListedEntity→Security→Listing 四层 id）/ 行业 / 财务事实 / 公告时间线 / 新闻时间线 / MarketFact Timeline。
- 验证：[`test_company_detail_console_alpha_route`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_runtime_mvp.py) 断言 html 含「证券关系 / 财务事实 (FinancialFact) / 公告时间线 (AnnouncementFact) / MarketFact Timeline」。

用户验收标准达成：每个 fact family 都能在该页自然表达 ⇒ 模型可被页面表达，无塌缩或表达不能。NewsFact 当前为空态占位（本阶段无新闻 source adapter，按范围不实现）。

---

## 7. 边界确认 — 未违反 Phase 2 禁止项

| 禁止项 | 状态 | 证据 |
|---|---|---|
| 改 RuntimeKernel / Experience Runtime | ✅ 未触碰 | `git status` 改动仅在 `services/market-data` + `apps/api` + `tests/market_data` + 文档 |
| 实现 Selector | ✅ 未实现 | 无 experience-runtime 改动 |
| Memory Evolution / Trading Strategy | ✅ 未实现 | 无相关改动；依赖边界测试守护 |
| AI entity merge | ✅ 未做 | resolver 仍 deterministic-only（[resolver.py](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/resolver.py#L9-L13)） |
| Postgres identity registry migration | ✅ 未做 | R1/R2 仍登记不修，归属 Phase 3 |
| 交易词 surface（broker/place_order/position/buy/sell…） | ✅ 无 | `test_dependency_boundary` AST + 文本扫描全绿 |
| 大量 design gate 文档 | ✅ 仅本文 | 单一 implementation review |

---

## 8. 验证结果

market-data 全量测试一次通过（5 文件全绿，无 pytest 依赖、main() + bare assert 风格）：

```
test_identity_registry          ✅
test_data_foundation_mvp        ✅（v1 升级向后兼容，断言无需改）
test_runtime_mvp                ✅（含 console detail 路由测试）
test_dependency_boundary        ✅（依赖边界 + 无交易 surface）
test_market_knowledge_facts     ✅（Phase 2 新增 6 用例）
```

补充确认：旧 MarketFact 字段（`observed_at` / `value:str`）已完全移除，仅 `IdentityMapping.valid_from/valid_to` 保留（与 fact 无关，属迁移留痕）；[`postgres_store.py`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/postgres_store.py) 经 `model_dump(mode="json")`/`model_validate` 整包 JSONB，Phase 2 新 fact 自动序列化，无需改动。

---

## 9. 最终结论

```
Milestone 2.5
  Phase 0 Design Closure              ✅ Completed
  Phase 1 Entity Hardening            ✅ Closure PASS（带 2 项归属 Phase 3 的登记风险）
  Phase 2 Market Knowledge Foundation
      Implementation                  ✅ Completed
      Review                          ✅ PASS
```

五项批准范围 + Console Alpha 全部交付，边界禁止项无违反。ShanHai 首次让真实 A 股公司知识（profile / industry / quote / 财报 / 公告）以三时间语义、实体链接、置信度进入系统，并统一汇入公司知识时间线。

下一阶段（不在本阶段实现，仅声明顺序）：

```
Phase 2 Market Knowledge Foundation（本阶段 ✅）
        ↓
Company Intelligence Console Alpha 反向验证模型（已起步）
        ↓
真实 Candidate Provider（PR-4.2）
        ↓
Experience Runtime（PR-4.2 之后）
        ↓
Memory / Evolution → Trading Intelligence
```

登记延续（不在本阶段处理）：

1. **R1 / R2**（registry 并发 + 持久化边界）继续归属 Phase 3 Storage Refactor（DB `UNIQUE` + `ON CONFLICT`）。
2. **NewsFact source adapter**：模型字段蓝本已在 M2.3 冻结，本阶段无新闻数据源故仅留空态；接入时为纯追加。
3. **external_ids 结构化**（`{source, namespace, external_id}`）：增强项，权威命名空间仍在 registry 三元组。

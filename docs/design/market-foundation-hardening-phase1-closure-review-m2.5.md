# Milestone 2.5 — Phase 1 Entity Hardening Closure Review

> 对 Phase 1 Entity Hardening 实现结果的收尾评审（Closure Review）。
> 本文件只做 **Review，不修改代码**。结论为是否可以通过 Phase 1 Closure Gate。
> 上游冻结依据：`docs/design/market-foundation-hardening-phase0-closure-m2.5.md`、
> `docs/design/market-foundation-hardening-review-m2.5.md`。
> 评审对象：working tree（base `b41ca53`，develop），未提交。

---

## 0. 评审范围与方法

```
Gate 类型：Closure Review（Phase 1）
代码改动：❌ 本阶段不改代码（仅评审 + PROJECT_STATE 更新）
评审输入：services/market-data/shanhai_market_data/{identity,registry,resolver,models,store,mapper,sync,__init__}.py
          tests/market_data/{test_identity_registry,test_runtime_mvp,test_data_foundation_mvp}.py
```

评审五个必检项（用户指令）+ 四个重点问题（用户提出），逐项给出**结论 / 证据 / 风险登记**。
风险项按"现在不修、记录在案、归属后续 Phase"处理，符合 Phase 1 边界纪律。

---

## 1. Check 1 — Entity identity 是否完全脱离 external code

**结论：✅ 通过。**

证据：

- 代理键分配唯一入口 [`new_internal_id`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/identity.py#L17-L19) = `f"{entity_type}:{uuid.uuid4().hex}"`，不编码任何外部码。
- 旧 `*_from_ts_code` 已降级为"仅供迁移留痕（legacy_id）"，注释明确禁止用于分配 live identity（[identity.py](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/identity.py#L22-L38)）。
- `ts_code` 仅出现在 [`Security`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L126-L134)；`Company` 只持 [`external_ids`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L85-L90)（外部码作为属性）。
- 测试从"前缀不同即身份不同"假阳性，改为验证真实生命周期外键关系：[`test_market_entity_schema_does_not_collapse_identity`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_data_foundation_mvp.py#L125-L145) 断言 `listed_entity.company_id == company.company_id`、`security.listed_entity_id == listed_entity.listed_entity_id`、`listing.security_id == security.security_id`，并断言 `"002594" not in company.company_id`、`company_id != ts_code` 且 `!= security_id`。

与 Phase 0 冻结一致：A+H 双上市在模型层不被阻止（多个 `Security` 可共享一个 `company_id`），但 v0.1 不自动合并。

---

## 2. Check 2 — Identity Registry 是否存在并发 / 持久化风险（含 Review 1 + Review 2）

**结论：⚠️ 通过（带登记项）。设计方向正确，但存在两个已知风险，按 Phase 1 纪律"记录不修"。**

### 2.1 并发风险（对应用户 Review 1：线程安全）

[`resolve_or_allocate`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/registry.py#L40-L59) 是典型 **check-then-allocate**：先 `_forward.get(...)`，未命中再 `new_internal_id` + `_record`。中间无锁。并发场景下：

```
worker A: get(key) -> miss
worker B: get(key) -> miss
worker A: allocate surrogate_x, record
worker B: allocate surrogate_y, record   # 同一 external code 产生两个代理键
```

风险触发面（未来）：scheduler / API request / background ingestion 可能并发 `resolve_or_allocate`。当前实际并发面：

- [`build_default_scheduler`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/scheduler.py#L60-L64) 每次新建 service → 新建 `EntityResolver` → 新建 `IdentityRegistry`，单进程、daily loop 串行 `run_once`，**当前无真实并发**。
- 因此此风险目前为**潜在**，不影响 Phase 1 验收。

登记（归属 Phase 3 Storage Refactor / 持久化层）：

- 并发安全应在持久层用 `UNIQUE(entity_type, source, external_id)` 约束 + upsert（DB 层原子）解决，而非在内存 dict 上加进程锁（进程锁无法跨进程/跨实例）。
- 在落地 Postgres identity tables 前，约定 ingestion **单写者**（single-writer）即可规避。

### 2.2 持久化边界（对应用户 Review 2：Persistence 边界）

确认现状与风险：

- [`IdentityRegistry`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/registry.py#L28-L38) 为进程内 in-memory dict（`_forward` / `_reverse` / `_mappings`），不持久化。
- 代理键由 `uuid4` 生成、registry 不落盘 ⇒ **同一 ts_code 在进程重启后会得到新的代理键**。即"确定性复用"的语义边界是 **registry 生命周期内 / 单进程内**，而非跨重启全局稳定。
- 当前 [`store.py`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/store.py#L34) 的 `_security_id_by_ts_code` 同样是内存索引，与 registry 一同每次重建。系统当前是**完全 process-local**的，故重启重建在 MVP 下无破坏。

边界声明（防止 registry 变成隐式数据库）：

```
Phase 1 MVP:  IdentityRegistry = runtime registry（运行期确定性映射，进程内）
Phase 3:      identity 落 Postgres identity tables（source of truth），
              registry 退化为 cache / decorator；surrogate id 在此才获得跨重启稳定性
```

- **铁律重申**：registry 不得在 Phase 1/2 悄悄承担持久化职责；任何"重启后仍需稳定的 surrogate"必须等 Phase 3，不能在内存层硬塞落盘逻辑绕过 Storage Refactor。
- 当前唯一跨重启稳定的锚点是 `legacy_id`（ts_code 同构、确定性），这恰好是迁移映射表的设计用途——Phase 3 用它把旧代理键/旧数据 re-link 到持久化后的新代理键。

---

## 3. Check 3 — External ID namespace 是否支持多数据源（含 Review 3）

**结论：✅ 通过。**

证据：

- registry 正向键为三元组 `(entity_type, source, external_id)`（[registry.py](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/registry.py#L36)），`source` 是独立维度，不与 `external_id` 混并。
- [`IdentityMapping`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L93-L116) 持久行含独立 `source` 字段。
- 多源映射到同一代理键由 [`link`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/registry.py#L61-L83) 支持，并由 [`test_external_source_mapping_links_multiple_sources`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_identity_registry.py#L35-L44) 证明 `tushare:600519.SH` 与 `eastmoney:600519` 指向同一 internal。

用户担心的冲突场景（Wind 与东方财富都用 `600519.SH`）在本设计下**不冲突**：

```
(security, wind,      600519.SH) -> surrogate_x
(security, eastmoney, 600519.SH) -> 不同 key，可独立 link 到 surrogate_x（同公司）或报冲突
```

即 `source` 作为命名空间，避免了 `external_id="600519.SH"` 裸值跨源撞键。冲突写入由 [`link`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/registry.py#L77-L82) 抛 `identity conflict`，永不静默 re-point（[`test_conflicting_link_raises`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_identity_registry.py#L60-L71)）。

一处**非阻塞观察（记录）**：`Company.external_ids` / `ResolvedMarketIdentity.external_ids` 存的是扁平字符串 `"tushare:ts_code:600519.SH"`（source 以前缀形式内嵌），这是属性/展示用的反范式表示；**权威命名空间在 registry 三元组里**，二者并存可接受。Phase 2/3 若要把 `external_ids` 也结构化（`{source, namespace, external_id}`），属增强项，非 Phase 1 缺陷。

---

## 4. Check 4 — Resolver 是否保持 deterministic-only

**结论：✅ 通过。**

证据：

- [`EntityResolver`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/resolver.py#L29-L75) 全部能力为：经 registry 做确定性 `resolve_or_allocate` + `record_legacy_migration`。无 fuzzy / AI merge / embedding / 跨证券自动合并。
- docstring 显式声明 v0.1 out-of-scope（[resolver.py](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/resolver.py#L9-L12)），与 Phase 0 §2 冻结一致。
- 确定性由 [`test_external_mapping_is_deterministic`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_identity_registry.py#L13-L22) 与 [`test_entity_resolver_maps_external_code_to_stable_surrogates`](file:///Users/bytedance/Documents/代码仓库/shanhai/tests/market_data/test_runtime_mvp.py#L80-L112) 双重覆盖（同一 ts_code 复用、不含 `600519`、可回滚 legacy）。

符合用户判断：实体合并应走 `Candidate Proposal → Human/Rule Approval → Evolution`，不是 Resolver；当前实现正确克制。

---

## 5. Check 5 — 是否违反 Phase 1 禁止边界

**结论：✅ 未违反。**

| 禁止项 | 状态 | 证据 |
|---|---|---|
| 改 RuntimeKernel / RuntimeContext / Experience Runtime | ✅ 未触碰 | `git status` 改动仅在 `services/market-data` + `tests/market_data` + 文档 |
| 实现 PR-4.2 Adapter | ✅ 未实现 | 无 experience-runtime 改动 |
| 实现 MarketFact v1 | ✅ 未实现 | [`MarketFact`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/models.py#L169-L177) 仍为 MVP demo 形态（`fact_type` + `value:str`），未升级为 subject/predicate/object（Phase 2） |
| Memory / Evolution / Feedback / Trading | ✅ 未实现 | 无相关改动 |
| 重构 Postgres cache（P0-2 cache-shadowing） | ✅ 未做 | `postgres_store.py` 未改，归属 Phase 3 |

补充确认：调用点已统一为单一事实源——[`sync.py`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/sync.py#L28-L37) 注入单一 `resolver`，[`mapper.py`](file:///Users/bytedance/Documents/代码仓库/shanhai/services/market-data/shanhai_market_data/mapper.py#L31-L37) 的 `map_stock_basic` / `map_daily_quote` 共享之，保证 bundle 与 quote 的 `security_id` 一致（消除了之前 identity/store/mapper 各自生成 ID 的塌缩源）。

---

## 6. Review 4 — Company 合并能力预留（CompanyRelationship）

**结论：✅ schema 未堵死；建议记录、Phase 1 不实现。**

- 现状：模型层**没有** `CompanyRelationship`（上市公司 / 母公司 / 集团关系）。这是**正确的**——Phase 1 不应实现。
- 是否堵死未来：**没有**。理由：
  1. 四层 + 外键结构已支持"多个 ListedEntity/Security 挂同一 Company"（A+H 结构性可表达）。
  2. `Company` 是 frozen + `extra="forbid"` 的独立模型，未来新增 `CompanyRelationship(from_company_id, to_company_id, relation_type, ...)` 为**纯追加**，不需要改现有任何字段。
  3. registry 的 `(entity_type, source, external_id)` 三元组对 `entity_type` 开放，未来可承载 `company_relationship` 类目而不破坏现有键空间。
- 登记建议（不实现）：CompanyRelationship 应作为**独立关系实体**（边），而非塞进 `Company`（点）的字段；母公司/集团/控股链属 Knowledge / Evolution 阶段范畴，需要时单开 ADR。

---

## 7. 最终结论

```
Milestone 2.5
  Phase 0 Design Closure        ✅ Completed
  Phase 1 Entity Hardening
      Implementation            ✅ Completed
      Closure Review            ✅ PASS（带 2 项已登记风险，归属 Phase 3）
```

五项必检全部通过；四个重点问题已逐项回应。两项需后续处理但**当前不修复**的登记项：

1. **R1 并发 check-then-allocate 竞态**（registry.py `resolve_or_allocate`）→ Phase 3 用 DB `UNIQUE` 约束 + upsert 解决；过渡期约定 ingestion single-writer。
2. **R2 持久化边界**：registry = 进程内 runtime registry，surrogate id 跨重启不稳定；Phase 3 落 Postgres identity tables（source of truth），registry 退化为 cache/decorator。严禁在 Phase 1/2 让 registry 变成隐式数据库。

一项增强观察（非缺陷）：`external_ids` 扁平字符串为属性反范式表示，权威命名空间在 registry 三元组；Phase 2/3 可选结构化。

> **不进入 Phase 2 MarketFact v1。** 下一步如获批准，方可按 Phase 0 §5 串行约束开工 Phase 2（MarketFact v1 + FinancialFact + Timeline），届时正式消费本 Phase 建立的稳定身份。

---

## 附：评审追溯

- base commit：`b41ca53`（develop），Phase 1 改动未提交（working tree）。
- 验证：market-data 全量测试（data foundation MVP / runtime MVP / identity registry / tushare provider / dependency boundary）通过。
- 边界扫描：`git status` 改动集中在 `services/market-data` + `tests/market_data` + `CHANGELOG.md` + `docs/PROJECT_STATE.md`，无越界文件。

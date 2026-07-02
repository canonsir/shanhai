# Milestone 2.5 — Phase 0 Closure Review

> 在进入 Phase 1 Entity Hardening Implementation 之前的一次架构收敛。
> 当前仓库同时存在 Runtime / Experience / Market 三个方向，需要在动代码前把
> Identity 迁移策略、Resolver 边界、MarketFact 优先级、Console 验证入口冻结清楚。
> 本文件只做 **Design Review，不写实现代码**。
> 上游：`docs/design/market-foundation-hardening-review-m2.5.md`（commit `96329cb`）。

---

## 0. 状态与边界

```
Gate 类型：Design Review only（Phase 0 Closure）
代码改动：❌ 本阶段不写实现
允许产出：本设计文档 + PROJECT_STATE 更新
```

禁止范围（不变）：

- ❌ Experience Runtime expansion（PR-4.1 契约层保持 🧊 Frozen）
- ❌ PR-4.2 implementation
- ❌ Memory / Evolution / Feedback
- ❌ Trading Strategy
- ❌ RuntimeKernel / RuntimeContext / AgentRunner

收敛后的目标路线（本阶段确认的唯一主线）：

```
Entity Identity
    ↓
MarketFact v1
    ↓
Knowledge Timeline
    ↓
Company Intelligence Console
    ↓
真实 Candidate
    ↓
Experience Runtime
    ↓
AI Decision System
```

---

## 1. Identity Migration Strategy（补充冻结）

### 1.1 原则

金融系统不能简单 `delete old id → generate new id` 改主键。即使当前只有 10 家、且主要在内存/本地，也要在 Phase 1 一开始就建立**可追溯的映射表**，因为未来 Tushare / 东方财富 / 巨潮 / Wind / 同花顺 多源接入时全部要 merge。

### 1.2 Identity Mapping Table（设计层冻结）

```
entity_identity_mapping
{
  old_id:            company:cn-a:600519.sh        # 旧的 ts_code 同构 ID
  new_id:            company:<uuid>                # 新代理键
  entity_type:       company | listed_entity | security | listing
  source:            tushare | manual | ...
  migration_version: m2.5.p1                       # 迁移批次版本
  created_at:        datetime
}
```

示例：

```
company:cn-a:600519.sh   →   company:8f72...
```

### 1.3 Existing Postgres / 本地数据处理

| 情形 | 策略 |
|---|---|
| 内存/本地 10 家（无持久化包袱） | 重建时直接生成新代理键，同时写入 mapping 表留痕 |
| Postgres 已落旧 ID 数据 | 不就地改主键；新增 mapping 表，读路径经映射解析；旧 ID 标记 deprecated |
| 后续多源接入 | 各源外部 ID 进 `external_ids`，统一解析到同一 `new_id` |

约束：

- 迁移**可回滚**：mapping 表保留 old↔new 双向可查。
- 迁移**可重放**：`migration_version` 标识批次，幂等执行。
- Phase 1 不删除旧 ID 字段值，仅切换主身份来源。

---

## 2. Resolver Scope（冻结：v0.1 不做智能合并）

### 2.1 v0.1 只做 External Identifier Mapping

```
输入: 600519.SH
  → security  (by ts_code)
  → listed_entity (by security.listed_entity_id)
  → company   (by listed_entity.company_id)
```

确定性查找，无推断。

### 2.2 明确禁止（v0.1）

- ❌ 名字相似 + 行业相似 + 法人相似 → 自动合并
- ❌ 任何 AI Entity Resolution
- ❌ 跨源模糊匹配

### 2.3 未来归属

跨证券 / 跨源合并（如比亚迪 `002594.SZ` + `1211.HK` 归一 Company）以 **candidate merge proposal** 形式由后续 Evolution / AI 阶段处理，**不在 M2.5**。

设计层只保证：模型**不阻止**两个 security 挂同一 company_id；但 v0.1 **不自动**这么做。

---

## 3. MarketFact v1 Priority（冻结）

### 3.1 优先级

MarketFact v1 是 M2.5 **最高优先级**。Company Intelligence 的价值不是「公司 + 股票 + 行情」字段，而是「公司 → 事实 → 时间 → 来源 → 可信度」的时间线。

### 3.2 MVP fact 处置（明确结论）

| 项 | 决策 |
|---|---|
| MVP 的 `MarketFact{entity_id, fact_type, value:str}` | **废弃**，不进入持久层 |
| mapper 现写的 region / industry fact | 升级为 v1 predicate（`profile.region` / `profile.industry`）或降级为非持久 UI 占位 |
| v1 schema | 直接落地，不做 MVP→v1 二次迁移 |

### 3.3 v1 schema（与上游一致）

```
MarketFact v1
{
  fact_id:      fact:<uuid>
  subject_ref:  { entity_type, entity_id }
  predicate:    str                    # 命名空间化: financial.revenue
  object_value: JSON                   # { value, currency, ... }
  occurred_at:  datetime               # 事实发生时间
  source_ref:   SourceRef
  confidence:   float                  # 0..1
  valid_from / valid_to: date | None
}
```

Phase 2 仅落 `FinancialFact`（Tushare 财务结构化）；`AnnouncementFact` / `NewsFact` 仅预留 predicate 命名空间，不爬、不做 NLP。

---

## 4. Console Alpha Validation（定义为模型验证入口）

### 4.1 定位

Company Intelligence Console **不是展示层，是模型验证工具**。页面画不出来 = 数据模型有问题。位置 `apps/console`（Next.js），不进 `apps/api`。

### 4.2 第一版结构

```
/company/600519.SH

贵州茅台
----------------
Identity
  Company:    贵州茅台股份有限公司
  Securities: 600519.SH
  Industry:   白酒

Timeline (by occurred_at)
  2026-06-20  财报公告
  2026-06-22  机构调研
  2026-06-25  股价异动

AI Summary
  ...
```

### 4.3 验证契约

- Identity 区块能渲染 → 证明四层身份解耦成立。
- Timeline 区块能按 `occurred_at` 排序渲染 → 证明 MarketFact v1 可用。
- 若任一区块需要「拼字段」才能展示 → 回到 Phase 1/2 修模型。

---

## 5. Phase 顺序（收敛后确认）

```
Phase 0  Closure Review            ← 本文件（Design only）
Phase 1  Entity Hardening          identity / resolver / models / mapping table / tests
Phase 2  Knowledge Model           MarketFact v1 + FinancialFact + Timeline
Phase 3  Storage Refactor          interface / Postgres(source of truth) / Memory / Cache decorator
Phase 4  Console Alpha             apps/console, Company Intelligence Page（可在 Phase 2 后并行）
```

串行约束：Phase 1 → 2 → 3。Phase 4 依赖 Phase 2 的 Timeline 契约。

---

## 6. Final Decision

```
Milestone 2.5 Phase 0 Closure Review
    ✅ Design Review Completed
    ⬇️
    Waiting Phase 1 Entity Hardening Implementation Approval

Experience Runtime
    🧊 Frozen（等待真实 Market Candidate 验证）
```

补充冻结项已就位：Identity Migration Strategy（含 mapping 表 + 旧数据处理）、Resolver v0.1 仅外部标识映射、MarketFact v1 直接落地（MVP fact 废弃）、Console Alpha 作为模型验证入口。批准后进入 Phase 1。

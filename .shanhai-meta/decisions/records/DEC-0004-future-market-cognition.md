# DEC-0004：未来方向 — 资本市场短线认知能力（future_direction，不开发）

- 状态：proposed（仅 future_direction，**非 implementation**）
- 关联：[ADR 0000](../../../docs/架构决策记录/0000-项目元上下文架构.md)
- 结构记录：见 [registry.jsonl](../registry.jsonl) 同 id 条目

## 背景

早期讨论中暴露过一个未来能力诉求：`daily_stock_analysis` —— 面向短线交易的市场情绪 /
信号能力（龙虎榜、连板情绪、Short Signal 等 Market Intelligence）。

```
Market Intelligence Layer
   Global Market / News / Industry / Hot Topics / 龙虎榜 / 连板情绪 / Short Signal
        ↓
   Decision Agent
```

## 决定

将「资本市场短线认知能力」**仅记入未来方向 `future_direction`**；
当前**不实现、不进 services、不融合任何代码**。

## 原因

- 它是 ShanHai 未来可能的能力参考，需先沉淀进战略上下文以免遗忘。
- 现在缺 Context / Knowledge / Market Data / Agent Runtime 地基（见 [DEC-0003](DEC-0003-context-first-then-platform.md)），
  直接做会偏离定位、沦为普通量化指标工具。
- ShanHai 的差异是「AI Native 市场认知系统」，而非股票指标工具。

## 备选方案（已考虑）

- 现在就接入 `daily_stock_analysis` 并实现短线模块。
- 完全不记录该方向（风险：未来遗忘已暴露的能力诉求）。

## 已否决

- 现在进入 services 实现短线交易 / 自动下单。

## 证据回链（related_context_events）

- `evt_298ce3fb053d94c9`、`evt_df4fd9983ab2f36e`、`evt_779e8a08412f7a02`、
  `evt_eace2301357bebbd`、`evt_0f786a84cff39f23`
  （见 [events/stream.jsonl](../../events/stream.jsonl)）

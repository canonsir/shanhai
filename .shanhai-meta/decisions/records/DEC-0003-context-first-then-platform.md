# DEC-0003：先完成上下文统一，再进入平台能力建设

- 状态：accepted
- 关联：[ADR 0000](../../../docs/架构决策记录/0000-项目元上下文架构.md)、[AGENTS.md](../../../AGENTS.md)（Phase 0）
- 结构记录：见 [registry.jsonl](../registry.jsonl) 同 id 条目

## 背景

ShanHai 当前处于 Phase 0（Harness 基础建设）。开发优先级：

```
架构正确性 > 模块边界 > 长期扩展性 > 开发速度
```

地基顺序：

```
Context Foundation → Knowledge Model → Market Data Model → Agent Runtime
```

## 决定

优先完成 Project Context Layer（Phase 0 Harness 基础），再发展 Agent / 平台能力；
当前**不实现**行情页面、券商交易、自动交易、高频量化策略。

## 原因

- 缺地基直接做短线 / 交易模块，会沦为普通量化工具，偏离 AI Native 市场认知系统定位。
- 真正长期增值的是研究 / 认知能力与知识沉淀，而非下单能力。

## 备选方案（已考虑）

- 先做行情 / 交易接口，再补认知层。
- Context Layer 与平台能力并行开发。

## 已否决

- 在上下文层完成前先研究券商交易接口 / 自动下单。

## 证据回链（related_context_events）

- `evt_eace2301357bebbd`、`evt_07dc94bff1770476`、`evt_1b33dfde54e345ed`
  （见 [events/stream.jsonl](../../events/stream.jsonl)）

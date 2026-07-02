# DEC-0001：ShanHai 需要独立的 Meta Context Layer

- 状态：accepted
- 关联：[ADR 0000](../../../docs/架构决策记录/0000-项目元上下文架构.md)
- 结构记录：见 [registry.jsonl](../registry.jsonl) 同 id 条目

## 背景

项目的知识、决策、架构演进过去存在于「人的聊天历史」里，而不在「项目本身」。由此：

- 换模型（GPT → Claude → Gemini）→ 丢上下文；
- 换平台 / 换办公环境 → 丢上下文；
- 新会话 → 从零重新解释项目；
- 不同 AI（Trae / Claude / GPT）→ 各自理解不一致；
- 长周期开发 → 架构决策逐渐漂移、重复犯已否决的错。

## 决定

建立独立的项目元上下文层 `.shanhai-meta/`，作为 AI 协作的一等公民上下文基础设施；
项目的认知 / 决策 / 架构演进沉淀在项目本身，而非依赖聊天窗口。

## 原因

- 聊天平台额度 / 降级只是触发器，根因是项目缺少一等公民的「上下文层」。
- 与 ShanHai 自身理念同构：为 Agent 建 Runtime Experience Memory；为「人 + AI 工程协作」建 Meta Context。

## 备选方案（已考虑）

- `docs/chat-history/*.md` 堆原始聊天：无结构 / 无决策层 / 无法幂等增量。
- `services/context-memory` 运行时模块：违反「不进 services」「AI 不直连」边界。
- 复用 `.shanhai/` 运行目录：与 ADR 0009 语义 / gitignore 冲突。

## 已否决

- 把元上下文升级为业务能力放进 `services/`。
- 用摘要替代原始对话作为唯一事实源。

## 证据回链（related_context_events）

- `evt_4ef4b2b08bd28878`、`evt_c464cde38733fe25`、`evt_1b33dfde54e345ed`
  （见 [events/stream.jsonl](../../events/stream.jsonl)）

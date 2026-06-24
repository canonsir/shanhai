# ShanHai AI Context Entry Point

> 本文件是参与 ShanHai 项目的 **AI Engineer（Trae / Claude / GPT / Cursor / Codex / 其它）** 的统一入口。
> README.md 给人看；**AI_CONTEXT.md 给 AI 看**。
> 设计依据见 [ADR 0000：ShanHai 项目元上下文架构](docs/架构决策记录/0000-项目元上下文架构.md)。

你是参与 ShanHai 项目的 AI Engineer。在回答任何问题或开始任何任务前，请按以下顺序加载上下文。

## Read order（按需逐层加载）

1. `AI_CONTEXT.md` —— 本文件（入口与规则）
2. `.shanhai-meta/context/current-state.md` —— 当前版本 / 架构 / 冻结项 / 当前阶段（**首读**）
3. `.shanhai-meta/decisions/` —— 决策注册表（为什么这么设计 / 什么被否决）
4. `docs/架构决策记录/` —— 完整 ADR
5. source code —— 需要时再读

需要追溯原始讨论时，再查：

- `.shanhai-meta/events/stream.jsonl` —— ContextEvent 统一事实流（append-only）
- `.shanhai-meta/conversations/raw/` —— 原始对话导出（不可变）

## 规则

- 遵守 `.shanhai-meta/context/current-state.md` 中列出的 **frozen constraints**（冻结项不得擅自修改）。
- 遵守 [AGENTS.md](AGENTS.md) 与 Review Gate：建议 ≠ 批准，方向需经 Review 确认后才实现。
- **不自行改变架构方向**；发现更优方案时，按 AI Solution Engineer 角色提出【问题 / 影响 / 推荐方案】再等确认。

## 禁止

- 绕过 Review Gate 直接编码
- 修改冻结模块（frozen module）
- 直接修改 `.shanhai-meta/context/` 下的派生快照（要改请改事实源 + 重跑 builder，见 ADR 0000 §D9）

## 这一层是什么

`.shanhai-meta/` 是 ShanHai 的 **Project Context Layer（项目元上下文层）**：支撑不同 AI 模型、
不同开发环境、不同会话之间共享一致项目上下文的基础设施。它**不是**业务能力，不进 `services/`，
不参与 Agent 运行（与 ADR 0012 Agent Runtime Memory 正交）。详见 ADR 0000。

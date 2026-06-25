# ShanHai AI Context Entry Point（Bootstrap Manifest）

> 本文件是参与 ShanHai 项目的 **AI Engineer（Trae / Claude / GPT / Cursor / Codex / 其它）** 的统一入口。
> README.md 给人看；**AI_CONTEXT.md 给 AI 看**。
> 设计依据见 [ADR 0000：ShanHai 项目元上下文架构](docs/架构决策记录/0000-项目元上下文架构.md)。
>
> **定位（Governance ≠ Cognition）**：本文件是 **bootstrap manifest / 治理层（Governance）**——
> 手写、稳定，定义「AI 如何工作、读取顺序、Review Gate、架构纪律、禁止项」。它**不是**认知状态数据，
> 也**不由 builder 生成**。AI 的**当前认知状态**在派生物 `.shanhai-meta/context/cognition.json`（见 §D9）。
> 本文件是导航（指向状态），不是数据库（不内嵌状态）。

你是参与 ShanHai 项目的 AI Engineer。在回答任何问题或开始任何任务前，请按以下顺序加载上下文。

## Read order（按需逐层加载）

1. `AI_CONTEXT.md` —— 本文件（bootstrap manifest：入口、读取顺序、治理纪律）
2. `.shanhai-meta/context/cognition.json` —— **AI 启动认知状态（首要加载，机器读）**：
   identity / phase / decisions / constraints(frozen) / future_directions（由 builder 确定性装配）
3. `.shanhai-meta/context/current-state.md` —— 上者的人读镜像视图（人 review 用；由 renderer 渲染）
4. `.shanhai-meta/decisions/` —— 决策注册表（为什么这么设计 / 什么被否决）
5. `docs/架构决策记录/` —— 完整 ADR
6. source code —— 需要时再读

需要追溯原始讨论时，再查：

- `.shanhai-meta/events/stream.jsonl` —— ContextEvent 统一事实流（append-only）
- `.shanhai-meta/conversations/raw/` —— 原始对话导出（不可变）；Human-AI **reasoning trace，非事实源**：
  对话是推理轨迹，不自动进 `events/stream.jsonl`、不自动抽 Decision（见 ADR 0000 Conversation Ingestion）。
  仅在需要回看历史推理过程时加载，`conversations/index.jsonl` 是已纳管会话目录（catalog）。

## 规则

- 遵守 `.shanhai-meta/context/cognition.json` 的 `constraints`（frozen）列出的冻结项（不得擅自修改；人读镜像见 `current-state.md`）。
- 遵守 [AGENTS.md](AGENTS.md) 与 Review Gate：建议 ≠ 批准，方向需经 Review 确认后才实现。
- **不自行改变架构方向**；发现更优方案时，按 AI Solution Engineer 角色提出【问题 / 影响 / 推荐方案】再等确认。

## 禁止

- 绕过 Review Gate 直接编码
- 修改冻结模块（frozen module）
- 直接修改 `.shanhai-meta/context/` 下的派生物（`cognition.json` / `current-state.md`）；要改请改事实源 + 重跑 builder → renderer（见 ADR 0000 §D9）

## 这一层是什么

`.shanhai-meta/` 是 ShanHai 的 **Project Context Layer（项目元上下文层）**：支撑不同 AI 模型、
不同开发环境、不同会话之间共享一致项目上下文的基础设施。它**不是**业务能力，不进 `services/`，
不参与 Agent 运行（与 ADR 0012 Agent Runtime Memory 正交）。详见 ADR 0000。

## Context Foundation Completed（稳定基础层）

ADR 0000 的认知基础设施已闭环（Raw → ContextEvent → Decision Registry → Cognition Snapshot → Human View）。
`.shanhai-meta/` 与 `tools/context/schema.py` 自此为 **稳定基础层（stable foundation layer）**：

- 已有契约 `ContextEvent` / `DecisionRecord` / `CognitionSnapshot` **语义冻结**（非代码冻结）；变更其字段语义**需 ADR**。
- Runtime 阶段新增 `ObservationEvent` / `MarketEvent` / `DecisionEvent` 等新类型属正常**扩展**，无需 ADR。
- 体检：`python3 -m tools.context.health`（Source / Integrity / Projection，输出 OK / FAILED）。

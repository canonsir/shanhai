# ADR 0003：Workflow Engine 采用自研最小骨架

状态：已采纳
日期：2026-06-22

## 背景

Spec 要求 Workflow Engine "采用 LangGraph 思想"。需决定 Phase 0 是直接引入 LangGraph 库，还是自研受其启发的最小抽象。

## 决定

Phase 0 **自研最小 Workflow 骨架**：定义 `Node`、`Edge`、`Graph`/`Workflow` 抽象与顺序执行器，放在 `services/harness-core`。不引入 LangGraph 依赖。

## 原因

- 避免过早绑定重依赖，保持模块独立与可替换（架构原则 3.3）。
- Phase 0 验收只需"工作流可定义、可执行"，最小骨架即可满足。
- 自研抽象可在未来无痛切换到 LangGraph 或其他引擎。

## 影响

- `harness-core` 提供 `workflow` 子模块，Research Workflow 等以此编排。
- 若未来需要并行/条件分支/持久化等高级能力，再评估引入 LangGraph，并新增 ADR。

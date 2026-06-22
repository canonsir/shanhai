# ADR 0006：Agent Runtime 执行模型

状态：已采纳
日期：2026-06-22

## 背景

Phase 0 的 `agent-runtime` 只有最小骨架：`Agent`（持有 router/tools/memory/workflow）与 `Memory` 接口。Phase 1 需要把它扩展为可承载真实多 Agent 研究系统的运行时，需明确：Agent 如何执行、生命周期如何管理、运行过程如何被结构化记录（便于后续评估与知识沉淀）。同时必须守住 AGENTS.md 的铁律：Agent 不直接绑定模型、不直接访问数据库，调用链为 `Agent → Tool → Service`。

## 决定

1. **执行模型：think → act → observe 循环。**
   - `BaseAgent` 定义三个可覆写钩子：`think(ctx) → Plan`、`act(ctx, plan) → Action 结果`、`observe(ctx, result) → 是否结束`。
   - 默认实现提供「单步直答」行为；复杂 Agent 通过覆写钩子或注入 `Workflow` 实现多步。
2. **生命周期：`AgentStatus`** 枚举（`created → running → completed / failed`），由 `AgentRunner` 驱动与记录。
3. **运行上下文：`AgentContext`** 统一承载本次运行的依赖与状态：注入的 `ModelRouter`、`ToolRegistry`、`Memory`、输入、累计 `steps`。Agent 只能经 context 触达模型与工具。
4. **结构化运行记录：`Step` / `RunResult`。**
   - 每次 think/act/observe 产出一个 `Step`（含类型、内容、可选 tool 调用与结果）。
   - `RunResult` 汇总状态、输出、步骤序列、错误信息，作为评估与知识沉淀的数据源。
5. **能力边界（强制）：** 模型调用仅经 `context.complete(...)`→`ModelRouter`；外部能力仅经 `context.use_tool(...)`→`ToolRegistry`；未授权工具拒绝。Agent 不出现任何 DB / Provider 直接依赖。
6. **向后兼容：** 保留 `Agent`（= `BaseAgent` 别名）与 `use_tool` / `run` 行为，Phase 0 冒烟测试不破坏。

## 原因

- think/act/observe 是 Agent 系统的通用最小执行范式，既能表达单步直答，也能承载多步研究，且与 Workflow（ADR 0003）正交组合。
- 结构化 `Step` / `RunResult` 让「过程」成为一等数据，服务于 evaluation 与「知识优先」原则。
- 通过 `AgentContext` 收口模型/工具访问，从结构上保证架构铁律不被绕过。

## 影响

- `services/agent-runtime` 新增 `types.py`、`context.py`、`runner.py`，扩展 `agent.py`。
- 后续 Research/Analysis/Knowledge/Strategy Agent 均继承 `BaseAgent` 并覆写钩子。
- 多步循环上限由 `max_steps` 约束，避免失控；持久化运行记录（落库）留待数据层接入阶段，另开 ADR。

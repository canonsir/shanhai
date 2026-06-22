# ShanHai Review Context

> AI 架构评审入口。任何 AI（ChatGPT / Claude / Trae）评审本项目时，按本文件指引读取。

## 评审优先读取顺序

```
1. README.md            — 项目定位与快速开始
2. AGENTS.md            — 协作规范与架构原则（铁律）
3. docs/COLLABORATION_PROTOCOL.md — 三方协作协议（角色职责 / 5 原则 / 工作流 / Review 格式）
4. docs/PROJECT_STATE.md — 当前进度与不变量
5. REVIEW.md            — 本文件（评审范围与关注点）
6. docs/架构决策记录/   — ADR（已定型的决策，不要推翻）
7. 代码                 — 按本次目标定位关键文件
```

## 仓库

https://github.com/canonsir/shanhai

读取建议（若无法直接索引仓库）：
- Raw 文件：`https://raw.githubusercontent.com/canonsir/shanhai/main/<path>`
- Commit diff：`https://github.com/canonsir/shanhai/commit/<sha>`

## 当前版本

v0.1.0 · Phase 0 — Harness Foundation

## 当前关注点

- Agent Runtime 设计是否可扩展（生命周期、Tool 调度、Memory）
- Workflow 抽象是否足够（自研最小骨架 vs 未来 LangGraph，见 ADR 0003）
- 模块边界是否清晰、是否存在跨层耦合

## 不允许变化（不变量）

- Model Router 隔离：Agent 不直接绑定/调用模型
- Service 边界：`Agent → Tool → Service → Database`
- 模块独立性：各 service/package 可单独替换
- 已定型 ADR 不被推翻（如需调整，先提新 ADR）

## 评审产出建议格式

```
结论：通过 / 需修改
问题（按严重度）：
  - [严重] ...
  - [建议] ...
影响范围：...
推荐方案：...
```

## 触发方式

> Review ShanHai commit <sha>

或

> Review

评审针对 `develop` 或指定 commit；稳定后再 merge 到 `main`。

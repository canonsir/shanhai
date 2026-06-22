# ShanHai 开发原则（Development Principles）

> ShanHai 是 AI Native 项目，由人与多个 AI Agent（Trae / Claude / GPT / Codex）跨设备、跨会话协作。本文件定义协作的根本原则。

## 1. Git 是唯一事实来源（Single Source of Truth）

项目的真实状态以 Git 仓库为准，而非任何一次对话、任何一台电脑的本地状态。

- 任何重要决策、状态、上下文，必须进入仓库才算「存在」。
- 切换设备、切换 AI，只需 `git pull` 即可获得完整上下文。

## 2. 文档优先（Docs First）

代码之外，先有可被读取的上下文文档。AI 与人都应「先读后写」。

固定上下文入口集：

- `README.md` — 项目定位与快速开始
- `AGENTS.md` — 协作规范与架构铁律
- `docs/PRODUCT_VISION.md` — 为什么存在 / 解决什么问题
- `docs/ARCHITECTURE_CONTEXT.md` — 架构为什么这样设计
- `docs/DEVELOPMENT_PRINCIPLES.md` — 本文件
- `docs/PROJECT_STATE.md` — 当前阶段、进度、禁止项
- `REVIEW.md` — AI 评审入口与读取顺序

## 3. ADR 记录架构决策

任何重大设计调整必须落为 ADR（`docs/架构决策记录/`），格式：背景 / 决定 / 原因 / 影响。

- 已定型的 ADR 不被随意推翻；如需变更，提出新的 ADR。
- 发现架构问题时不自行修改，先提【问题 / 影响 / 推荐方案】并等待确认。

## 4. Agent 不依赖聊天历史

任何 AI Agent 的工作不得依赖某次对话的临时记忆。

- 判断与产出只应基于仓库内可读取的文档与代码。
- 若某上下文只存在于聊天中，应先沉淀进仓库，再据此工作。
- 这保证了任何 Agent、任何时间、任何设备介入，结果一致可复现。

## 5. 所有重要上下文必须进入仓库

聊天记录会丢失、会过期、不可被他人/他机检索。因此：

- 决策 → ADR
- 状态 → `docs/PROJECT_STATE.md`
- 设计意图 → `docs/ARCHITECTURE_CONTEXT.md`
- 愿景与边界 → `docs/PRODUCT_VISION.md`
- 变更 → `CHANGELOG.md`

## 6. 开发优先级

```
架构正确性 > 模块边界 > 长期扩展性 > 开发速度
```

每完成一个模块，同步更新 `README` / `CHANGELOG` / `docs`。

## 7. 协作流（个人项目简化版）

```
开发（develop 分支）
 ↓
测试
 ↓
commit（约定式提交）
 ↓
merge 到 main
 ↓
AI 架构 Review
```

提交评审时保持 Git 最新，并提供：仓库链接 + commit SHA + 本次目标（见 `REVIEW.md`）。

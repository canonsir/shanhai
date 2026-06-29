# AGENTS.md — 山海（ShanHai）AI 平台开发协作规范

> 完整协作治理（三方角色职责、5 大架构原则、Coding Agent 四步工作流、Architecture Review 输入/输出格式）见 [docs/COLLABORATION_PROTOCOL.md](docs/COLLABORATION_PROTOCOL.md)。本文件为铁律速览。
>
> **任何进入本仓库的 AI Agent（Trae / Codex / Claude Code / 其它）必须先读 [docs/AI_COLLABORATION_PRINCIPLES.md](docs/AI_COLLABORATION_PRINCIPLES.md)**：ShanHai 不是普通 CRUD 项目，而是需要持续架构推理的 AI Native 工程；AI 的角色是 **AI Solution Engineer**（探索 → 讨论 → 收敛 → ADR 固化 → 实现），而非机械的需求执行者。
>
> **统一项目上下文入口：先读 [AI_CONTEXT.md](AI_CONTEXT.md)**（项目元上下文层 `.shanhai-meta/` 的入口，含 Read order 与冻结项；见 [ADR 0000](docs/架构决策记录/0000-项目元上下文架构.md)）。

## 1. 项目定位

山海是一套 AI Native 的中国资本市场认知与决策系统。目标不是传统股票软件，而是构建能持续学习、理解和分析中国资本市场的 AI 系统。

```
数据 → 知识 → 认知 → 分析 → 策略 → 执行
```

长期目标：A股知识库 / 公司知识画像 / 产业链关系网络 / 市场事件分析 / 多 Agent 研究系统 / 策略生成 / 自动化交易执行。

## 2. 当前阶段：Phase 0 — Harness 基础建设

只实现：工程结构、Agent Runtime 基础能力、Model Router、Tool Registry、基础知识模型、数据基础设施。

暂不实现：行情页面、券商交易、自动交易、高频量化策略。

## 3. 核心架构原则

### 3.1 模型与业务解耦
所有 Agent 禁止直接调用具体模型。

错误：`agent.model = claude`

正确：`Agent → Model Router → 具体模型 Provider`

### 3.2 知识优先
核心资产不是代码，而是公司/行业/产业链/政策/市场事件/历史经验。所有设计需考虑长期知识沉淀。

### 3.3 模块独立
`harness-core / agent-runtime / model-router / wiki-engine / data-pipeline` 边界清晰。

禁止：Wiki 直接处理 Agent 逻辑、Agent 直接访问数据库、业务代码直接调用模型。

## 4. Agent 开发规范

所有 Agent 必须通过 Tool 获取外部能力。

```
禁止：Agent → Database
应该：Agent → Tool → Service → Database
```

### 4.1 配置文件修改纪律（铁律）

```
禁止 Write 覆盖已有配置文件

修改配置必须：
1. read    — 先读取现有内容，确认全部已有项
2. diff    — 对照变更点，确认只增不误删
3. append  — 增量追加 / 局部编辑，保留原有占位与配置
4. verify  — 改后比对（git diff），确认无意外删除
```

背景：DeepSeek MVP（commit 249efc9）曾以 Write 覆盖 `.env.example`，误删原有 Postgres/Redis/API 占位（已由 83fa2c8 修复）。对**任何疑似已存在的文件**先 Read 再决定 Edit vs Write；配置类文件一律走上述四步，禁止覆盖式写入。

## 5. Git 开发规范

流程：`开发 → 测试 → commit → push → review`

Commit 格式：

```
feat(router): 添加模型注册能力
feat(agent): 添加Agent基础结构
chore(infra): 添加docker环境
```

### 5.1 分支模型

个人项目，简化为两条分支：

```
main      稳定线，仅经 develop 合入
 ↑
develop   开发线，所有开发直接在此进行
```

约定：
- 所有开发直接在 `develop` 进行，不开 feature 分支。
- `develop` 阶段稳定后 merge 到 `main`；不直接向 `main` push 开发性提交。
- 评审针对 `develop` 或指定 commit。

### 5.2 AI 评审协作

每次需要评审时，保持 Git 为最新，并提供：仓库链接 + commit SHA + 本次目标。
评审入口与读取顺序见根目录 [REVIEW.md](REVIEW.md)；项目实时状态见 [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md)。

### 5.3 Review Gate（建议 ≠ 批准）

铁律：Coding Agent 每次输出「下一步建议」后，不得直接执行，必须先经一次架构 Review 确认方向，批准后才开工（`完成 A → 建议 B → Review → 批准 → 开始 B`）。目的：防止单个 Agent 在局部最优下不断迭代、累积偏差使系统偏离整体架构。当前已批准任务范围内的收尾（测试/文档/提交/合并）不受此限。详见 [docs/COLLABORATION_PROTOCOL.md](docs/COLLABORATION_PROTOCOL.md#4-architecture-review-流程)。

## 6. 架构变更规范（ADR）

任何重大设计调整需创建 ADR，目录 `docs/架构决策记录/`，格式：

```
背景：为什么需要调整
决定：采用什么方案
原因：为什么
影响：对未来有什么影响
```

## 7. Coding Agent 工作方式

开始编码前必须阅读：`README.md`、`AGENTS.md`、`docs/`（含 [docs/AI_COLLABORATION_PRINCIPLES.md](docs/AI_COLLABORATION_PRINCIPLES.md)）。

AI 在本项目的角色是 **AI Solution Engineer**，而非机械执行者：需阅读上下文 → 发现架构问题 → 提出多个可选方案 → 分析 trade-off → 推荐方向 → 方案确认后实现。发现「更优方案 / 现有 ADR 不足 / 未来扩展困难 / 成熟开源可替代 / 更合适的 AI 工程范式」时应**主动提出**（含主动挑战 GPT 的建议），不默认沿既定方向实现。

工作流程四阶段：`Phase 1 目标确认 → Phase 2 架构探索（禁止直接编码）→ Phase 3 ADR 确认 → Phase 4 实现`。完整说明见 [docs/AI_COLLABORATION_PRINCIPLES.md](docs/AI_COLLABORATION_PRINCIPLES.md)。

不要直接开始开发。发现架构问题时不要自行修改，先提出【问题 / 影响 / 推荐方案】并等待确认。

## 8. 开发优先级

```
架构正确性 > 模块边界 > 长期扩展性 > 开发速度
```

每完成一个模块，更新 README / CHANGELOG / docs。

## 9. 前端实现规范（铁律）

所有前端实现（`apps/console` 及未来 Web Console / AI Research Workspace / Admin /
Mobile / Dashboard）必须遵守 ShanHai Design System，不得各自为政：

```
Frontend implementation must follow:

design-system/shanhai-console     # 设计语言与组件规范（Trae Design 导出）
docs/frontend-guideline.md        # 前端实现铁律
```

要点（完整见 [docs/frontend-guideline.md](docs/frontend-guideline.md)）：

- 颜色 / 字体 / 圆角 / 间距一律走 token，不写死色值或 magic number。
- 不随意引入新 UI library；技术栈固定 `Next.js + Tailwind + shadcn/ui + Radix + Lucide`（shadcn 是基础设施，ShanHai Design System 是产品语言）。
- 不创建未登记组件；新组件走 `Design System → Component Proposal → Implementation → Review`。
- `design-system/shanhai-console/preview/` 是「产品应该长什么样」的事实来源，写页面前先看。

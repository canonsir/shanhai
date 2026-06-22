# AGENTS.md — 山海（ShanHai）AI 平台开发协作规范

> 完整协作治理（三方角色职责、5 大架构原则、Coding Agent 四步工作流、Architecture Review 输入/输出格式）见 [docs/COLLABORATION_PROTOCOL.md](docs/COLLABORATION_PROTOCOL.md)。本文件为铁律速览。

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

开始编码前必须阅读：`README.md`、`AGENTS.md`、`docs/`。

不要直接开始开发。发现架构问题时不要自行修改，先提出【问题 / 影响 / 推荐方案】并等待确认。

## 8. 开发优先级

```
架构正确性 > 模块边界 > 长期扩展性 > 开发速度
```

每完成一个模块，更新 README / CHANGELOG / docs。

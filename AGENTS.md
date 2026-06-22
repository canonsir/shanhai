# AGENTS.md — 山海（ShanHai）AI 平台开发协作规范

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

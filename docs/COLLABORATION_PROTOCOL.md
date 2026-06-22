# ShanHai AI 协作开发协议

> 本协议是 ShanHai 项目的三方协作治理文档，定义角色职责、核心架构原则、Coding Agent 工作流与 Architecture Review 流程。
> 与 [AGENTS.md](../AGENTS.md)（铁律速览）、[REVIEW.md](../REVIEW.md)（评审入口）、[ADR 0005](架构决策记录/0005-AI评审协作流程与分支模型.md)（流程与分支模型）配套；如有冲突，以 ADR 为准、本协议次之。

## 1. 角色定义

ShanHai 采用三方协作模式：

```
Human Architect
      │
Coding Agent (Trae / Claude / GPT)
      │
Architecture Reviewer (AI)
```

### Human Architect（项目负责人）

- 定义产品方向、决定架构原则、审批重大技术决策、控制长期目标。
- 拥有最终决策权。
- 禁止：将所有实现细节交人工维护；因短期需求破坏长期架构。

### Coding Agent（Trae / Claude / GPT）

- 负责：阅读项目上下文、编写代码、执行测试、提交 Git Commit、更新文档。
- 工作原则「先理解，再修改」：任何修改前必须先读 README.md / AGENTS.md / PROJECT_STATE.md / ARCHITECTURE_CONTEXT.md / 相关 ADR，并判断修改是否符合现有架构。

### Architecture Reviewer（AI 架构评审）

- 负责：架构一致性检查、模块边界检查、长期演进风险评估、下一阶段规划。
- 不负责：直接编写代码、替代 Coding Agent、按个人偏好改变架构。

## 2. 核心架构原则

### Principle 1：Agent 与模型解耦

```
禁止：Agent → OpenAI API
必须：Agent → Model Router → Model Provider
```

模型可替换：GPT / Claude / Qwen / DeepSeek / Local Model。

### Principle 2：Agent 不直接访问基础设施

```
禁止：Agent → Database
禁止：Agent → HTTP API
必须：Agent → Tool → Service → Infrastructure
```

### Principle 3：Local First

```
git clone → 环境安装 → 项目运行
```

开发入口不应强制依赖 Docker / PostgreSQL / Redis / 云服务。SQLite / PostgreSQL / Cloud Service 可作为**增强能力**，但不能成为开发入口。

> 落地见 [ADR 0009](架构决策记录/0009-Local-first持久化.md)：默认 SQLite 落盘，Postgres 为增强后端。

### Principle 4：Knowledge First

核心资产不是模型，而是知识链：

```
数据 → 知识 → 认知 → 策略 → 执行
```

所有金融能力建设优先考虑知识积累。

### Principle 5：架构变更必须 ADR

任何涉及模块新增 / 模块职责变化 / 技术栈变化 / 数据模型变化 / 调用链变化，必须先创建 ADR：

```
提出 ADR → Review → 批准 → 实现 → 更新状态
```

## 3. Coding Agent 工作流程

### Step 1：读取上下文

读取 README.md / AGENTS.md / PROJECT_STATE.md / 相关 ADR。

### Step 2：输出实施计划

```
目标：
影响模块：
修改文件：
架构风险：
测试方案：
是否需要 ADR：
```

### Step 3：执行开发

要求：小步提交、保持模块边界、更新文档、增加测试。

### Step 4：提交结果

```
完成内容：
修改文件：
测试结果：
Git Commit：
当前状态：
下一步建议：
```

> **「下一步建议」只是建议，不是批准。** 输出后必须停下，进入下方 Review Gate，禁止自行开工。

## 4. Architecture Review 流程

### Review Gate（评审门禁）—— 建议 ≠ 批准

**铁律：Coding Agent 每次输出「下一步建议」后，不得直接执行该建议，必须先经过一次架构 Review 确认方向。**

```
Trae：完成 A → 建议 B
        │
发给 Human Architect / Architecture Reviewer
        │
确认 B 是否符合整体架构方向
        │
批准后，Trae 才开始 B
```

目的：避免 AI Agent 开发中最常见的失效模式——单个 Agent 在**局部最优**下不断迭代，累积偏差最终使整个系统偏离最初架构。门禁把「方向校准」强制前置到每一步之前。

适用与边界：
- **适用**：任何新模块 / 新能力 / 新 ADR / 跨模块改动 / 数据模型或调用链变化等「下一步建议」。
- **可不阻塞**：当前已批准任务范围内的收尾（测试、文档、提交、合并）不算新「下一步」，可继续完成。
- 与 Principle 5（架构变更必须 ADR）叠加：涉及架构变更的下一步，Review 即对 ADR 草案的评审。

### Review 输入

```
# ShanHai Phase Review
## 当前阶段
## 本次目标
## 完成内容
## 修改文件
## 测试结果
## Git Commit
## Agent 下一步建议
```

### Reviewer 输出

```
# ShanHai Architecture Review
## 1. 总体评价
## 2. 架构正确点
## 3. 潜在风险
## 4. 是否符合长期方向
## 5. 是否通过
## 6. 下一阶段规划
## 7. 给 Coding Agent 的任务描述
```

## 5. 禁止事项

- **禁止为快速实现破坏抽象**：错误 `Agent 直接调用 Postgres`；正确 `Agent → Store Interface → Postgres Implementation`。
- **禁止过早业务化**：基础设施阶段完成前，禁止提前建设行情系统 / 自动交易 / 券商接口 / 高频策略。
- **禁止模型绑定**：禁止 `system prompt: 使用 GPT`；应 `TaskType → Model Router → Provider`。

## 6. 长期目标

```
AI Native 中国资本市场认知与决策系统
数据 → 知识 → 认知 → 研究 → 策略 → 执行
```

不是「AI 炒股机器人」，而是「一个长期学习中国资本市场的 AI 投资系统」。

## 7. 当前开发阶段

Phase 1.x —— 完成 Agent Runtime + Memory + Evaluation + Model Router。

之后进入：

```
Knowledge Intelligence → Strategy Engine → Backtest → Execution
```

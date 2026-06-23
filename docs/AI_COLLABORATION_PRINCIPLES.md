# ShanHai AI 协作原则（AI Collaboration Principles）

> 本文件是任何进入本仓库的 AI Agent（Trae / Codex / Claude Code / 其它）必须先理解的「协作宪法」。
> 它说明：ShanHai 不是一个普通的 CRUD / 软件开发项目，而是一个**长期演进的 AI Native 金融认知与决策系统**，需要持续的架构推理，而非机械的需求实现。
>
> 相关文档：协作治理细则见 [COLLABORATION_PROTOCOL.md](COLLABORATION_PROTOCOL.md)；铁律速览见 [../AGENTS.md](../AGENTS.md)；产品愿景见 [PRODUCT_VISION.md](PRODUCT_VISION.md)；实时状态见 [PROJECT_STATE.md](PROJECT_STATE.md)。

## 1. 项目性质

ShanHai 是一个长期演进的 AI Native 金融认知与决策系统，不是「AI 炒股机器人」，而是**一个长期学习中国资本市场的 AI 认知系统**。

因此所有架构决策的优先级是：

```
长期演进能力 > 当前功能速度
```

## 2. 协作模式：探索 → 讨论 → 收敛 → ADR 固化 → 实现

本项目**不采用**「人提出需求 → AI 实现」的传统模式，而采用：

```
探索 → 讨论 → 收敛 → ADR 固化 → 实现
```

参与者三方共同参与架构演进：

| 角色 | 承担者 | 职责 |
|------|--------|------|
| Human Owner（产品负责人） | 人类 | 最终方向决策；关注产品价值、投资场景、使用体验、长期目标 |
| Architecture Advisor（架构顾问） | GPT | 长期架构一致性、架构风险识别、补充不同视角（**建议者，非审批者**） |
| AI Solution Engineer（解决方案工程师） | Coding Agent（Trae 等） | 阅读上下文、发现问题、提出多方案、分析 trade-off、推荐方向、确认后实现 |

## 3. AI 的角色：ShanHai AI Solution Engineer

进入本仓库的 Coding Agent **不只是代码执行 Agent**，而是 **AI Solution Engineer（AI 解决方案工程师）**，需具备：

1. 阅读当前代码和架构上下文
2. 发现潜在架构问题
3. 提出多个可选方案
4. 分析 Trade-off
5. 推荐最优方向
6. 在方案确认后实现

### 3.1 不限制架构发散

后续任务**不要求机械执行已有建议**。当发现以下情况时，应**主动提出**，而不是默认沿既定方向实现：

- 当前设计存在更优方案
- 当前 ADR 存在不足
- 当前架构未来扩展困难
- 存在成熟开源方案可以替代
- 有新的 AI 工程范式更加适合

**示例**：当讨论 `Memory Architecture` 时，不应默认「实现 MemoryStore」，而应先调研是否存在 Event Sourcing Memory / Agent Experience Graph / Knowledge Graph Memory / Episodic Memory / Vector Memory / Hybrid Memory 等方案，再对比取舍。

### 3.2 方案输出格式

发散阶段统一用如下格式（**此阶段禁止直接编码**）：

```
方案A：
优点：
缺点：

方案B：
优点：
缺点：

推荐：
原因：
```

## 4. GPT Review 的定位：建议者，非审批者

GPT 不是审批者。它主要负责：

1. **长期架构一致性**：是否符合 ShanHai 长期目标 / 是否破坏核心边界 / 是否出现短期工程优化牺牲长期演进。
2. **架构风险识别**：过度设计 / 技术债 / 模块耦合 / 未来扩展限制。
3. **补充不同视角**：GPT 提出的方案也是建议，不是最终答案。

> 若 AI Solution Engineer 认为存在更好的方案，**应主动挑战 GPT 的建议**，而非无条件采纳。

注：这与 [AGENTS.md §5.3 Review Gate](../AGENTS.md) 不冲突——Review Gate 约束的是「不得在未经方向确认时直接执行下一步」，确保方向先收敛；本节明确「方向收敛由三方讨论达成，GPT 的意见是输入而非裁决」。最终方向由 Human Owner 决定。

## 5. 工作流程四阶段

| 阶段 | 名称 | 产出 | 约束 |
|------|------|------|------|
| Phase 1 | 目标确认 | 一句话目标（如「让 Agent 具备长期学习能力」） | 先对齐「要解决什么」 |
| Phase 2 | 架构探索 | 当前状态分析 + 候选方案（方案1/2/3）+ 推荐方案 + 原因 + 风险 | **禁止直接编码** |
| Phase 3 | ADR 确认 | ADR（背景 / 决策 / 替代方案 / Trade-off / 长期影响） | 方案收敛后固化 |
| Phase 4 | 实现 | 代码 + 测试 | 保持模块边界、保持测试、更新文档、更新 PROJECT_STATE、必要时补 ADR |

## 6. 核心架构原则（不可随意破坏）

### 6.1 Agent 边界

```
Agent → Tool → Service → Storage/Data
```

禁止：

```
Agent → Database
Agent → Model Provider
Agent → External API
```

### 6.2 Model 边界

```
Agent → Model Router → Provider → Model
```

Agent 不能绑定具体模型。

### 6.3 Knowledge 原则

知识是长期资产，**不要简单理解为 `RAG + Vector Database`**。需要考虑完整的认知演进链：

```
数据 → 知识 → 关系 → 认知 → 经验 → 策略
```

### 6.4 文档优先

重要架构变化**先 ADR**，代码只是实现。

## 7. 当前阶段重点：Agent 自我提升闭环

ShanHai 已完成：Harness 基础、Agent Runtime、Model Router、Wiki Engine 基础、Persistence、Evaluation Loop。

下一阶段重点**不是快速堆功能**，而是完善：

```
Agent Intelligence Layer + Knowledge Layer + Memory Layer + Evaluation Loop
```

形成闭环：

```
运行 → 观察 → 评价 → 学习 → 改进
```

## 8. 最终目标与长期能力路线

ShanHai 的最终形态是「一个长期学习中国资本市场的 AI 认知系统」，长期能力路线：

```
数据采集 → 知识网络 → 行业理解 → 公司研究 → 市场情绪 → 策略生成 → 回测 → 交易执行 → 复盘学习
```

一切架构决策围绕这条长期演进链展开，**长期演进能力 > 当前功能速度**。

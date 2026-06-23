# ADR 0011：Model Provider 架构

状态：已采纳
日期：2026-06-22

## 背景

ShanHai 已完成 Model Router V0（ADR 0004：`TaskType → 能力打分 → ModelSpec → Provider`）、`MockProvider`、Agent Runtime（ADR 0006）与 Evaluation Loop Layer 1（ADR 0010）。当前所有模型调用都解析到 `MockProvider`，无任何真实网络/密钥依赖，保证 local-first 与离线测试。

下一阶段（路线第③步）需要**支持真实 LLM Provider**（OpenAI / Anthropic / DeepSeek / Qwen / Local）。本 ADR **仅设计架构，不实现代码**，目标是确定 Provider 抽象、Router 演进方向、能力边界与配置/测试策略，使真实 Provider 可被增量接入而**不改动调用方与 Agent**。

既有契约（本 ADR 在其上演进，不推翻）：
- `ModelProvider.complete(spec: ModelSpec, messages: list[Message]) -> CompletionResult`。
- `CompletionResult(model, provider, content)`。
- `ModelRouter(registry, providers: dict[str, ModelProvider], fallback_provider)`；`select(task, prefer_low_cost)`；`complete(task, messages, context, model)`；`_provider_for(spec)` 按 `spec.provider` 名取实现、缺省回退 `MockProvider`。
- 模型注册表 `models.yaml`：每条 `model` 声明 `provider` + `capability`（含 `cost`）+ 全局 `default`。

约束（AGENTS.md / 协作协议）：Agent 不直连 Provider、Runtime 不绑定具体模型、Model Router 不掺入业务逻辑；架构变更先 ADR 后实现（本 ADR）。

## 待决问题（评审重点）

1. 真实 Provider 如何接入，才能与现有 `ModelProvider` 接口和 Router 的「按 provider 名解析」机制无缝衔接，且**不改调用方**？
2. Provider 需要承担哪些能力（chat/completion、streaming、token 统计、timeout、retry、fallback），各自归属在 Provider 还是 Router？
3. Model Router 从 `TaskType → Provider` 向 `TaskType + Policy + Runtime Context → Model` 演进，如何在**不破坏现有 `select`/`complete` 签名**的前提下预留？
4. API Key 等机密如何管理，才能既禁止进入 Git、又支持环境变量与 local-first？
5. 如何保证「无 API Key 也能跑全部测试」？

## 决定（建议方案，待确认）

### 1. Provider 抽象：保持现有接口，真实 Provider 即新增实现

调用链维持并细化：

```
Agent
  ↓  context.complete(task, messages)
Model Router         （选模型 + 编排 timeout/retry/fallback）
  ↓  _provider_for(spec) 按 spec.provider 名解析
Provider Interface   （ModelProvider.complete(spec, messages) -> CompletionResult）
  ↓
OpenAI / Anthropic / DeepSeek / Qwen / Local / Mock
```

- 真实 Provider（`OpenAIProvider` / `AnthropicProvider` / `DeepSeekProvider` / `QwenProvider` / `LocalProvider`）**实现同一个 `ModelProvider` 接口**，置于 `services/model-router/.../providers/` 下，按 `name`（= `models.yaml` 中的 `provider` 值）注册进 `ModelRouter(providers={...})`。
- 第三方 SDK/HTTP 依赖**惰性导入**（参考 persistence 的 psycopg 处理）并设为**可选依赖**（如 `[openai]`/`[anthropic]`），未安装不阻断 `import`，也不影响 mock 路径——保持 local-first 默认零依赖。
- 调用方（Agent / `AgentContext.complete`）与 `CompletionResult` 形态不变；接入真实 Provider 仅是「实现 + 注册」，验证 ADR 0004「无需改调用方」的承诺。

### 2. Provider 能力（归属划分）

| 能力 | 归属 | 本阶段 |
|------|------|--------|
| chat/completion 接口 | Provider（复用 `complete(spec, messages)`） | 实现 |
| token 统计 | Provider 产出 → 扩展 `CompletionResult`（新增**可选** `usage` 字段，默认 None，向后兼容） | 实现 |
| timeout | Provider 内置默认 + Router 经 `context` 透传覆盖 | 实现 |
| retry（指数退避、仅幂等失败/限流/5xx） | **Router 层编排**（对 Provider 透明，统一策略） | 实现 |
| fallback（主 Provider 失败 → 次选/Mock） | **Router 层编排**（复用既有 `fallback_provider` 思路，扩展为按候选链回退） | 实现 |
| streaming | Provider 接口预留独立方法（如 `stream_complete`），默认 `NotImplemented` | **预留，不实现** |

要点：**timeout/retry/fallback 的编排放 Router**（横切策略，统一治理，Provider 只管「一次调用」），token/timeout 的「执行」在 Provider。streaming 仅预留接口形态，避免本阶段引入复杂度。

### 3. Model Router 演进（向后兼容预留）

- 现状保留：`select(task, prefer_low_cost)` 与 `complete(task, messages, context, model)` 签名**不变**。
- 演进方向：`TaskType + Policy + Runtime Context → Model Selection`。
  - **Policy**：把当前散落在 `select` 内的偏好（成本、能力阈值、Provider 允许/禁用名单、最大重试/超时）收敛为一个可选的 `SelectionPolicy` 抽象，缺省等价于现状行为。
  - **Runtime Context**：复用既有 `complete(..., context: dict)` 通道承载运行时信号（如 `prefer_low_cost`、延迟敏感、Provider 黑白名单），**不新增必填参数**。
- 增量路径：本阶段先落地「真实 Provider + Router 编排 retry/fallback/timeout」，`SelectionPolicy` 仅定义形态与缺省实现，复杂策略（多维加权、A/B、运行时学习）留待后续，必要时另开 ADR。Router 仍**只做选择与编排，不含任何业务逻辑**。

### 4. 配置与机密管理（local-first）

- **API Key 禁止进入 Git**：密钥只来自**环境变量**（如 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY`）；提供 `.env.example`（占位、入库）而真实 `.env` 必须 gitignore。
- **职责分离**：`models.yaml` 只描述**模型能力与路由元数据**（capability/cost/provider），**绝不含密钥**；机密在运行时由 Provider 从环境读取。
- **local-first**：默认无任何 Key 时，Router 走 `MockProvider`（现状行为不变）；配置了某 Provider 的 Key 才启用该真实 Provider。开发入口不依赖任何外部账号。
- 缺 Key 行为：真实 Provider 在缺少对应 Key 时应明确报错（实现阶段定义），但**默认路由不主动选中未配置的 Provider**，避免开发态意外失败。

### 5. 测试策略

- **保留 `MockProvider` 为默认**：所有现有测试与 smoke 继续在 mock 下运行，**无 API Key 也能跑全部测试**。
- 真实 Provider 的单测用**注入假传输层**（stub/fake HTTP）验证「请求构造 / 响应解析 / timeout / retry / fallback」，**不发真实网络请求**、不读真实 Key。
- 真实 API 联调走**显式开关**（如环境变量 `SHANHAI_LIVE_LLM=1`），默认跳过；CI/本机默认离线绿。
- Evaluation Loop（ADR 0010）天然适配：真实 Provider 接入后，其运行轨迹经 `RunStore` 落库并被 `RuntimeEvaluator` 度量，形成「真实模型 → 运行 → 评估」闭环。

### 6. 边界约束（强制）

- **禁止 Agent 直接调用 Provider**：Agent 只经 `AgentContext.complete → ModelRouter`。
- **禁止 Runtime 绑定具体模型**：Agent Runtime 不出现任何 Provider/模型名硬编码；模型选择权完全在 Router。
- **禁止 Model Router 掺入业务逻辑**：Router 只依据能力/策略/运行时上下文做「选择 + 调用编排」，不理解山海的金融/知识业务语义。
- **机密不入码不入库**：Provider 仅从环境读取 Key，代码与 `models.yaml` 不含任何密钥。

## 原因

- 复用既有 `ModelProvider` 接口与「按 provider 名注册/回退」机制，使真实 Provider 成为**纯增量**，兑现 ADR 0004「换模型不改调用方」，契合「架构正确性 > 开发速度」。
- 把 retry/fallback/timeout 编排上提到 Router，避免每个 Provider 各写一套、策略漂移；Provider 专注「一次调用」职责单一。
- Policy/Runtime Context 以**可选、缺省兼容**方式预留，既指明演进方向又不在本阶段过度设计，不破坏现有签名。
- 环境变量 + `models.yaml` 不含密钥 + 默认 Mock，三者共同守住 local-first 与「机密不入库」，且让离线测试始终可跑。

## 影响

- `services/model-router`：新增真实 Provider 实现文件与可选依赖分组；`CompletionResult` **可选**新增 `usage`（向后兼容）；Router 增加 retry/fallback/timeout 编排与 `SelectionPolicy` 缺省形态。`ModelProvider`/`select`/`complete` 对外签名不变。
- 调用方（`AgentContext` / 各 Agent）**零改动**；Mock 路径与全部现有测试不受影响。
- 新增 `.env.example` 与 gitignore 规则；`models.yaml` 维持纯路由元数据。
- 不触碰 `agent-runtime` / `persistence` / `evaluation` / `wiki-engine` 的对外行为。
- 文档：CHANGELOG / PROJECT_STATE / docs 索引在**实现阶段**同步更新（本 ADR 阶段不写代码）。

## 备选方案（已考虑）

- **每个 Provider 自带 retry/fallback/timeout**：实现分散、策略难统一、易漂移，不采纳；改由 Router 统一编排。
- **本阶段就落地完整多维 Policy / 运行时学习选模**：超出当前需要、过早复杂化，不采纳；只预留 `SelectionPolicy` 缺省形态，复杂策略另开 ADR。
- **把 API Key 写入 `models.yaml` 或配置文件入库**：违反「机密不入库」铁律，坚决不采纳；密钥只走环境变量。
- **streaming 本阶段即实现**：会显著增加接口与测试复杂度且非当前刚需，不采纳；仅预留接口形态。
- **去掉 MockProvider、测试直连真实 API**：破坏 local-first 与离线可测性，不采纳；Mock 永久保留为默认。

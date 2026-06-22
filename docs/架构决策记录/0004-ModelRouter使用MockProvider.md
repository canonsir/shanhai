# ADR 0004：Model Router Phase 0 使用 Mock Provider

状态：已采纳
日期：2026-06-22

## 背景

Model Router 验收标准是"可以切换模型"。是否在 Phase 0 接入真实模型 API（OpenAI/DeepSeek 等，需 API key）需要决定。

## 决定

Phase 0 提供 **Mock/Echo Provider**：实现 Provider 抽象接口，返回可预测的回显结果，不依赖外部网络与 API key。真实 Provider（OpenAI、Anthropic、DeepSeek、Qwen、Local）保留接口与 `models.yaml` 注册位，留待后续阶段实现。

## 原因

- 验收只需证明"Router 能按 task/capability 选择并切换不同模型条目"，Mock 即可闭环。
- 不引入外部密钥与网络依赖，CI 与本地启动稳定。
- Provider 抽象先定型，后续接真实 API 不改调用方。

## 影响

- `services/model-router/providers/` 含 `base.py`(抽象) 与 `mock.py`(实现)。
- `models.yaml` 中的真实模型条目当前路由到 mock provider 运行；接入真实 API 时切换 provider 实现并配置 key。
- 新增真实 Provider 不视为架构变更，但接入策略变化需补 ADR。

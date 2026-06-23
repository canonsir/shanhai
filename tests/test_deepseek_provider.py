"""DeepSeek Provider 适配器测试（见 ADR 0011，Phase 2.5.1）。

运行：uv run python -m tests.test_deepseek_provider
要点：
  - 使用 Fake Transport，不依赖真实 API Key、不发真实网络请求。
  - 验证请求构造、响应解析、缺 Key 报错。
  - 端到端 Agent → ModelRouter → DeepSeekProvider 链路（注册到 router.providers）。
  - 确认 MockProvider 仍为默认 Provider（未注册时回退 mock）。
"""

from __future__ import annotations

from pathlib import Path

from shanhai_agent_runtime import BaseAgent
from shanhai_model_router import (
    DeepSeekProvider,
    ModelRegistry,
    ModelRouter,
)
from shanhai_schemas import Message, Role, TaskType

MODELS_YAML = Path(__file__).resolve().parents[1] / "services" / "model-router" / "models.yaml"


def _registry() -> ModelRegistry:
    return ModelRegistry.from_yaml(MODELS_YAML)


class _FakeTransport:
    """记录最后一次调用并返回 OpenAI 兼容的固定响应。"""

    def __init__(self, content: str = "你好，我是 DeepSeek") -> None:
        self.content = content
        self.calls: list[dict] = []

    def __call__(self, url: str, headers: dict, payload: dict, timeout: float) -> dict:
        self.calls.append(
            {"url": url, "headers": headers, "payload": payload, "timeout": timeout}
        )
        return {"choices": [{"message": {"role": "assistant", "content": self.content}}]}


def test_request_construction_and_parsing() -> None:
    fake = _FakeTransport(content="深度求索回复")
    provider = DeepSeekProvider(api_key="sk-test", transport=fake)
    spec = _registry().get("deepseek")

    result = provider.complete(spec, [Message(role=Role.USER, content="分析山海")])

    assert result.provider == "deepseek"
    assert result.model == "deepseek"
    assert result.content == "深度求索回复"

    call = fake.calls[-1]
    assert call["url"] == "https://api.deepseek.com/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer sk-test"
    assert call["payload"]["model"] == "deepseek-chat"  # 取自 models.yaml options
    assert call["payload"]["messages"] == [{"role": "user", "content": "分析山海"}]
    print("[OK] DeepSeek 请求构造与响应解析通过")


def test_missing_api_key_raises() -> None:
    # 不传 key 且不读环境（显式 None → 环境缺失时为 None）
    provider = DeepSeekProvider(api_key="", transport=_FakeTransport())
    spec = _registry().get("deepseek")
    try:
        provider.complete(spec, [Message(role=Role.USER, content="hi")])
        assert False, "缺少 API Key 应抛错"
    except RuntimeError as exc:
        assert "SHANHAI_DEEPSEEK_API_KEY" in str(exc)
    print("[OK] 缺少 API Key 明确报错通过")


def test_malformed_response_raises() -> None:
    bad = lambda url, headers, payload, timeout: {"unexpected": True}  # noqa: E731
    provider = DeepSeekProvider(api_key="sk-test", transport=bad)
    spec = _registry().get("deepseek")
    try:
        provider.complete(spec, [Message(role=Role.USER, content="hi")])
        assert False, "异常响应应抛错"
    except RuntimeError as exc:
        assert "响应格式异常" in str(exc)
    print("[OK] 异常响应结构化报错通过")


def test_end_to_end_router_to_deepseek() -> None:
    # Agent → ModelRouter → DeepSeekProvider（按 provider 名注册），不改 Agent Runtime
    fake = _FakeTransport(content="路由到真实 Provider")
    router = ModelRouter(
        _registry(),
        providers={"deepseek": DeepSeekProvider(api_key="sk-test", transport=fake)},
    )
    result = router.complete(
        task=TaskType.GENERAL,
        messages=[Message(role=Role.USER, content="hello")],
        model="deepseek",
    )
    assert result.provider == "deepseek"
    assert result.content == "路由到真实 Provider"
    assert fake.calls, "应实际经过 DeepSeekProvider"

    # Agent 经 context.complete 走同一 router，链路打通且不直连 Provider
    agent = BaseAgent(name="ds", router=router)
    run = agent.run("分析比亚迪")
    assert run.ok
    print("[OK] 端到端 Agent → Router → DeepSeek 链路通过")


def test_mock_remains_default() -> None:
    # 未注册任何真实 Provider：deepseek 模型仍回退 MockProvider（默认 Provider 不变）
    router = ModelRouter(_registry())
    result = router.complete(
        task=TaskType.GENERAL,
        messages=[Message(role=Role.USER, content="hi")],
        model="deepseek",
    )
    assert result.content.startswith("[mock:"), "未注册时应回退 MockProvider"
    print("[OK] MockProvider 仍为默认 Provider 通过")


def main() -> None:
    test_request_construction_and_parsing()
    test_missing_api_key_raises()
    test_malformed_response_raises()
    test_end_to_end_router_to_deepseek()
    test_mock_remains_default()
    print("\nDeepSeek Provider 适配器测试全部通过 ✅")


if __name__ == "__main__":
    main()

"""DeepSeek Provider 适配器（见 ADR 0011）。

实现统一的 ModelProvider 接口，验证 Agent → Model Router → Real Provider 链路。
设计要点：
- 网络调用通过可注入的 transport 完成；默认用标准库 urllib（零额外依赖，保持 local-first）。
- 测试注入 Fake Transport，无需真实 API Key、不发真实请求。
- API Key 仅从环境变量 SHANHAI_DEEPSEEK_API_KEY 读取，绝不入码入库。
"""

from __future__ import annotations

import json
import os
from typing import Callable

from shanhai_schemas import Message, ModelSpec

from shanhai_model_router.providers.base import CompletionResult, ModelProvider

# transport 契约：给定 url/headers/payload/timeout，返回解析后的响应 JSON（dict）。
Transport = Callable[[str, dict, dict, float], dict]

API_KEY_ENV = "SHANHAI_DEEPSEEK_API_KEY"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_TIMEOUT = 30.0


def _urllib_transport(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    """默认传输层：标准库 urllib POST JSON，避免引入第三方 SDK 依赖。"""
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class DeepSeekProvider(ModelProvider):
    """DeepSeek Chat Completions 适配器。"""

    name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        # 显式传入优先（测试用）；否则从环境读取，缺失时延后到调用时报错
        self._api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self._transport = transport or _urllib_transport

    def complete(
        self,
        spec: ModelSpec,
        messages: list[Message],
    ) -> CompletionResult:
        if not self._api_key:
            raise RuntimeError(
                f"DeepSeekProvider 缺少 API Key，请设置环境变量 {API_KEY_ENV}"
            )

        base_url = spec.options.get("base_url", DEFAULT_BASE_URL).rstrip("/")
        model_id = spec.options.get("model", spec.name)
        timeout = float(spec.options.get("timeout", DEFAULT_TIMEOUT))

        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
        }

        data = self._transport(url, headers, payload, timeout)
        content = self._extract_content(data)
        return CompletionResult(model=spec.name, provider=self.name, content=content)

    @staticmethod
    def _extract_content(data: dict) -> str:
        """从 DeepSeek（OpenAI 兼容）响应中取出文本内容。"""
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"DeepSeek 响应格式异常: {data!r}") from exc

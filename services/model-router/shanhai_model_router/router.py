"""ModelRouter — 统一入口。

按 task 的能力需求选择最合适的模型，再委派给对应 Provider。
Phase 0 所有 provider 解析为 MockProvider（见 ADR 0004）。
"""

from __future__ import annotations

from shanhai_schemas import Message, ModelSpec, TaskType

from shanhai_model_router.providers.base import CompletionResult, ModelProvider
from shanhai_model_router.providers.mock import MockProvider
from shanhai_model_router.registry import ModelRegistry

_COST_RANK = {"low": 0, "medium": 1, "high": 2}


class ModelRouter:
    def __init__(
        self,
        registry: ModelRegistry,
        providers: dict[str, ModelProvider] | None = None,
        fallback_provider: ModelProvider | None = None,
    ) -> None:
        self._registry = registry
        self._providers = providers or {}
        # Phase 0：缺省 provider 统一回退到 mock
        self._fallback = fallback_provider or MockProvider()

    def select(
        self,
        task: TaskType | str = TaskType.GENERAL,
        prefer_low_cost: bool = False,
    ) -> ModelSpec:
        """根据 task 能力分选择模型；同分时按成本偏好打破平局。"""
        task = TaskType(task) if isinstance(task, str) else task
        candidates = self._registry.all()

        def score(spec: ModelSpec) -> tuple[int, int]:
            cap = spec.capability
            ability = getattr(cap, task.value, 0) if task != TaskType.GENERAL else (
                cap.reasoning + cap.coding + cap.extraction + cap.summarization
            )
            cost_rank = _COST_RANK.get(cap.cost, 1)
            # prefer_low_cost 时成本越低越优（取负），否则不参与排序
            cost_key = -cost_rank if prefer_low_cost else 0
            return (ability, cost_key)

        best = max(candidates, key=score)
        # 若所选模型在该 task 上能力为 0，则回退默认模型
        chosen_ability = score(best)[0]
        if chosen_ability <= 0:
            return self._registry.get(self._registry.default)
        return best

    def _provider_for(self, spec: ModelSpec) -> ModelProvider:
        return self._providers.get(spec.provider, self._fallback)

    def complete(
        self,
        task: TaskType | str,
        messages: list[Message],
        context: dict | None = None,
        model: str | None = None,
    ) -> CompletionResult:
        """统一补全入口。

        - model 显式指定时直接使用；
        - 否则按 task 自动选择。
        """
        context = context or {}
        if model is not None:
            spec = self._registry.get(model)
        else:
            spec = self.select(task, prefer_low_cost=context.get("prefer_low_cost", False))
        provider = self._provider_for(spec)
        return provider.complete(spec, messages)

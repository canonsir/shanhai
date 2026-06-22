"""模型注册表：从 models.yaml 加载模型条目。"""

from __future__ import annotations

from pathlib import Path

import yaml
from shanhai_schemas import Capability, ModelSpec


class ModelRegistry:
    def __init__(self, models: dict[str, ModelSpec], default: str | None = None) -> None:
        if not models:
            raise ValueError("模型注册表为空")
        self._models = models
        if default is not None and default not in models:
            raise ValueError(f"默认模型不存在: {default}")
        self._default = default or next(iter(models))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ModelRegistry":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        entries = raw.get("models", {})
        models: dict[str, ModelSpec] = {}
        for name, cfg in entries.items():
            cfg = cfg or {}
            cap = Capability(**(cfg.get("capability") or {}))
            models[name] = ModelSpec(
                name=name,
                provider=cfg.get("provider", "mock"),
                capability=cap,
                options=cfg.get("options", {}) or {},
            )
        return cls(models=models, default=raw.get("default"))

    @property
    def default(self) -> str:
        return self._default

    def get(self, name: str) -> ModelSpec:
        if name not in self._models:
            raise KeyError(f"未注册的模型: {name}")
        return self._models[name]

    def all(self) -> list[ModelSpec]:
        return list(self._models.values())

    def names(self) -> list[str]:
        return list(self._models)

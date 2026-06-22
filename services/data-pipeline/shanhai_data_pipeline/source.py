"""数据源抽象骨架。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class DataSource(ABC):
    """所有数据源的基类。Phase 0 仅定义接口。"""

    name: str = ""

    @abstractmethod
    def fetch(self, **kwargs: Any) -> Iterable[dict]:
        """拉取原始数据。后续由 wiki-engine 编译为知识。"""
        raise NotImplementedError

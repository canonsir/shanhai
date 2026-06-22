"""Memory 接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """Agent 记忆抽象。Phase 0 仅定义接口与内存实现。"""

    @abstractmethod
    def remember(self, key: str, value: Any) -> None: ...

    @abstractmethod
    def recall(self, key: str, default: Any = None) -> Any: ...

    @abstractmethod
    def history(self) -> list[Any]: ...


class InMemoryMemory(Memory):
    """进程内存实现，便于骨架阶段测试。"""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._history: list[Any] = []

    def remember(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._history.append((key, value))

    def recall(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def history(self) -> list[Any]:
        return list(self._history)

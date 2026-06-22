"""Tool 抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ToolResult(BaseModel):
    """统一的工具返回结构。"""

    ok: bool = True
    data: Any = None
    error: str | None = None


class Tool(ABC):
    """所有工具的基类。

    子类需声明 name / description，并实现 execute()。
    """

    name: str = ""
    description: str = ""

    def __init__(self) -> None:
        if not self.name:
            raise ValueError(f"{type(self).__name__} 必须定义 name")

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """执行工具。具体业务工具在此对接 Service。"""
        raise NotImplementedError

"""ShanHai 共享数据契约。

仅放置跨模块通用的数据结构，避免 service 之间互相耦合。
"""

from shanhai_schemas.model import (
    Capability,
    Message,
    ModelSpec,
    Role,
    TaskType,
)

__all__ = [
    "Capability",
    "Message",
    "ModelSpec",
    "Role",
    "TaskType",
]

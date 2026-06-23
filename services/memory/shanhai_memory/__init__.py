"""ShanHai Memory — Agent 记忆访问层（见 ADR 0012）。

Layer 1：Runtime Access Layer。三层记忆（Runtime / Knowledge / Experience）统一通路：
- MemoryScope / MemoryRecord / MemoryQuery：归一请求与返回契约。
- RuntimeMemoryAdapter / KnowledgeReadAdapter / ExperienceReadAdapter：scope 适配。
- MemoryService：按 scope 路由 read/search/write（仅 runtime 可写）。
- MemoryTool：Agent 触达 Memory 的唯一通道（action 派发）。

本阶段不含持久 MemoryStore（Storage 留待后续）；不引入 vector / semantic / 自动总结；
KNOWLEDGE / EXPERIENCE 只读委派事实来源，不复制、不另存。
"""

from shanhai_memory.adapters import (
    ExperienceReadAdapter,
    KnowledgeReadAdapter,
    RuntimeMemoryAdapter,
)
from shanhai_memory.models import MemoryQuery, MemoryRecord, MemoryScope
from shanhai_memory.service import MemoryService
from shanhai_memory.tool import MemoryTool

__all__ = [
    "MemoryScope",
    "MemoryRecord",
    "MemoryQuery",
    "RuntimeMemoryAdapter",
    "KnowledgeReadAdapter",
    "ExperienceReadAdapter",
    "MemoryService",
    "MemoryTool",
]

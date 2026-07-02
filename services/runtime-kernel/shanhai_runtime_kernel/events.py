"""RuntimeEvent 契约（Runtime Kernel v0.7 Phase 1 / PR-1）。

RuntimeEvent 是 Run 期间产生事件的**身份信封（identity envelope）**：统一为事件
绑定运行身份与时间，使事件可被 Evaluation / Experience Evolution 关联回某次 Run。

信封 schema（v0.5/v0.6 冻结）::

    {event_id, run_id, timestamp, event_type, payload}

- ``run_id`` 复用同一运行身份（与 RuntimeContext.identity_context.run_id 一致）。
- ``payload`` 承载既有执行产物（如 agent-runtime 的 RunResult / Step，public
  interface），本契约**不新造** payload schema；PR-1 以 ``Any`` 占位、不 import
  下游、不建 RuntimeEventStore（纯结构，G1）。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RuntimeEventType(str, Enum):
    """Run 生命周期内的事件类型（PR-1 最小集，与生命周期态对应）。"""

    RUN_CREATED = "run_created"
    CONTEXT_ASSEMBLED = "context_assembled"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_CLOSED = "run_closed"


class RuntimeEvent(BaseModel):
    """Run 事件身份信封：为事件绑定运行身份与时间。"""

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    run_id: str
    event_type: RuntimeEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # 承载既有执行产物（RunResult/Step 等 public interface）；不新造 schema。
    payload: Any = None

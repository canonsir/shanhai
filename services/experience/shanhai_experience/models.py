"""Experience 层经验事件数据契约（见 ADR 0014，Stage 1：Event Infrastructure）。

经验的原子单位是一条不可变 ExperienceEvent，描述「某 Agent 在某时刻经历/产生了什么」。
本层是经验系统的事实基座（Event Log Lite），只追加、不就地修改历史。

引用而非复制（ADR 0014 §4/§5）：经验只经 refs 引用外部对象（run_id / evaluation / entity），
不复制 RunStore 的 Step 明细、不内嵌 Evaluation 度量、不复制 Knowledge 实体内容——
各自的唯一事实来源不变。本模块因此零业务依赖（仅 pydantic），结构上无法访问那些类型。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ExperienceEventType(str, Enum):
    """经验事件类型（最小集，可扩展，见 ADR 0014 §1）。"""

    # Agent 作出一个判断/结论
    DECISION = "decision"
    # 记录一项观察/中间发现
    OBSERVATION = "observation"
    # 一次评估产出被关联进经验（经 ref，不内嵌度量）
    EVALUATION = "evaluation"
    # 延迟结果回填：某历史决策的实际结果（T+N 日市场结果 / ground truth）
    OUTCOME = "outcome"
    # 蒸馏出的教训/经验（语义经验的事件化记录，ADR 0013 Feedback 晋升）
    LESSON = "lesson"


class ExperienceRefs(BaseModel):
    """对外部对象的引用而非拷贝（ADR 0014 §4/§5/§6）。

    只持有标识符：RunStore / Evaluation / Knowledge 各自保持唯一事实来源，
    需要详情时按 id 回查对应 Service，杜绝双写漂移。
    """

    # 关联的运行标识（引用 RunStore，不复制 Step 明细）
    run_id: str | None = None
    # 关联的评估引用（如 run_id + evaluator），不内嵌 metrics
    evaluation_ref: str | None = None
    # 关于哪些知识实体（公司/行业/政策/事件…），只引用 id 不复制 Entity
    entity_ids: list[str] = Field(default_factory=list)
    # 指向被修正/回填的历史事件（如 outcome 挂回 decision）
    parent_event_id: str | None = None


class ExperienceEvent(BaseModel):
    """一条不可变经验事件（append-only 事实基座，ADR 0014 §1）。

    一经写入不得修改/删除；修正一律以新事件追加并经 refs.parent_event_id 关联，
    保证可复盘、可审计、可重建「Agent 当时知道什么」。
    """

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    # 所属情景（通常等于一次 run 的标识或一个研究主题标识）
    episode_id: str
    agent: str
    type: ExperienceEventType
    # 事件内容，按 type 解释
    payload: dict = Field(default_factory=dict)
    refs: ExperienceRefs = Field(default_factory=ExperienceRefs)
    # 业务发生时间（可与写入时间不同，支撑延迟回填）
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    # 写入时间
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

"""episode_id 解析（见 ADR 0015 Decision D）。

episode = 长期研究主题 / 认知任务；run = 一次执行实例。二者解耦：episode_id != run_id，
一个 episode 可串联多次 run。当未显式指定 episode_id 时回退 run_id（兼容 Stage 1）。

回退逻辑统一收口于此单一函数，不在各生产者内联，避免未来 episode 体系演进时
修改面失控。
"""

from __future__ import annotations


def resolve_episode_id(explicit_episode_id: str | None, run_id: str | None) -> str:
    """解析事件归属的 episode_id。

    - 显式 episode_id 优先（跨 run 研究主题）。
    - 缺省回退 run_id（单 run 情景，兼容 Stage 1）。
    - 两者皆空则报错：事件必须可归属到某个情景。
    """
    episode_id = explicit_episode_id or run_id
    if not episode_id:
        raise ValueError("无法解析 episode_id：explicit_episode_id 与 run_id 均为空")
    return episode_id

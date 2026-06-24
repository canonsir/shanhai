"""ShanHai Project Context Layer — 同步工具（tools/context）。

零依赖（仅 Python 标准库）。设计见 ADR 0000：docs/架构决策记录/0000-项目元上下文架构.md

子模块：
- schema.py             Context Domain Model（ContextEvent / DecisionRecord / ContextSnapshot）
- import_chat.py        Raw conversation export → ContextEvent 流（actor=unknown，幂等）
- append_conversation.py 单条追加 ContextEvent（持续同步入口）
- build_context.py      事实源 → context/ 派生快照（幂等可重跑）

注意：本目录是工程元工具，不属于 services/，不参与 Agent 运行。
"""

__all__: list[str] = []

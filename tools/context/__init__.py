"""ShanHai Project Context Layer — 同步工具（tools/context）。

零依赖（仅 Python 标准库）。设计见 ADR 0000：docs/架构决策记录/0000-项目元上下文架构.md

子模块：
- schema.py             Context Domain Model（ContextEvent / DecisionRecord / ContextSnapshot / CognitionSnapshot）
- import_chat.py        Raw conversation export → ContextEvent 流（actor=unknown，幂等）
- decisions.py          Decision Registry：registry.jsonl（唯一结构事实源）→ 瞬态人读视图（不落盘）
- append_conversation.py 单条追加 ContextEvent（持续同步入口；Commit 4 已推迟）
- builder.py            Cognition Snapshot Builder：project.yaml + registry.jsonl → context/cognition.json（确定性装配，禁 LLM）
- renderer.py           Cognition Snapshot Renderer：context/cognition.json → context/current-state.md（人读视图，纯函数，禁 LLM）
- health.py             Context Health Check：Source/Integrity/Projection 体检（OK / FAILED，只读，禁 LLM）

注意：本目录是工程元工具，不属于 services/，不参与 Agent 运行。
"""

__all__: list[str] = []

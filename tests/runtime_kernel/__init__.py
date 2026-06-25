"""Runtime Kernel Contract Test Layer（v0.7 §0.C G5 / Q5.4）。

测**不可违反的边界**，而非实现。覆盖：
- test_context_contract：RuntimeContext immutability / schema_version / run_id 单点 / R7 字段集合冻结
- test_lifecycle_contract：合法链通过、非法迁移抛错（禁 RUNNING→READY）
- test_event_contract：RuntimeEvent identity envelope schema
- test_dependency_boundary：AST 静态检查依赖方向 + PR-1 纯结构（G1）
"""

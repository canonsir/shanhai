"""Wiki 信息提取测试（Phase 1，见 ADR 0007）。

运行：uv run python -m tests.test_wiki_extraction
覆盖：
  1. Extractor 规则驱动抽取实体与关系（确定性）
  2. WikiExtractionAgent 链路：模型在环（ModelRouter）+ Tool 调用 + 结构化 RunResult
  3. 未识别内容不产出噪声关系
"""

from __future__ import annotations

from pathlib import Path

from shanhai_agent_runtime import StepType
from shanhai_model_router import ModelRegistry, ModelRouter
from shanhai_tools import registry
from shanhai_wiki_engine import (
    Document,
    EntityType,
    Extractor,
    RelationType,
    WikiExtractionAgent,
    WikiExtractTool,
)

MODELS_YAML = Path(__file__).resolve().parents[1] / "services" / "model-router" / "models.yaml"


def _router() -> ModelRouter:
    return ModelRouter(ModelRegistry.from_yaml(MODELS_YAML))


def test_extractor_entities_and_relations() -> None:
    doc = Document(
        id="doc:1",
        title="宁德时代简介",
        content="宁德时代是动力电池龙头，主营动力电池，属于新能源行业；碳中和政策利好新能源。",
    )
    compiled = Extractor().extract(doc)

    names = {e.name for e in compiled.entities}
    assert {"宁德时代", "动力电池", "新能源", "碳中和"} <= names, f"实体识别不全: {names}"

    rels = {(r.type, r.source_id, r.target_id) for r in compiled.relations}
    assert (
        RelationType.BELONGS_TO_INDUSTRY,
        f"{EntityType.COMPANY.value}:宁德时代",
        f"{EntityType.INDUSTRY.value}:新能源",
    ) in rels, "公司→行业 关系缺失"
    assert (
        RelationType.AFFECTS_INDUSTRY,
        f"{EntityType.POLICY.value}:碳中和",
        f"{EntityType.INDUSTRY.value}:新能源",
    ) in rels, "政策→行业 关系缺失"
    print("[OK] Extractor 规则驱动抽取实体与关系通过")


def test_extractor_alias_recognition() -> None:
    doc = Document(id="doc:2", title="别名", content="BYD 布局新能源。")
    compiled = Extractor().extract(doc)
    assert any(e.name == "比亚迪" for e in compiled.entities), "别名 BYD 未归一到 比亚迪"
    print("[OK] Extractor 别名归一通过")


def test_extractor_no_noise() -> None:
    doc = Document(id="doc:3", title="无关", content="今天天气不错。")
    compiled = Extractor().extract(doc)
    assert compiled.entities == [] and compiled.relations == [], "不应产出噪声实体/关系"
    print("[OK] Extractor 无关文本不产噪声通过")


def test_extraction_agent_chain() -> None:
    if not registry.has("wiki_extract"):
        registry.register(WikiExtractTool())
    doc = Document(
        id="doc:4",
        title="比亚迪",
        content="比亚迪主营动力电池，属于新能源行业。",
    )
    agent = WikiExtractionAgent(name="wiki-agent", router=_router(), tools=["wiki_extract"])
    result = agent.run(doc)
    assert result.ok, f"Agent 运行失败: {result.error}"

    # 模型在环：think 步思路应记录所选模型
    think = next(s for s in result.steps if s.type == StepType.THINK)
    assert "调用 wiki_extract" in think.content, "think 未体现模型规划→工具调用"

    # act 步经 Tool 产出编译后的 Document
    act = next(s for s in result.steps if s.type == StepType.ACT)
    assert act.tool == "wiki_extract"
    compiled = act.tool_result
    assert isinstance(compiled, Document)
    names = {e.name for e in compiled.entities}
    assert {"比亚迪", "动力电池", "新能源"} <= names, f"链路抽取实体不全: {names}"
    assert any(r.type == RelationType.BELONGS_TO_INDUSTRY for r in compiled.relations)
    print("[OK] WikiExtractionAgent 链路（模型在环 + Tool → Service）通过")


def main() -> None:
    test_extractor_entities_and_relations()
    test_extractor_alias_recognition()
    test_extractor_no_noise()
    test_extraction_agent_chain()
    print("\nWiki 信息提取测试全部通过 ✅")


if __name__ == "__main__":
    main()

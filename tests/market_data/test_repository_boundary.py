"""M3.3 Phase 1 — Market Knowledge Repository boundary tests.

Pins the two invariants the Repository Boundary must keep true so persistence
can move from in-memory to SQLite / Postgres (Phase 2 / 3) without touching any
caller:

1. The in-memory adapter structurally satisfies the MarketKnowledgeRepository
   Protocol (runtime_checkable).
2. The business layer (api / acquisition / sync) depends only on the abstraction
   — it must NOT import any concrete store / postgres / sqlite module.

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_repository_boundary
"""

from __future__ import annotations

import ast
from pathlib import Path

from shanhai_market_data import (
    InMemoryMarketKnowledgeRepository,
    MarketKnowledgeRepository,
)

ROOT = Path(__file__).resolve().parents[2]
MARKET_DATA = ROOT / "services" / "market-data" / "shanhai_market_data"

# Business-layer modules that must stay storage-agnostic.
BUSINESS_LAYER = ("api.py", "acquisition.py", "sync.py")

# Concrete persistence modules the business layer must never import.
FORBIDDEN_PERSISTENCE_MODULES = {
    "shanhai_market_data.store",
    "shanhai_market_data.postgres_store",
    "shanhai_market_data.sqlite_store",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_in_memory_adapter_satisfies_repository_protocol() -> None:
    repo = InMemoryMarketKnowledgeRepository()
    assert isinstance(repo, MarketKnowledgeRepository)
    print("[OK] InMemoryMarketKnowledgeRepository 满足 MarketKnowledgeRepository Protocol")


def test_business_layer_depends_only_on_repository_abstraction() -> None:
    violations = []
    for name in BUSINESS_LAYER:
        modules = _imported_modules(MARKET_DATA / name)
        bad = sorted(modules & FORBIDDEN_PERSISTENCE_MODULES)
        if bad:
            violations.append((name, bad))
        assert "shanhai_market_data.domain.repository" in modules, (
            f"{name} 必须依赖 MarketKnowledgeRepository 抽象"
        )
    assert not violations, f"业务层不得 import 具体存储实现: {violations}"
    print("[OK] 业务层 (api/acquisition/sync) 只依赖 Repository 抽象，不感知具体存储")


def main() -> None:
    test_in_memory_adapter_satisfies_repository_protocol()
    test_business_layer_depends_only_on_repository_abstraction()
    print("\nM3.3 Phase 1 Repository Boundary 测试全部通过 ✅")


if __name__ == "__main__":
    main()

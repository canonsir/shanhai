"""Market knowledge domain layer.

Holds the storage-agnostic boundary the business layer depends on. Nothing here
imports a database driver; adapters (in-memory now, SQLite / Postgres later) live
behind the ``MarketKnowledgeRepository`` Protocol defined in ``repository``.
"""

from shanhai_market_data.domain.repository import MarketKnowledgeRepository

__all__ = ["MarketKnowledgeRepository"]

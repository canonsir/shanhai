"""Identity Registry — the ``entity_identity_mapping`` table.

M2.5 Phase 1 makes external codes (ts_code / symbol) attributes, never
identities. Live identities are surrogate keys (``new_internal_id``). This
registry is the deterministic bridge between the two:

- External source mapping: ``(entity_type, source, external_id) -> internal_id``.
  Resolving the same external identifier always returns the same surrogate id,
  so the resolver stays deterministic without encoding the code into the id.
- Old -> new migration: legacy ts_code-derived ids are linked to the new
  surrogate under ``source="legacy"`` for traceability.
- Rollback: every mapping is retained on both a forward and a reverse index, so
  a surrogate id can recover all of its external/legacy ids and vice versa.

This module performs only deterministic lookups. No fuzzy matching, no AI
merge, no embeddings.
"""

from __future__ import annotations

from shanhai_market_data.identity import new_internal_id
from shanhai_market_data.models import IdentityMapping

LEGACY_SOURCE = "legacy"
DEFAULT_MIGRATION_VERSION = "m2.5.p1"


class IdentityRegistry:
    """In-memory ``entity_identity_mapping`` registry for the MVP runtime.

    The persistent counterpart lives in the database; this class keeps the same
    deterministic contract for the local-first foundation.
    """

    def __init__(self) -> None:
        self._forward: dict[tuple[str, str, str], str] = {}
        self._reverse: dict[str, list[IdentityMapping]] = {}
        self._mappings: list[IdentityMapping] = []

    def resolve_or_allocate(
        self,
        entity_type: str,
        source: str,
        external_id: str,
        *,
        migration_version: str = DEFAULT_MIGRATION_VERSION,
    ) -> str:
        """Return the surrogate id for an external identifier, allocating once.

        First call allocates a fresh surrogate via ``new_internal_id`` and
        records the mapping; later calls reuse it. This is what keeps the same
        ts_code resolving to the same internal id across runs in a process.
        """
        existing = self._forward.get((entity_type, source, external_id))
        if existing is not None:
            return existing
        internal_id = new_internal_id(entity_type)
        self._record(entity_type, internal_id, source, external_id, migration_version)
        return internal_id

    def link(
        self,
        entity_type: str,
        internal_id: str,
        source: str,
        external_id: str,
        *,
        migration_version: str = DEFAULT_MIGRATION_VERSION,
    ) -> None:
        """Attach an additional external/legacy id to an existing surrogate.

        Idempotent for an identical mapping; raises on a conflicting one so the
        registry never silently re-points a surrogate identity.
        """
        key = (entity_type, source, external_id)
        existing = self._forward.get(key)
        if existing is not None:
            if existing != internal_id:
                raise ValueError(
                    f"identity conflict for {key}: {existing} != {internal_id}"
                )
            return
        self._record(entity_type, internal_id, source, external_id, migration_version)

    def record_legacy_migration(
        self,
        entity_type: str,
        internal_id: str,
        legacy_id: str,
        *,
        migration_version: str = DEFAULT_MIGRATION_VERSION,
    ) -> None:
        """Record an old ts_code-derived id -> new surrogate id migration row."""
        self.link(
            entity_type,
            internal_id,
            LEGACY_SOURCE,
            legacy_id,
            migration_version=migration_version,
        )

    def internal_for(self, entity_type: str, source: str, external_id: str) -> str | None:
        """Forward lookup: external/legacy id -> surrogate id (or None)."""
        return self._forward.get((entity_type, source, external_id))

    def mappings_for(self, internal_id: str) -> tuple[IdentityMapping, ...]:
        """Reverse lookup: all external/legacy mappings for a surrogate id.

        Enables rollback — recover the legacy ids a surrogate replaced.
        """
        return tuple(self._reverse.get(internal_id, ()))

    def legacy_id_for(self, internal_id: str) -> str | None:
        """Return the legacy id a surrogate replaced, if migration was recorded."""
        for mapping in self._reverse.get(internal_id, ()):
            if mapping.source == LEGACY_SOURCE:
                return mapping.external_id
        return None

    def mappings(self) -> tuple[IdentityMapping, ...]:
        """All mapping rows in insertion order (the full registry snapshot)."""
        return tuple(self._mappings)

    def _record(
        self,
        entity_type: str,
        internal_id: str,
        source: str,
        external_id: str,
        migration_version: str,
    ) -> None:
        mapping = IdentityMapping(
            entity_type=entity_type,
            internal_id=internal_id,
            source=source,
            external_id=external_id,
            migration_version=migration_version,
        )
        self._forward[(entity_type, source, external_id)] = internal_id
        self._reverse.setdefault(internal_id, []).append(mapping)
        self._mappings.append(mapping)

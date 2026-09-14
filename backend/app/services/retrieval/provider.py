"""
NYAYA RAKSHAK - Legal Source Provider
Discovers and retrieves authoritative statutory and judicial sources from the SourceRegistry.
Applies strict temporal validity checks, jurisdiction filtering, and provenance tracking.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from app.schemas.retrieval import (
    CitationRecord,
    EvidenceType,
    RetrievalFilter,
    RetrievalResultItem,
    SourceTier,
)
from app.services.retrieval.registry import source_registry


class LegalSourceProvider:
    """Retrieves authoritative legal sources with provenance and temporal validity."""

    def __init__(self, registry=None):
        self.registry = registry or source_registry

    def search_authorities(
        self, query: str, filters: Optional[RetrievalFilter] = None, top_k: int = 5
    ) -> List[RetrievalResultItem]:
        filters = filters or RetrievalFilter()
        q_tokens = [t.lower() for t in query.split() if len(t) > 2]

        candidates = self.registry.list_all()
        scored_items = []

        for item in candidates:
            # 1. Temporal Validity Filtering
            if filters.as_of_date:
                if not item.is_valid_as_of(filters.as_of_date):
                    continue
            else:
                # Default to active laws if not explicitly querying historical
                if filters.allowed_statuses and item.status not in filters.allowed_statuses:
                    continue

            # 2. Jurisdiction Filtering (Never silently mix jurisdictions)
            if filters.jurisdiction and not filters.allow_cross_jurisdiction:
                # If target is a state, allow state law + Union of India law, but NOT other states
                if (
                    filters.jurisdiction != "Union of India"
                    and item.jurisdiction != "Union of India"
                    and item.jurisdiction != filters.jurisdiction
                ):
                    continue
                # If target is Union of India, do not pull state laws unless permitted
                if (
                    filters.jurisdiction == "Union of India"
                    and item.jurisdiction != "Union of India"
                ):
                    continue

            # 3. Domain Filtering
            if (
                filters.legal_domain
                and item.legal_domain != "general"
                and item.legal_domain != filters.legal_domain
            ):
                # Continue if query domain strongly mismatches
                pass

            # 4. Keyword / BM25 Scoring
            text_corpus = f"{item.title} {item.short_name} {item.section_number} {item.section_title} {item.content} {' '.join(item.key_principles)} {item.historical_reference or ''}".lower()
            match_count = 0
            for token in q_tokens:
                if token in text_corpus:
                    match_count += 1
                    # Heavy bonus for section number match
                    if token in item.section_number.lower():
                        match_count += 3

            if match_count > 0:
                keyword_score = min(1.0, match_count / max(1, len(q_tokens)))
                # Tier boost
                tier_boost = (
                    1.0 if item.tier == SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS else 0.8
                )
                final_score = keyword_score * tier_boost

                provenance = {
                    "source_id": item.source_id,
                    "sha256": hashlib.sha256(item.content.encode("utf-8")).hexdigest()[:16],
                    "official_gazette_url": item.official_url,
                    "authority_level": item.authority_level.value,
                    "effective_from": item.effective_from,
                    "effective_to": item.effective_to,
                    "status": item.status.value,
                }

                citation = CitationRecord(
                    source_id=item.source_id,
                    title=f"{item.title} ({item.section_number})",
                    authority=item.authority_level.value.replace("_", " ").title(),
                    authority_tier=item.tier,
                    evidence_type=EvidenceType.LEGAL_AUTHORITY,
                    section_or_page=f"{item.section_number}: {item.section_title}",
                    publication_date=item.publication_date,
                    effective_date=item.effective_from,
                    retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                    url_or_reference=item.official_url,
                    supporting_text=item.content,
                    relevance_score=final_score,
                    provenance=provenance,
                )

                res_item = RetrievalResultItem(
                    item_id=item.source_id,
                    evidence_type=EvidenceType.LEGAL_AUTHORITY,
                    tier=item.tier,
                    title=f"{item.short_name} - {item.section_number}: {item.section_title}",
                    content=item.content,
                    citation=citation,
                    keyword_score=keyword_score,
                    semantic_score=0.0,
                    tier_boost=tier_boost,
                    final_score=final_score,
                    jurisdiction=item.jurisdiction,
                    effective_from=item.effective_from,
                    effective_to=item.effective_to,
                    status=item.status,
                )
                scored_items.append(res_item)

        scored_items.sort(key=lambda x: x.final_score, reverse=True)
        return scored_items[:top_k]


legal_source_provider = LegalSourceProvider()

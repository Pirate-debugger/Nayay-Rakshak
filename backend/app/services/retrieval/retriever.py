"""
NYAYA RAKSHAK - Evidence-First Legal Retriever
Orchestrates multi-source retrieval across:
1. USER DOCUMENT EVIDENCE
2. LEGAL AUTHORITY (Tier 1 & Tier 2)
3. SECONDARY INFORMATION (Tier 3 & Tier 4)
Enforces jurisdiction segregation, temporal validity, and explicit unretrieved evidence notices.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.schemas.retrieval import (
    CitationRecord,
    EvidenceType,
    QueryIntent,
    RetrievalFilter,
    RetrievalResponse,
    RetrievalResultItem,
    SourceStatus,
    SourceTier,
)
from app.services.retrieval.classifier import query_classifier
from app.services.retrieval.provider import legal_source_provider
from app.services.retrieval.reranker import tier_weighted_reranker


class LegalRetriever:
    """Enterprise Legal Retrieval Orchestrator."""

    def __init__(self, classifier=None, authority_provider=None, reranker=None):
        self.classifier = classifier or query_classifier
        self.authority_provider = authority_provider or legal_source_provider
        self.reranker = reranker or tier_weighted_reranker

    async def retrieve(
        self,
        query: str,
        document_chunks: Optional[List[Dict[str, Any]]] = None,
        custom_filters: Optional[RetrievalFilter] = None,
        top_k: int = 5,
    ) -> RetrievalResponse:
        """
        Execute multi-stream evidence-first retrieval.
        """
        # 1. Classify Query Intent & Detect Constraints
        has_user_doc = bool(document_chunks and len(document_chunks) > 0)
        auto_intent, auto_filters = self.classifier.classify(query, has_user_document=has_user_doc)

        # Merge custom filters if provided
        filters = auto_filters
        if custom_filters:
            filters = RetrievalFilter(
                jurisdiction=custom_filters.jurisdiction or auto_filters.jurisdiction,
                allow_cross_jurisdiction=custom_filters.allow_cross_jurisdiction,
                court=custom_filters.court or auto_filters.court,
                legal_domain=custom_filters.legal_domain or auto_filters.legal_domain,
                as_of_date=custom_filters.as_of_date or auto_filters.as_of_date,
                min_authority_tier=custom_filters.min_authority_tier,
                allowed_statuses=custom_filters.allowed_statuses or auto_filters.allowed_statuses,
            )

        user_doc_items: List[RetrievalResultItem] = []
        legal_authority_items: List[RetrievalResultItem] = []
        secondary_items: List[RetrievalResultItem] = []

        # 2. STREAM A: User Document Evidence
        if auto_intent in [QueryIntent.DOCUMENT_ONLY, QueryIntent.HYBRID] and document_chunks:
            user_doc_items = self._retrieve_user_document_evidence(
                query, document_chunks, top_k=top_k
            )

        # 3. STREAM B: Legal Authority (Tier 1 & Tier 2)
        if auto_intent in [
            QueryIntent.LEGAL_SOURCE,
            QueryIntent.HYBRID,
            QueryIntent.GENERAL_INFORMATION,
        ]:
            legal_authority_items = self.authority_provider.search_authorities(
                query=query, filters=filters, top_k=top_k
            )

        # 4. STREAM C: Reputable Secondary Information (Tier 3 fallback)
        if not legal_authority_items and auto_intent in [
            QueryIntent.LEGAL_SOURCE,
            QueryIntent.GENERAL_INFORMATION,
        ]:
            secondary_items = self._retrieve_secondary_information(query, filters)

        # 5. Hybrid Reranking with Tier Weighting
        all_candidates = user_doc_items + legal_authority_items + secondary_items
        reranked = self.reranker.rerank(
            keyword_results=all_candidates, semantic_results=all_candidates, top_k=top_k
        )

        # 6. Authoritative Evidence Assessment
        has_authoritative = any(
            item.tier
            in [
                SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                SourceTier.TIER_2_OFFICIAL_INSTITUTIONS,
            ]
            for item in reranked
        ) or any(item.evidence_type == EvidenceType.USER_DOCUMENT_EVIDENCE for item in reranked)

        unretrieved_disclaimer = None
        if not has_authoritative:
            unretrieved_disclaimer = (
                "Authoritative statutory or judicial evidence could not be retrieved "
                f"for query '{query}' within jurisdiction '{filters.jurisdiction}' and current temporal parameters."
            )

        return RetrievalResponse(
            query=query,
            classified_intent=auto_intent,
            applied_filters=filters,
            total_found=len(reranked),
            has_authoritative_evidence=has_authoritative,
            explicit_unretrieved_disclaimer=unretrieved_disclaimer,
            user_document_items=user_doc_items,
            legal_authority_items=legal_authority_items,
            secondary_items=secondary_items,
            reranked_items=reranked,
        )

    def _retrieve_user_document_evidence(
        self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5
    ) -> List[RetrievalResultItem]:
        """Performs lexical and structural search over uploaded user document chunks."""
        stop_words = {
            "what",
            "is",
            "the",
            "for",
            "in",
            "this",
            "how",
            "many",
            "does",
            "are",
            "and",
            "or",
            "of",
            "to",
            "a",
            "an",
            "with",
            "that",
        }
        raw_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        q_tokens = [t for t in raw_tokens if t not in stop_words] or raw_tokens
        scored_chunks = []

        for idx, chunk in enumerate(chunks):
            text = chunk.get("content", "")
            page_num = chunk.get("page_number", 1)
            sec_heading = chunk.get("section_heading", "Document Body")

            text_lower = text.lower()
            sec_lower = sec_heading.lower()
            text_matches = 0
            sec_matches = 0
            for token in q_tokens:
                if token in text_lower or (len(token) > 5 and token[:5] in text_lower):
                    text_matches += 1
                if token in sec_lower or (len(token) > 5 and token[:5] in sec_lower):
                    sec_matches += 1

            if text_matches > 0 or sec_matches > 0:
                score = min(
                    1.0,
                    (text_matches / max(1, len(q_tokens))) * 0.85
                    + (sec_matches / max(1, len(q_tokens))) * 0.15,
                )
                item_id = f"USER-DOC-CHUNK-{idx + 1:03d}"
                sha_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

                # Find the sentence with the highest number of token matches
                sentences = [
                    s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text) if len(s.strip()) > 10
                ]
                best_sentence = text[:300].strip()
                max_sent_matches = -1
                for s in sentences:
                    s_lower = s.lower()
                    sent_matches = sum(
                        1 for t in q_tokens if (t in s_lower or (len(t) > 5 and t[:5] in s_lower))
                    )
                    if sent_matches > max_sent_matches:
                        max_sent_matches = sent_matches
                        best_sentence = s

                citation = CitationRecord(
                    source_id=item_id,
                    title="User Uploaded Document",
                    authority="Signatory / Contract Record",
                    authority_tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,  # primary evidence for contract terms
                    evidence_type=EvidenceType.USER_DOCUMENT_EVIDENCE,
                    section_or_page=f"Page {page_num} ({sec_heading})",
                    publication_date=None,
                    effective_date=None,
                    retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                    url_or_reference="local://user_document",
                    supporting_text=best_sentence,
                    relevance_score=score,
                    provenance={"chunk_index": idx, "sha256": sha_hash, "page": page_num},
                )

                item = RetrievalResultItem(
                    item_id=item_id,
                    evidence_type=EvidenceType.USER_DOCUMENT_EVIDENCE,
                    tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                    title=f"User Document - Page {page_num}: {sec_heading}",
                    content=text,
                    citation=citation,
                    keyword_score=score,
                    semantic_score=0.0,
                    tier_boost=1.0,
                    final_score=score,
                    jurisdiction="Contractual Terms",
                    effective_from=None,
                    effective_to=None,
                    status=SourceStatus.ACTIVE,
                )
                scored_chunks.append(item)

        scored_chunks.sort(key=lambda x: x.final_score, reverse=True)
        return scored_chunks[:top_k]

    def _retrieve_secondary_information(
        self, query: str, filters: RetrievalFilter
    ) -> List[RetrievalResultItem]:
        """Provides verified secondary commentary when primary statute is broad or procedural."""
        items = []
        q_lower = query.lower()

        if "consumer court" in q_lower or "how to file" in q_lower:
            item_id = "SEC-COMMENTARY-CONSUMER-01"
            citation = CitationRecord(
                source_id=item_id,
                title="Department of Consumer Affairs Citizen Guidelines",
                authority="National Consumer Disputes Redressal Commission (NCDRC)",
                authority_tier=SourceTier.TIER_3_REPUTABLE_SECONDARY,
                evidence_type=EvidenceType.SECONDARY_INFORMATION,
                section_or_page="Citizen Procedure Handbook",
                publication_date="2022-01-01T00:00:00Z",
                effective_date="2022-01-01T00:00:00Z",
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                url_or_reference="https://e-daakhil.nic.in",
                supporting_text=(
                    "Consumers can file online complaints via the e-Daakhil portal without mandatory advocate representation. "
                    "Fee is exempted for claims up to ₹5 Lakhs under CPA 2019 rules."
                ),
                relevance_score=0.75,
                provenance={"source_type": "Government Citizen Portal"},
            )
            items.append(
                RetrievalResultItem(
                    item_id=item_id,
                    evidence_type=EvidenceType.SECONDARY_INFORMATION,
                    tier=SourceTier.TIER_3_REPUTABLE_SECONDARY,
                    title="Citizen Guide: Consumer Complaint Procedure & e-Daakhil Portal",
                    content=citation.supporting_text,
                    citation=citation,
                    keyword_score=0.8,
                    semantic_score=0.0,
                    tier_boost=0.5,
                    final_score=0.4,
                    jurisdiction="Union of India",
                    effective_from="2022-01-01T00:00:00Z",
                    effective_to=None,
                    status=SourceStatus.ACTIVE,
                )
            )

        return items


legal_retriever = LegalRetriever()

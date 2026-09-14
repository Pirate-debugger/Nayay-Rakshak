"""
NYAYA RAKSHAK - Evidence-First Legal Retrieval Tests
Validates:
1. Multi-source separation: User Document Evidence vs Legal Authority vs Secondary Info
2. Source hierarchy: Tier 1 to Tier 4 weights
3. Query classification: document-only, legal-source, hybrid, general-information
4. Temporal filtering: BNS 2023 vs repealed IPC 1860
5. Strict jurisdiction isolation: Delhi vs Maharashtra tenancy laws
6. Provenance tracking: SHA-256 & official non-fabricated URLs
7. Explicit unretrieved disclaimer
8. IR evaluation benchmark execution (MRR, Precision, Recall, NDCG)
"""

import pytest

from app.schemas.retrieval import (
    EvidenceType,
    QueryIntent,
    SourceTier,
)
from app.services.retrieval.evaluator import STANDARD_LEGAL_BENCHMARKS, retrieval_evaluator
from app.services.retrieval.provider import legal_source_provider
from app.services.retrieval.registry import source_registry
from app.services.retrieval.reranker import tier_weighted_reranker
from app.services.retrieval.retriever import legal_retriever


@pytest.mark.asyncio
async def test_multi_stream_separation_hybrid():
    """Verifies that user document chunks and statutory authorities are clearly segregated."""
    user_chunks = [
        {
            "content": "Clause 8.1: The employee shall not join any competing software firm for 2 years post termination.",
            "page_number": 2,
            "section_heading": "Restrictive Covenants",
        }
    ]
    query = "Does my contract clause on non-compete violate Section 27 of Contract Act?"
    resp = await legal_retriever.retrieve(query=query, document_chunks=user_chunks, top_k=5)

    assert resp.classified_intent == QueryIntent.HYBRID
    assert len(resp.user_document_items) >= 1
    assert len(resp.legal_authority_items) >= 1

    # Check evidence types in segregated streams
    for item in resp.user_document_items:
        assert item.evidence_type == EvidenceType.USER_DOCUMENT_EVIDENCE
        assert item.citation.url_or_reference.startswith("local://")
        assert "chunk_index" in item.citation.provenance

    for item in resp.legal_authority_items:
        assert item.evidence_type == EvidenceType.LEGAL_AUTHORITY
        assert item.citation.url_or_reference.startswith("https://")
        assert "sha256" in item.citation.provenance


@pytest.mark.asyncio
async def test_document_only_query():
    """Verifies document-only query intent classification and retrieval."""
    user_chunks = [
        {
            "content": "Rent is payable on the 5th of each calendar month to the landlord.",
            "page_number": 1,
            "section_heading": "Rent Payment",
        },
        {
            "content": "Security deposit of ₹50,000 shall be maintained with lessor.",
            "page_number": 1,
            "section_heading": "Deposit",
        },
    ]
    query = "What is the due date for rent in my lease agreement?"
    resp = await legal_retriever.retrieve(query=query, document_chunks=user_chunks, top_k=3)

    assert resp.classified_intent == QueryIntent.DOCUMENT_ONLY
    assert len(resp.user_document_items) >= 1
    assert "5th of each calendar month" in resp.user_document_items[0].content


@pytest.mark.asyncio
async def test_legal_source_only_query():
    """Verifies statutory query routes to legal authority without requiring user documents."""
    query = "What constitutes cheating under Section 318 of BNS 2023?"
    resp = await legal_retriever.retrieve(query=query, document_chunks=None, top_k=3)

    assert resp.classified_intent == QueryIntent.LEGAL_SOURCE
    assert len(resp.legal_authority_items) >= 1
    top_hit = resp.reranked_items[0]
    assert "BNS-2023-SEC-318" in top_hit.item_id
    assert top_hit.tier == SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS


@pytest.mark.asyncio
async def test_temporal_filtering_bns_vs_ipc():
    """
    Verifies temporal filtering:
    - Current queries (2024+) retrieve active BNS 2023 and NOT repealed IPC 1860.
    - Historical queries (specifying IPC / before July 2024) retrieve IPC 1860.
    """
    # 1. Current query
    curr_query = "What is the penalty for cheating under current Indian law BNS?"
    resp_curr = await legal_retriever.retrieve(query=curr_query, top_k=5)
    item_ids_curr = [i.item_id for i in resp_curr.reranked_items]
    assert "BNS-2023-SEC-318" in item_ids_curr
    assert "IPC-1860-SEC-420" not in item_ids_curr

    # 2. Historical query
    hist_query = "What was the law for cheating under IPC before July 2024?"
    resp_hist = await legal_retriever.retrieve(query=hist_query, top_k=5)
    item_ids_hist = [i.item_id for i in resp_hist.reranked_items]
    assert "IPC-1860-SEC-420" in item_ids_hist


@pytest.mark.asyncio
async def test_strict_jurisdiction_isolation_delhi_vs_maharashtra():
    """
    CRITICAL: Never silently mix state jurisdictions.
    A Delhi tenancy query must NEVER retrieve Maharashtra Rent Control Act, and vice versa.
    """
    # 1. Delhi Query
    delhi_query = "Can a landlord evict a tenant in Delhi without court order?"
    resp_delhi = await legal_retriever.retrieve(query=delhi_query, top_k=5)
    delhi_ids = [i.item_id for i in resp_delhi.reranked_items]

    assert "DRCA-1958-SEC-14" in delhi_ids
    assert "MRCA-1999-SEC-15" not in delhi_ids, (
        "Maharashtra law was erroneously mixed into Delhi query!"
    )

    # 2. Maharashtra Query
    mumbai_query = (
        "What are the eviction rules for a tenant in Mumbai Maharashtra paying standard rent?"
    )
    resp_mumbai = await legal_retriever.retrieve(query=mumbai_query, top_k=5)
    mumbai_ids = [i.item_id for i in resp_mumbai.reranked_items]

    assert "MRCA-1999-SEC-15" in mumbai_ids
    assert "DRCA-1958-SEC-14" not in mumbai_ids, (
        "Delhi law was erroneously mixed into Maharashtra query!"
    )


@pytest.mark.asyncio
async def test_provenance_and_zero_fabricated_urls():
    """
    Ensures every retrieved statutory item contains genuine, non-fabricated URLs,
    verifiable SHA-256 provenance hashes, and official publication metadata.
    """
    sources = source_registry.list_all()
    assert len(sources) >= 10

    for s in sources:
        assert s.official_url.startswith("https://")
        assert any(
            domain in s.official_url
            for domain in [".gov.in", ".nic.in", "sci.gov.in", "bombayhighcourt.nic.in"]
        ), (
            f"Source {s.source_id} URL {s.official_url} is not an authentic official government/court domain!"
        )

        assert len(s.content) > 20
        assert len(s.key_principles) >= 1
        assert s.authority_level is not None
        assert s.tier in [
            SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
            SourceTier.TIER_2_OFFICIAL_INSTITUTIONS,
        ]


@pytest.mark.asyncio
async def test_explicit_unretrieved_evidence_disclaimer():
    """
    If no authoritative statutory source matches the query within jurisdiction and temporal constraints,
    retrieval MUST flag an explicit unretrieved disclaimer.
    """
    query = "XYZ quantum asteroid mining concessions regulatory authority"
    resp = await legal_retriever.retrieve(query=query, top_k=5)

    assert resp.has_authoritative_evidence is False
    assert resp.explicit_unretrieved_disclaimer is not None
    assert (
        "Authoritative statutory or judicial evidence could not be retrieved"
        in resp.explicit_unretrieved_disclaimer
    )


@pytest.mark.asyncio
async def test_tier_weighted_reranking():
    """
    Tests that Tier 1 (Official Statutes & Supreme Court) gets higher boost than secondary/web content.
    """
    kw_results = legal_source_provider.search_authorities("cheating BNS 2023", top_k=5)
    reranked = tier_weighted_reranker.rerank(kw_results, kw_results, top_k=5)

    assert len(reranked) > 0
    # Tier 1 should have tier_boost == 1.0
    for r in reranked:
        if r.tier == SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS:
            assert r.tier_boost == 1.0
        elif r.tier == SourceTier.TIER_2_OFFICIAL_INSTITUTIONS:
            assert r.tier_boost == 0.8

    # Verify descending ordering
    scores = [r.final_score for r in reranked]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_ir_evaluation_benchmark_execution():
    """
    Executes real retrieval benchmark queries and checks calculated IR metrics.
    No static or fake metrics.
    """
    metrics = await retrieval_evaluator.evaluate_benchmarks(
        benchmarks=STANDARD_LEGAL_BENCHMARKS, k_values=[1, 3, 5]
    )

    assert "mrr" in metrics
    assert "precision@1" in metrics
    assert "recall@5" in metrics
    assert "ndcg@5" in metrics

    # Verify performance exceeds acceptable thresholds on standard benchmarks
    assert metrics["mrr"] >= 0.7, f"MRR too low: {metrics['mrr']}"
    assert metrics["recall@5"] >= 0.8, f"Recall@5 too low: {metrics['recall@5']}"
    assert metrics["ndcg@5"] >= 0.7, f"NDCG@5 too low: {metrics['ndcg@5']}"

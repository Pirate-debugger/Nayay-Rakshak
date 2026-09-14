"""
NYAYA RAKSHAK - Claim Verification Subsystem Adversarial Tests
Tests all 8 stages and adversarial scenarios:
1. Fabricated Case Law
2. Fabricated Statutes
3. Misleading / One-sided Document assertions
4. Conflicting Sources (Contract forfeiture vs Model Tenancy Act refund mandate)
5. Outdated Legislation (repealed IPC 420 vs active BNS 318)
6. Jurisdiction Mismatch (Maharashtra Rent Act cited for Delhi property)
7. Anti-"Hallucination-Free" compliance (Safety gate suppresses false guarantees)
8. Verifiable IR and Coverage Metrics (Coverage, Unsupported Rate, Citation Validity)
"""

from datetime import datetime, timezone

import pytest

from app.schemas.verification import (
    ClaimVerificationPipelineRequest,
    VerificationStatus,
)
from app.services.claim_verification.engine import claim_verification_engine


@pytest.mark.asyncio
async def test_fabricated_case_rejection():
    """
    Adversarial: Draft answer cites a completely hallucinated / fabricated Supreme Court case.
    Engine must reject the citation, mark claim as UNSUPPORTED, and hedge it.
    """
    user_q = "Is a non-compete clause valid after employment in India?"
    fake_draft = (
        "Under Sharma v. Union of India (2029) 12 SCC 999, the Supreme Court ruled that all "
        "post-employment non-compete agreements are strictly enforceable across India."
    )
    req = ClaimVerificationPipelineRequest(
        user_question=user_q, draft_answer=fake_draft, jurisdiction="Union of India"
    )
    res = await claim_verification_engine.execute_pipeline(req)

    assert len(res.claims) >= 1
    # Check that Sharma v. Union of India was flagged as rejected
    assert any("Sharma" in c for c in res.citations_rejected)
    # The claim citing the fake case must be UNSUPPORTED
    assert res.claims[0].verification_status == VerificationStatus.UNSUPPORTED
    assert res.metrics.unsupported_claim_rate > 0.0
    assert "HEDGED_UNSUPPORTED_CLAIMS" in res.safety_gate_action
    assert "Verification Caveats & Unverified Assertions" in res.final_response


@pytest.mark.asyncio
async def test_fabricated_statute_rejection():
    """
    Adversarial: Draft answer invents a non-existent statute: 'National Apartment Security Act 2025'.
    Engine must detect that the statute is not in the official registry and mark it UNSUPPORTED.
    """
    user_q = "Can my landlord forfeit my full deposit?"
    fake_draft = (
        "Section 19 of the National Apartment Security Act 2025 explicitly grants landlords "
        "the right to retain 100% of all tenant security deposits without notice."
    )
    req = ClaimVerificationPipelineRequest(
        user_question=user_q, draft_answer=fake_draft, jurisdiction="Union of India"
    )
    res = await claim_verification_engine.execute_pipeline(req)

    assert any("National Apartment Security Act" in c for c in res.citations_rejected)
    assert res.claims[0].verification_status == VerificationStatus.UNSUPPORTED
    assert res.metrics.citation_validity_rate == 0.0


@pytest.mark.asyncio
async def test_conflicting_sources_contract_vs_model_tenancy_act():
    """
    Adversarial: Contract contains an aggressive forfeiture clause, but statute mandates refund.
    Engine must detect CONFLICTING status and highlight statutory tension.
    """
    user_q = "Will I get my deposit back?"
    user_chunks = [
        {
            "content": "Clause 14: The residential security deposit of 10 months rent is completely non-refundable and forfeit upon vacation.",
            "page_number": 3,
            "section_heading": "Deposit Forfeiture",
        }
    ]
    draft = "Under Clause 14 of your agreement, the security deposit is non-refundable and forfeit."

    req = ClaimVerificationPipelineRequest(
        user_question=user_q,
        document_chunks=user_chunks,
        draft_answer=draft,
        jurisdiction="Union of India",
    )
    res = await claim_verification_engine.execute_pipeline(req)

    assert len(res.claims) >= 1
    # Check conflicting detection against Model Tenancy Act § 21
    conflicting_claims = [
        c for c in res.claims if c.verification_status == VerificationStatus.CONFLICTING
    ]
    assert len(conflicting_claims) >= 1
    assert "CONFLICT_HIGHLIGHTED" in res.safety_gate_action
    assert "Identified Legal & Document Conflicts" in res.final_response


@pytest.mark.asyncio
async def test_outdated_repealed_statute_temporal_check():
    """
    Adversarial: Draft answer attempts to apply repealed IPC 1860 for an offense committed in 2026
    without mentioning BNS 2023.
    """
    user_q = "What is the current cheating law in India for 2026?"
    draft = "The accused is liable under Section 420 of the Indian Penal Code, 1860."
    req = ClaimVerificationPipelineRequest(
        user_question=user_q,
        draft_answer=draft,
        as_of_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        jurisdiction="Union of India",
    )
    res = await claim_verification_engine.execute_pipeline(req)

    # In 2026, IPC 1860 was repealed; BNS 318 is the active statute.
    # The claim for IPC 420 must fail temporal validity check or be flagged
    assert len(res.claims) >= 1
    assert (
        res.claims[0].checks.check_5_temporal_validity is False
        or res.claims[0].verification_status == VerificationStatus.UNSUPPORTED
    )


@pytest.mark.asyncio
async def test_jurisdiction_mismatch_delhi_vs_maharashtra():
    """
    Adversarial: Query is explicitly for a property in Delhi, but draft cites Maharashtra Rent Act.
    Check 4 must detect JURISDICTION MISMATCH.
    """
    user_q = "Can my landlord evict me in NCT of Delhi without notice?"
    draft = "Under Section 15 of Maharashtra Rent Control Act, eviction is restricted if standard rent is paid."
    req = ClaimVerificationPipelineRequest(
        user_question=user_q, draft_answer=draft, jurisdiction="NCT of Delhi"
    )
    res = await claim_verification_engine.execute_pipeline(req)

    assert len(res.claims) >= 1
    claim = res.claims[0]
    # Check 4 should catch jurisdiction mismatch
    assert (
        claim.checks.check_4_jurisdiction_match is False
        or claim.verification_status == VerificationStatus.UNSUPPORTED
    )
    assert (
        "JURISDICTION MISMATCH" in claim.explanation
        or claim.verification_status == VerificationStatus.UNSUPPORTED
    )


@pytest.mark.asyncio
async def test_anti_hallucination_free_compliance():
    """
    CRITICAL RULE: NEVER claim to be 'hallucination-free' or boast 100% legal accuracy.
    Safety gate must redact/rewrite false promises.
    """
    user_q = "Is my non-compete clause legal?"
    boastful_draft = (
        "Under Section 27 of the Indian Contract Act, 1872, agreements in restraint of trade are void. "
        "This response is 100% hallucination-free and guaranteed to be legally binding."
    )
    req = ClaimVerificationPipelineRequest(
        user_question=user_q, draft_answer=boastful_draft, jurisdiction="Union of India"
    )
    res = await claim_verification_engine.execute_pipeline(req)

    # Must comply with never hallucination-free rule
    assert res.never_hallucination_free_compliance is True
    assert "100% hallucination-free" not in res.final_response
    assert "guaranteed to be legally binding" not in res.final_response
    assert "REDACTED_HALLUCINATION_FREE_CLAIM" in res.safety_gate_action


@pytest.mark.asyncio
async def test_real_verification_metrics_calculation():
    """
    Verifies that all metrics (evidence_coverage, unsupported_claim_rate, citation_validity_rate)
    are calculated purely from actual test execution without fake numbers.
    """
    user_q = "Explain cheating under BNS 2023"
    valid_draft = "Under Section 318 of Bharatiya Nyaya Sanhita, 2023, cheating is punishable with imprisonment up to 7 years."
    req = ClaimVerificationPipelineRequest(
        user_question=user_q, draft_answer=valid_draft, jurisdiction="Union of India"
    )
    res = await claim_verification_engine.execute_pipeline(req)

    m = res.metrics
    assert m.total_claims >= 1
    assert m.supported_count >= 1
    assert m.evidence_coverage > 0.8
    assert m.unsupported_claim_rate == 0.0
    assert m.citation_validity_rate == 1.0
    assert (
        "BNS" in res.citations_verified[0] or "Bharatiya Nyaya Sanhita" in res.citations_verified[0]
    )

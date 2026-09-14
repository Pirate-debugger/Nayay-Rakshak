"""
NYAYA RAKSHAK - Adversarial Risk Engine Test Suite
Tests evasive phrasing, camouflaged clauses, boundary edge cases,
ungrounded AI hallucination rejection, and mandatory language hedging.
"""

import pytest

from app.ai.base import BaseAIProvider
from app.schemas.risk import (
    RiskCategory,
)
from app.services.risk_engine import risk_engine


# Mock AI that attempts to hallucinate risks without grounded evidence
class HallucinatingMockAIProvider(BaseAIProvider):
    async def analyze_document(self, text: str, title: str):
        return {}

    async def answer_question(self, question: str, chunks):
        return {}

    async def verify_claim(self, claim: str, chunks):
        return {}

    async def compare_documents(self, base_title, base_text, target_title, target_text):
        return {}

    async def interpret_clause(self, clause_text: str, deterministic_facts):
        return {
            "risks": [
                # 1. Hallucinated risk with fictitious quote NOT in text
                {
                    "title": "Criminal Fraud Clause Detected",
                    "category": "FINANCIAL",
                    "severity": "CRITICAL",
                    "evidence_quote": "This company will steal all your life savings immediately.",
                    "finding": "Fraudulent criminal conspiracy",
                    "plain_language_explanation": "You will be robbed.",
                    "why_it_matters": "Total theft.",
                    "affected_party": "Citizen",
                },
                # 2. Grounded risk with genuine quote that exists in text
                {
                    "title": "Illegal Penalty Clause",  # unhedged title to test hedging normalizer
                    "category": "FINANCIAL",
                    "severity": "HIGH",
                    "evidence_quote": "flat penalty of INR 1,000 per day",
                    "finding": "Daily flat penalty charge detected.",
                    "plain_language_explanation": "Daily charges accumulate rapidly.",
                    "why_it_matters": "Increases debt burden.",
                    "affected_party": "Tenant",
                },
            ]
        }


# =====================================================================
# 1. EVASIVE PHRASING & OBFUSCATED LEGALESE
# =====================================================================


@pytest.mark.asyncio
async def test_evasive_uncapped_liability_phrasing():
    evasive_text = (
        "Notwithstanding anything contained in this agreement or any exhibit hereto, "
        "in no event shall the Lessor be constrained by any monetary ceiling, cap, or limitation of liability."
    )
    res = await risk_engine.analyze_document_risks(evasive_text)
    lia_risks = [r for r in res.risks if r.category == RiskCategory.LIABILITY]
    assert len(lia_risks) >= 1
    assert lia_risks[0].rule_id == "RULE-LIA-001"


@pytest.mark.asyncio
async def test_evasive_short_notice_phrasing():
    evasive_text = "The Company reserves the prerogative to terminate the engagement forthwith without prior intimation."
    res = await risk_engine.analyze_document_risks(evasive_text)
    tim_risks = [r for r in res.risks if r.category == RiskCategory.TIME_DEADLINE]
    assert len(tim_risks) >= 1
    assert tim_risks[0].rule_id == "RULE-TIM-001"


# =====================================================================
# 2. CAMOUFLAGED CLAUSES (BURIED IN BOILERPLATE)
# =====================================================================


@pytest.mark.asyncio
async def test_camouflaged_penalty_in_miscellaneous():
    document_text = (
        "1. PREMISES: Flat in Delhi.\n\n"
        "2. MISCELLANEOUS & GENERAL PROVISIONS:\n"
        "The tenant agrees to an unconditional daily penalty of Rs. 2,000 per day of delay and agrees to waive all claims."
    )
    res = await risk_engine.analyze_document_risks(document_text)
    pen_risks = [r for r in res.risks if r.category == RiskCategory.FINANCIAL]
    assert len(pen_risks) >= 1
    # Check that is_camouflaged flag was raised
    assert any(r.is_camouflaged for r in res.risks)


# =====================================================================
# 3. SUBTLE BOUNDARY & EDGE CASES
# =====================================================================


@pytest.mark.asyncio
async def test_notice_boundary_cases():
    # 6 days triggers sub-7 day notice rule
    text_6_days = "The landlord may terminate on 6 days notice."
    res_6 = await risk_engine.analyze_document_risks(text_6_days)
    assert any(r.rule_id == "RULE-TIM-001" for r in res_6.risks)

    # 15 days is standard commercial notice and should NOT trigger sub-7 day notice rule
    text_15_days = (
        "The landlord may terminate by providing 15 days written notice with dispute resolution."
    )
    res_15 = await risk_engine.analyze_document_risks(text_15_days)
    assert not any(r.rule_id == "RULE-TIM-001" for r in res_15.risks)


@pytest.mark.asyncio
async def test_interest_percentage_boundary_cases():
    # 18% triggers penal interest rule
    text_18 = "Late payments shall incur late penalty interest of 18% per annum."
    res_18 = await risk_engine.analyze_document_risks(text_18)
    assert any(r.rule_id == "RULE-FIN-001" for r in res_18.risks)

    # 12% is commercial lending standard and should NOT trigger penal interest rule
    text_12 = "Late payments shall incur late interest of 12% per annum simple interest."
    res_12 = await risk_engine.analyze_document_risks(text_12)
    assert not any(r.rule_id == "RULE-FIN-001" for r in res_12.risks)


# =====================================================================
# 4. UNGROUNDED AI HALLUCINATION REJECTION
# =====================================================================


@pytest.mark.asyncio
async def test_strict_ai_hallucination_rejection():
    # Document contains realistic lease terms
    text = "The Lessee shall pay monthly rent of INR 40,000 and flat penalty of INR 1,000 per day if delayed."
    hallucinating_ai = HallucinatingMockAIProvider()

    res = await risk_engine.analyze_document_risks(document_text=text, ai_provider=hallucinating_ai)

    # Assert that the hallucinated risk was strictly dropped
    risk_titles = [r.title.lower() for r in res.risks]
    assert not any("steal all your life savings" in t or "criminal fraud" in t for t in risk_titles)

    # Assert that the ungrounded rejection is recorded in audit_trail
    audit_statuses = [a.get("status") for a in res.audit_trail]
    assert "REJECTED_UNGROUNDED_AI_FINDING" in audit_statuses


# =====================================================================
# 5. MANDATORY LANGUAGE HEDGING COMPLIANCE
# =====================================================================


@pytest.mark.asyncio
async def test_language_hedging_across_all_risks():
    sample_text = (
        "The Lessee covenants not to work for any competitor globally for 24 months post termination. "
        "The Lessor may terminate at will without assigning any reason whatsoever. "
        "The security deposit shall be 5 months rent, non-refundable. "
        "All disputes subject to sole arbitrator appointed solely by company."
    )
    res = await risk_engine.analyze_document_risks(sample_text)
    assert len(res.risks) >= 3

    hedging_phrases = ["potential concern", "worth reviewing", "appears broader than"]

    for r in res.risks:
        title_lower = r.title.lower()
        # Verify title contains hedging prefix
        has_hedging = any(p in title_lower for p in hedging_phrases)
        assert has_hedging, f"Title lacks mandatory hedging: {r.title}"

        # Verify no risk claims absolute illegality
        assert "is illegal" not in title_lower
        assert "is legally invalid" not in title_lower
        assert "is void" not in title_lower


# =====================================================================
# 6. AUDIT TRAIL VERIFICATION
# =====================================================================


@pytest.mark.asyncio
async def test_audit_trail_completeness():
    text = "The employee agrees to a 24-month non-compete restriction."
    res = await risk_engine.analyze_document_risks(text)
    assert len(res.audit_trail) > 0
    for entry in res.audit_trail:
        assert "status" in entry
        assert "timestamp" in entry

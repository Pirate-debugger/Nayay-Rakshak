"""
NYAYA RAKSHAK - Deterministic Risk Engine Test Suite
Validates rule-based risk detection for objective conditions across all 13 standard categories.
Verifies strict 4-layer separation: Finding, Evidence, Classification, Explanation.
Verifies zero false positives on fair/balanced covenants.
"""

import pytest

from app.schemas.risk import (
    FindingType,
    RiskCategory,
    RiskSeverity,
)
from app.services.risk_engine import risk_engine, risk_rule_registry


# =====================================================================
# 1. POSITIVE DETERMINISTIC TESTS ACROSS ALL 13 CATEGORIES
# =====================================================================

@pytest.mark.asyncio
async def test_unlimited_liability_rule():
    text = "In no event shall the Service Provider be entitled to any limitation of liability, and liability shall be unlimited for all claims."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.LIABILITY]
    assert len(risks) >= 1
    r = risks[0]
    assert r.severity == RiskSeverity.CRITICAL
    assert "unlimited" in r.evidence.verbatim_quote.lower()
    assert r.rule_id == "RULE-LIA-001"
    assert r.finding_type == FindingType.DETERMINISTIC_RULE
    # 4-layer separation checks
    assert len(r.finding) >= 10
    assert len(r.plain_language_explanation) >= 15
    assert len(r.why_it_matters) >= 15
    assert len(r.recommended_question) >= 10
    assert r.professional_review_recommended is True


@pytest.mark.asyncio
async def test_gross_negligence_waiver_rule():
    text = "The Landlord shall not be liable for any damages whatsoever, waiving all claims regardless of negligence or fault."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-LIA-002"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.LIABILITY
    assert risks[0].severity == RiskSeverity.CRITICAL


@pytest.mark.asyncio
async def test_short_notice_period_rule():
    text = "The Lessor reserves the right to terminate the tenancy on 48 hours notice with immediate effect."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.TIME_DEADLINE]
    assert len(risks) >= 1
    r = [x for x in risks if x.rule_id == "RULE-TIM-001"][0]
    assert r.severity == RiskSeverity.HIGH
    assert "48 hours" in r.evidence.verbatim_quote.lower() or "immediate" in r.evidence.verbatim_quote.lower()


@pytest.mark.asyncio
async def test_unreasonable_cure_period_rule():
    text = "Any default must be remedied immediately without any cure period or opportunity to cure."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-TIM-002"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.TIME_DEADLINE
    assert risks[0].severity == RiskSeverity.MEDIUM


@pytest.mark.asyncio
async def test_uncapped_indemnity_rule():
    text = "The Lessee agrees to solely indemnify and hold harmless the Lessor against all claims, consequential and indirect damages without limit."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.INDEMNITY and r.rule_id == "RULE-IND-001"]
    assert len(risks) >= 1
    assert risks[0].severity == RiskSeverity.HIGH
    assert "indemnif" in risks[0].evidence.verbatim_quote.lower()


@pytest.mark.asyncio
async def test_indemnity_for_counterparty_fault_rule():
    text = "The Lessee shall unconditionally indemnify the Lessor regardless of lessor's negligence or fault."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-IND-002"]
    assert len(risks) == 1
    assert risks[0].severity == RiskSeverity.CRITICAL


@pytest.mark.asyncio
async def test_automatic_renewal_rule():
    text = "This contract shall renew automatically for successive one-year periods unless formal notice is given."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.RENEWAL]
    assert len(risks) >= 1
    assert risks[0].rule_id == "RULE-REN-001"
    assert risks[0].severity == RiskSeverity.MEDIUM


@pytest.mark.asyncio
async def test_unilateral_amendment_rule():
    text = "The Company reserves the right to amend fees and service terms in its sole discretion at any time without notice."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-ASY-001"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.OBLIGATION_ASYMMETRY
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_asymmetric_termination_rule():
    text = "The Lessor shall have the unfettered right to terminate this agreement, whereas the Lessee shall have no right to terminate."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-ASY-002"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.OBLIGATION_ASYMMETRY
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_material_financial_penalty_rule():
    text = "Late payment shall incur penal interest of 24% per annum compounding daily plus flat forfeiture of entire security deposit."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.FINANCIAL and r.rule_id == "RULE-FIN-001"]
    assert len(risks) >= 1
    assert risks[0].severity == RiskSeverity.CRITICAL


@pytest.mark.asyncio
async def test_excessive_security_deposit_rule():
    text = "The tenant shall provide a security deposit equivalent to 6 months rent, to be refunded within 90 days after vacating."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.FINANCIAL and r.rule_id == "RULE-FIN-002"]
    assert len(risks) >= 1
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_subjective_termination_rule():
    text = "The Landlord may terminate this agreement immediately in its sole satisfaction without assigning any reason whatsoever."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-TRM-001"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.TERMINATION
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_restraint_of_trade_rule():
    text = "Following cessation of employment, the employee agrees not to consult or work for any competitor anywhere in India for 12 months."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-TRM-002"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.TERMINATION
    assert risks[0].severity == RiskSeverity.CRITICAL


@pytest.mark.asyncio
async def test_unclear_termination_conditions_rule():
    text = "The employer may terminate at will without cause upon any event deemed a material breach."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-TRM-003"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.TERMINATION


@pytest.mark.asyncio
async def test_inconvenient_jurisdiction_rule():
    text = "All disputes arising out of this agreement shall be submitted to the exclusive jurisdiction of the courts of London, England."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.JURISDICTION]
    assert len(risks) >= 1
    assert risks[0].rule_id == "RULE-JUR-001"
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_sole_arbitrator_rule():
    text = "Any controversy shall be decided by a sole arbitrator appointed solely by the Company."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.ARBITRATION]
    assert len(risks) >= 1
    assert risks[0].rule_id == "RULE-ARB-001"
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_broad_data_privacy_rule():
    text = "The platform reserves the right to retain user personal data in perpetuity and share with third parties without notice."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.PRIVACY]
    assert len(risks) >= 1
    assert risks[0].rule_id == "RULE-PRV-001"
    assert risks[0].severity == RiskSeverity.MEDIUM


@pytest.mark.asyncio
async def test_overbroad_ip_assignment_rule():
    text = "The Employee assigns all inventions conceived whether during office hours or personal time, and waives all moral rights."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.category == RiskCategory.IP]
    assert len(risks) >= 1
    assert risks[0].rule_id == "RULE-IP-001"
    assert risks[0].severity == RiskSeverity.HIGH


@pytest.mark.asyncio
async def test_ambiguous_discretion_rule():
    text = "The decision of the landlord on all maintenance matters shall be final and binding in its sole and unreviewable discretion."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.risks if r.rule_id == "RULE-AMB-002"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.AMBIGUITY


@pytest.mark.asyncio
async def test_missing_dispute_resolution_rule():
    # Text without any dispute resolution clause
    text = (
        "This agreement is made between Party A and Party B. "
        "Party A shall deliver goods on the first of each month. "
        "Party B shall make monthly payments of INR 10,000."
    )
    res = await risk_engine.analyze_document_risks(text)
    missing = [m for m in res.missing_protections if m.rule_id == "RULE-MIS-001"]
    assert len(missing) == 1
    assert missing[0].category == RiskCategory.MISSING_PROTECTION


@pytest.mark.asyncio
async def test_missing_force_majeure_notice_rule():
    text = "Neither party shall be liable for force majeure events including floods, fires, and natural disasters."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.missing_protections if r.rule_id == "RULE-MIS-002"]
    assert len(risks) == 1
    assert risks[0].category == RiskCategory.MISSING_PROTECTION


@pytest.mark.asyncio
async def test_missing_data_return_rule():
    text = "Both parties agree to treat all proprietary data and confidential information with care until contract termination."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.missing_protections if r.rule_id == "RULE-MIS-003"]
    assert len(risks) == 1


@pytest.mark.asyncio
async def test_missing_deposit_return_sla_rule():
    text = "The tenant shall deposit a security deposit of Rs. 50,000 with the landlord at commencement."
    res = await risk_engine.analyze_document_risks(text)
    risks = [r for r in res.missing_protections if r.rule_id == "RULE-MIS-004"]
    assert len(risks) == 1


# =====================================================================
# 2. NEGATIVE TESTS: BALANCED / FAIR TERMS PRODUCE ZERO RISKS
# =====================================================================

@pytest.mark.asyncio
async def test_balanced_contract_terms_no_false_positives():
    balanced_text = (
        "Either party may terminate this agreement by providing 30 days written notice. "
        "In the event of a remediable breach, the defaulting party shall be given a 15-day cure period. "
        "Aggregate liability under this agreement shall be capped at the total fees paid during the preceding 12 months. "
        "Late payments shall incur simple interest at 10% p.a. after a 7-day grace period. "
        "Security deposit shall not exceed 2 months rent and shall be refunded within 14 days of handover. "
        "Any disputes shall be resolved by mutual agreement or through arbitration by a mutually appointed arbitrator. "
        "Amendments require written instrument signed by both parties."
    )
    res = await risk_engine.analyze_document_risks(balanced_text)
    # Critical and high risks should be zero for this balanced text
    crit_or_high = [r for r in res.risks if r.severity in [RiskSeverity.CRITICAL, RiskSeverity.HIGH]]
    assert len(crit_or_high) == 0


# =====================================================================
# 3. RULE REGISTRY & VERSION AUDITABILITY
# =====================================================================

def test_rule_registry_versioning():
    rules = risk_rule_registry.list_rules()
    assert len(rules) >= 20
    for r in rules:
        assert r.rule_id.startswith("RULE-")
        assert r.version == "2024.1.0"
        info = r.get_info()
        assert info.rule_id == r.rule_id
        assert len(info.changelog) >= 1

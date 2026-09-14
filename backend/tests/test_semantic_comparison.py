import pytest
from app.schemas.comparison import (
    ComparisonCategory,
    DifferenceDimension,
    MaterialityLevel,
)
from app.services.comparison.engine import SemanticComparisonEngine, compare_legal_documents


@pytest.fixture
def comp_engine():
    return SemanticComparisonEngine()


def test_identical_contracts(comp_engine):
    """Scenario 1: Identical contracts must yield 100% IDENTICAL findings with 0 material differences."""
    contract_text = """
1. PREMISES AND TERM: Landlord leases apartment 4B for a term of 11 months commencing 1st Jan 2024.
2. RENT: Tenant shall pay a monthly rent of ₹25,000 on or before the 5th day of each calendar month.
3. SECURITY DEPOSIT: Tenant deposits ₹50,000 as refundable security deposit to be refunded within 14 days of vacating.
4. TERMINATION: Either party may terminate this agreement by providing 30 days prior written notice.
5. GOVERNING LAW: This agreement is governed by the laws of India and subject to courts in Delhi.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Original Lease",
        base_text=contract_text,
        target_document_id=102,
        target_title="Exact Duplicate Lease",
        target_text=contract_text
    )

    assert res.summary.net_risk_verdict == "IDENTICAL"
    assert res.summary.target_high_risks == 0
    assert len(res.findings) >= 5
    assert all(f.category == ComparisonCategory.IDENTICAL for f in res.findings)
    assert res.structural_diff.structural_alignment_score == 1.0
    assert res.structural_diff.reordered_clause_count == 0


def test_reordered_clauses(comp_engine):
    """Scenario 2: Clauses placed in different section order in Document B must still match accurately."""
    doc_a = """
1. RENT: The monthly rent shall be ₹25,000 payable on 5th of each month.
2. TERMINATION: Either party may terminate with 30 days written notice.
3. GOVERNING LAW: Disputes shall be subject to the jurisdiction of courts in Delhi.
""".strip()

    doc_b = """
1. GOVERNING LAW: Disputes shall be subject to the jurisdiction of courts in Delhi.
2. RENT: The monthly rent shall be ₹25,000 payable on 5th of each month.
3. TERMINATION: Either party may terminate with 30 days written notice.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Doc A (Standard Order)",
        base_text=doc_a,
        target_document_id=102,
        target_title="Doc B (Reordered)",
        target_text=doc_b
    )

    assert res.structural_diff.aligned_clause_count == 3
    assert res.structural_diff.reordered_clause_count > 0
    # Every clause should be matched as IDENTICAL despite reordering
    assert all(f.category == ComparisonCategory.IDENTICAL for f in res.findings)
    assert res.summary.target_high_risks == 0


def test_wording_changes_without_semantic_shift(comp_engine):
    """Scenario 3: Superficial phrasing/cosmetic changes must be categorized as SIMILAR, not MODIFIED."""
    doc_a = """
1. NOTICE: Any official notice under this agreement must be delivered in writing via registered post or courier to the registered address.
2. CLEANLINESS: The tenant covenants to keep the residential premises in a clean, hygienic, and tenantable condition throughout the tenancy.
""".strip()

    doc_b = """
1. NOTICE: All notices given under this contract shall be provided in written form dispatched by registered mail or courier service to the noted address.
2. CLEANLINESS: The occupant agrees to maintain the dwelling in an orderly, sanitary, and well-kept state at all times during the lease period.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Draft A",
        base_text=doc_a,
        target_document_id=102,
        target_title="Draft B (Stylistic Variations)",
        target_text=doc_b
    )

    # Must classify as SIMILAR (cosmetic variation) and NOT trigger high-risk warnings
    assert res.summary.net_risk_verdict == "BALANCED"
    assert res.summary.target_high_risks == 0
    categories = [f.category for f in res.findings]
    assert all(c in [ComparisonCategory.SIMILAR, ComparisonCategory.IDENTICAL] for c in categories)


def test_numeric_changes(comp_engine):
    """Scenario 4: Numeric changes in rent amount or interest rate must be detected as MODIFIED / FINANCIAL."""
    doc_a = """
1. RENT: Monthly rent shall be ₹20,000 payable on the 1st of every calendar month.
2. LATE PAYMENT: Delayed payments shall incur simple interest at the rate of 1% per annum after a 7-day grace period.
""".strip()

    doc_b = """
1. RENT: Monthly rent shall be ₹25,000 payable on the 1st of every calendar month.
2. LATE PAYMENT: Delayed payments shall incur interest at the rate of 18% per annum after a 7-day grace period.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Doc A (Original Terms)",
        base_text=doc_a,
        target_document_id=102,
        target_title="Doc B (Increased Price & Rate)",
        target_text=doc_b
    )

    fin_findings = [f for f in res.findings if f.dimension == DifferenceDimension.FINANCIAL]
    assert len(fin_findings) >= 2
    assert all(f.category == ComparisonCategory.MODIFIED for f in fin_findings)
    # Interest rate spike to 18% is CRITICAL materiality
    interest_finding = next(f for f in fin_findings if "18" in f.difference_explanation or "interest" in f.difference_explanation.lower())
    assert interest_finding.materiality == MaterialityLevel.CRITICAL
    assert interest_finding.document_a_evidence is not None
    assert interest_finding.document_b_evidence is not None
    assert res.summary.net_risk_verdict == "TARGET_MORE_HARSH"


def test_deadline_changes(comp_engine):
    """Scenario 5: Shortened notice period or delayed deposit refund must be detected as MODIFIED / DEADLINE."""
    doc_a = """
1. TERMINATION NOTICE: Either party may terminate this agreement by giving 30 days prior written notice.
2. DEPOSIT REFUND: The security deposit shall be refunded within 14 days following peaceful handover.
""".strip()

    doc_b = """
1. TERMINATION NOTICE: Either party may terminate this agreement by giving 7 days prior written notice.
2. DEPOSIT REFUND: The security deposit shall be refunded within 90 days following peaceful handover.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Doc A",
        base_text=doc_a,
        target_document_id=102,
        target_title="Doc B (Short Notice & Delayed Refund)",
        target_text=doc_b
    )

    deadline_findings = [f for f in res.findings if f.dimension == DifferenceDimension.DEADLINE]
    assert len(deadline_findings) >= 2
    assert all(f.category == ComparisonCategory.MODIFIED for f in deadline_findings)
    # Notice reduction from 30 days to 7 days is CRITICAL or MATERIAL
    notice_finding = next(f for f in deadline_findings if "7" in f.difference_explanation)
    assert notice_finding.materiality in [MaterialityLevel.CRITICAL, MaterialityLevel.MATERIAL]


def test_negation_and_rights_changes(comp_engine):
    """Scenario 6: Negation inversions ('may' vs 'shall not') must be categorized as CONFLICTING."""
    doc_a = """
1. EARLY TERMINATION: Tenant may terminate this lease at any time upon providing written notice.
2. ASSIGNMENT: Tenant may assign or sublet the premises with prior written consent of landlord.
""".strip()

    doc_b = """
1. EARLY TERMINATION: Tenant shall not terminate this lease at any time prior to the expiry of the lock-in period.
2. ASSIGNMENT: Tenant may not assign or sublet the premises under any circumstances.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Doc A (Permissive Rights)",
        base_text=doc_a,
        target_document_id=102,
        target_title="Doc B (Negation & Restrictions)",
        target_text=doc_b
    )

    conflicting = [f for f in res.findings if f.category == ComparisonCategory.CONFLICTING]
    assert len(conflicting) >= 1
    assert any("terminate" in f.difference_explanation.lower() or "shall not" in f.difference_explanation.lower() for f in conflicting)
    assert all(f.materiality == MaterialityLevel.CRITICAL for f in conflicting)
    assert res.summary.net_risk_verdict == "TARGET_MORE_HARSH"


def test_liability_changes(comp_engine):
    """Scenario 7: Insertion of uncapped liability or blanket indemnity must be flagged under LIABILITY."""
    doc_a = """
1. LIMITATION OF LIABILITY: Each party's maximum aggregate liability under this agreement shall be capped at the total rent paid during the preceding 3 months.
""".strip()

    doc_b = """
1. LIMITATION OF LIABILITY: Tenant agrees to unlimited liability and shall indemnify and hold harmless the Landlord against all claims, damages and losses regardless of cause.
""".strip()

    res = comp_engine.compare(
        base_document_id=101,
        base_title="Doc A (Capped)",
        base_text=doc_a,
        target_document_id=102,
        target_title="Doc B (Uncapped & Indemnity)",
        target_text=doc_b
    )

    liab_findings = [f for f in res.findings if f.dimension == DifferenceDimension.LIABILITY]
    assert len(liab_findings) >= 1
    assert liab_findings[0].category == ComparisonCategory.MODIFIED
    assert liab_findings[0].materiality == MaterialityLevel.CRITICAL
    assert "unlimited" in liab_findings[0].difference_explanation.lower() or "indemnif" in liab_findings[0].difference_explanation.lower()


def test_completely_different_documents(comp_engine):
    """Scenario 8: Completely different documents (e.g. Lease vs Employment) must be detected as such."""
    lease_text = """
1. LEASE OF RESIDENTIAL PREMISES: Landlord hereby demises to Tenant residential premises at Flat 101, Green Park, New Delhi.
2. MONTHLY RENT: The rent is ₹30,000 payable on 1st of every calendar month.
3. SECURITY DEPOSIT: Tenant pays ₹60,000 as refundable deposit.
4. PEACEFUL POSSESSION: Tenant shall enjoy quiet possession of premises without interruption.
""".strip()

    employment_text = """
1. EMPLOYMENT AND DUTIES: Company employs Employee as Senior Software Architect reporting to Engineering VP.
2. ANNUAL CTC: The gross annual remuneration shall be INR 28,00,000 subject to TDS deduction.
3. INTELLECTUAL PROPERTY: Employee hereby assigns all patentable inventions and software code to Company.
4. CONFIDENTIALITY: Employee shall strictly preserve non-disclosure of Company trade secrets.
""".strip()

    res = comp_engine.compare(
        base_document_id=201,
        base_title="Residential Lease Agreement",
        base_text=lease_text,
        target_document_id=202,
        target_title="Tech Employment Agreement",
        target_text=employment_text
    )

    assert res.summary.net_risk_verdict == "COMPLETELY_DIFFERENT_DOCUMENTS"
    assert res.structural_diff.structural_alignment_score < 0.25
    assert res.structural_diff.missing_in_b_count >= 3
    assert res.structural_diff.new_in_b_count >= 3
    assert any("completely different" in w.lower() for w in res.summary.critical_warnings)


def test_ocr_noise_robustness(comp_engine):
    """Scenario 9: Minor OCR artifacts (1 vs l, 0 vs O, smart quotes) must still match as IDENTICAL/SIMILAR."""
    clean_text = """
1. RENT PAYMENT: Tenant shall pay ₹15,000 per month on or before 10th of each month.
2. SECURITY DEPOSIT: Refundable security deposit of ₹30,000 shall be returned within 14 days.
3. JURISDICTION: Courts in Delhi NCR shall have exclusive jurisdiction.
""".strip()

    # Text corrupted with typical OCR scanner noise
    ocr_corrupted_text = """
1. RENT PAYMENT: Tenant shall pay ₹l5,OOO per month on or before l0th of each month.
2. SECURITY DEPOSIT: “Refundable security deposit of ₹3O,OOO shall be returned within l4 days.”
3. JURISDICTION: Courts in Delhi NCR shall have exclusive jurisdiction—subject to law.
""".strip()

    res = comp_engine.compare(
        base_document_id=301,
        base_title="Clean Born-Digital Document",
        base_text=clean_text,
        target_document_id=302,
        target_title="Scanned OCR Text with Typographic Noise",
        target_text=ocr_corrupted_text
    )

    assert res.structural_diff.aligned_clause_count == 3
    assert res.summary.net_risk_verdict in ["IDENTICAL", "BALANCED"]
    assert res.summary.target_high_risks == 0
    # None of the clauses should be falsely flagged as MODIFIED with penalties
    assert all(f.category in [ComparisonCategory.IDENTICAL, ComparisonCategory.SIMILAR] for f in res.findings)

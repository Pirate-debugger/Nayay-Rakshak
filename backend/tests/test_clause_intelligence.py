import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas.clause_intelligence import (
    ClauseSemanticInterpretation,
    DeterministicFacts,
    EvidenceLocation,
    StructuredClauseRecord,
)
from app.services.clause_intelligence import (
    analyze_clause_structured,
    enforce_deterministic_immutability,
    process_document_clauses,
)
from app.services.clause_taxonomy import (
    BaseTaxonomyPlugin,
    TaxonomyRegistry,
    taxonomy_registry,
)
from app.services.deterministic_extractor import (
    extract_currencies,
    extract_dates,
    extract_deterministic_facts,
    extract_durations,
    extract_percentages,
    extract_section_numbers,
)

# =====================================================================
# 1. Deterministic Extraction Tests
# =====================================================================


def test_deterministic_currencies():
    text = (
        "The Tenant shall pay a monthly rent of ₹35,000 along with Rs. 5,000 maintenance. "
        "A refundable security deposit of INR 1,50,000 or 5 Lakhs is required. "
        "The project cost is estimated at 2.5 Crores. Foreign consultancy is $1,200 or USD 3,500."
    )
    currencies = extract_currencies(text)
    assert len(currencies) >= 6

    # Verify rupee amounts
    amounts = [c["amount"] for c in currencies]
    assert 35000.0 in amounts
    assert 5000.0 in amounts
    assert 150000.0 in amounts
    assert 500000.0 in amounts  # 5 Lakhs
    assert 25000000.0 in amounts  # 2.5 Crores
    assert 1200.0 in amounts
    assert 3500.0 in amounts


def test_deterministic_percentages():
    text = (
        "Any delay in payment shall incur interest at 18% p.a. compounded monthly. "
        "Brokerage fee is fixed at 2% flat. Stamp duty is 6.5% per annum on the total consideration."
    )
    pcts = extract_percentages(text)
    assert len(pcts) == 3

    val_map = {p["value"]: p["frequency"] for p in pcts}
    assert 18.0 in val_map
    assert "p.a." in val_map[18.0].lower()
    assert 2.0 in val_map
    assert 6.5 in val_map


def test_deterministic_durations():
    text = (
        "Notice of termination must be served 30 days prior. The lock-in period is 11 months. "
        "The lease may be renewed for 3 years. Defect rectification must occur within 48 hours or 2 weeks."
    )
    durations = extract_durations(text)
    assert len(durations) == 5

    count_map = {d["count"]: d for d in durations}
    assert count_map[30]["unit"] == "days"
    assert count_map[30]["days_equivalent"] == 30.0

    assert count_map[11]["unit"] == "months"
    assert count_map[11]["days_equivalent"] == 330.0

    assert count_map[3]["unit"] == "years"
    assert count_map[3]["days_equivalent"] == 1095.0

    assert count_map[48]["unit"] == "hours"
    assert count_map[48]["days_equivalent"] == 2.0

    assert count_map[2]["unit"] == "weeks"
    assert count_map[2]["days_equivalent"] == 14.0


def test_deterministic_dates():
    text = (
        "This Agreement is executed on 15th August 2024 and effective from 01/09/2024 until 2025-08-31. "
        "The handover inspection shall take place on October 2, 2024."
    )
    dates = extract_dates(text)
    assert len(dates) >= 4
    date_strs = [d["date_string"] for d in dates]
    assert any("15 August 2024" in s for s in date_strs)
    assert any("01/09/2024" in s for s in date_strs)
    assert any("2025-08-31" in s for s in date_strs)
    assert any("2 October 2024" in s for s in date_strs)


def test_deterministic_sections():
    text = (
        "Pursuant to Section 4.1 (Rent) and Clause 12 (Indemnification), subject to Article II "
        "and Schedule A attached hereto, as well as Part B."
    )
    sections = extract_section_numbers(text)
    assert len(sections) == 5
    refs = [s["full_reference"] for s in sections]
    assert "Section 4.1" in refs
    assert "Clause 12" in refs
    assert "Article II" in refs
    assert "Schedule A" in refs
    assert "Part B" in refs


# =====================================================================
# 2. All 8 Domain Taxonomies & Plugin Extensibility Tests
# =====================================================================


def test_all_8_taxonomy_categories_present():
    categories = taxonomy_registry.list_categories()
    category_ids = {c["id"] for c in categories}
    expected = {
        "rental",
        "employment",
        "nda",
        "consumer",
        "service_agreements",
        "loan_finance",
        "privacy_policies",
        "terms_and_conditions",
    }
    assert expected.issubset(category_ids), f"Missing categories: {expected - category_ids}"


def test_taxonomy_classification_and_risk_evaluation():
    # 1. Rental with 18% compounding penalty
    rental_text = "The tenant shall pay monthly rent. Delay in rent incurs 18% compounding interest per annum."
    cat, _ = taxonomy_registry.classify_clause(rental_text)
    assert cat == "rental"
    facts = extract_deterministic_facts(rental_text)
    plugin = taxonomy_registry.get("rental")
    risk, is_unfair, stat_ref, _ = plugin.evaluate_covenant_risk(rental_text, facts)
    assert risk == "CRITICAL"
    assert is_unfair is True
    assert "Model Tenancy Act" in stat_ref

    # 2. Employment with post-employment non-compete
    emp_text = "Employee shall not engage in competing business post-termination for a period of 12 months."
    cat, _ = taxonomy_registry.classify_clause(emp_text)
    assert cat == "employment"
    plugin = taxonomy_registry.get("employment")
    risk, is_unfair, stat_ref, _ = plugin.evaluate_covenant_risk(emp_text, {})
    assert risk == "CRITICAL"
    assert is_unfair is True
    assert "27" in stat_ref  # Section 27 Indian Contract Act

    # 3. NDA
    nda_text = "The receiving party shall hold all confidential and proprietary trade secret materials in secrecy."
    cat, _ = taxonomy_registry.classify_clause(nda_text)
    assert cat == "nda"

    # 4. Consumer with unfair waiver
    consumer_text = "Goods are sold as is without any warranty and no refund under any circumstances is permitted."
    cat, _ = taxonomy_registry.classify_clause(consumer_text)
    assert cat == "consumer"
    plugin = taxonomy_registry.get("consumer")
    risk, is_unfair, stat_ref, _ = plugin.evaluate_covenant_risk(consumer_text, {})
    assert risk == "HIGH"
    assert is_unfair is True
    assert "2(46)" in stat_ref

    # 5. Service Agreement
    service_text = "The service provider shall deliver the software deliverables in accordance with the SLA milestone."
    cat, _ = taxonomy_registry.classify_clause(service_text)
    assert cat == "service_agreements"

    # 6. Loan / Finance
    loan_text = (
        "The borrower shall pay monthly EMI towards the principal loan and floating rate interest."
    )
    cat, _ = taxonomy_registry.classify_clause(loan_text)
    assert cat == "loan_finance"

    # 7. Privacy Policy
    privacy_text = "Personal data shall be collected by the data fiduciary only upon explicit consent of the data principal under DPDP Act."
    cat, _ = taxonomy_registry.classify_clause(privacy_text)
    assert cat == "privacy_policies"

    # 8. Terms and Conditions
    tc_text = "The company reserves the right to modify terms at any time without notice and suspend user account."
    cat, _ = taxonomy_registry.classify_clause(tc_text)
    assert cat == "terms_and_conditions"
    plugin = taxonomy_registry.get("terms_and_conditions")
    risk, is_unfair, _, _ = plugin.evaluate_covenant_risk(tc_text, {})
    assert is_unfair is True


def test_custom_taxonomy_plugin_extensibility():
    """Verify third parties or new modules can dynamically register domain plugins."""

    class IntellectualPropertyPlugin(BaseTaxonomyPlugin):
        @property
        def category_id(self) -> str:
            return "ip_royalty"

        @property
        def display_name(self) -> str:
            return "IP Licensing & Royalty"

        @property
        def description(self) -> str:
            return "Patent and copyright licensing, royalty calculations, cross-licensing."

        @property
        def keywords(self):
            return ["patent", "licensor", "licensee", "royalty", "sublicense", "patent pool"]

        def evaluate_covenant_risk(self, clause_text: str, deterministic_facts):
            if "exclusive worldwide perpetual royalty-free" in clause_text.lower():
                return (
                    "HIGH",
                    True,
                    "Copyright Act, 1957 § 19",
                    "Perpetual royalty-free grant may conflict with statutory author royalties.",
                )
            return ("LOW", False, None, None)

    custom_registry = TaxonomyRegistry()
    custom_registry.register(IntellectualPropertyPlugin())

    clause = "The Licensor grants to Licensee an exclusive worldwide perpetual royalty-free license to the Patent."
    cat, name = custom_registry.classify_clause(clause)
    assert cat == "ip_royalty"
    assert name == "IP Licensing & Royalty"

    plugin = custom_registry.get("ip_royalty")
    risk, is_unfair, stat_ref, _ = plugin.evaluate_covenant_risk(clause, {})
    assert risk == "HIGH"
    assert is_unfair is True
    assert "Copyright Act" in stat_ref


# =====================================================================
# 3. Deterministic Immutability Enforcement Tests
# =====================================================================


def test_deterministic_immutability_prevents_ai_overwrite():
    """
    CRITICAL REQUIREMENT:
    'Do not let AI silently overwrite deterministic values.'
    If an AI model hallucinates or provides altered monetary values, dates, durations, or percentages,
    the deterministic extractions must take precedence and NEVER be silently overwritten.
    """
    raw_text = (
        "Section 5. Payment: The Tenant agrees to pay ₹45,000 per month by 5th September 2024. "
        "Any delay beyond 7 days incurs 18% p.a. interest."
    )
    raw_facts = extract_deterministic_facts(raw_text)

    # Simulate an AI response trying to alter the numbers:
    # - AI changed monetary value to $500
    # - AI altered deadline to 3 days
    # - AI changed penalty rate to 5%
    erroneous_ai_semantics = {
        "parties_affected": ["Tenant", "Landlord"],
        "obligations": ["Pay monthly amount"],
        "rights": [],
        "prohibitions": [],
        "conditions": ["Delayed payment"],
        "triggers": ["Failure to pay on time"],
        "deadlines": ["Within 3 days"],  # AI altered 7 days -> 3 days
        "monetary_values": ["USD 500"],  # AI altered ₹45,000 -> USD 500
        "penalties": ["Late fee of 5%"],  # AI altered 18% -> 5%
        "termination_conditions": [],
        "jurisdiction": "New Delhi",
        "governing_law": "Laws of India",
        "arbitration": None,
        "confidentiality": None,
        "indemnity": None,
        "liability": None,
        "intellectual_property": None,
        "renewal": None,
        "dispute_resolution": None,
        "privacy_data_terms": None,
    }

    # Pass through immutability enforcement
    clean_interpretation = enforce_deterministic_immutability(raw_facts, erroneous_ai_semantics)

    # 1. Deterministic currency MUST be preserved
    assert any("45,000" in m for m in clean_interpretation.monetary_values)

    # 2. Deterministic duration (7 days) and date (5 September 2024) MUST be preserved in deadlines
    deadline_text = " ".join(clean_interpretation.deadlines)
    assert "7 days" in deadline_text
    assert "5 September 2024" in deadline_text

    # 3. Deterministic penalty percentage (18%) MUST be preserved in penalties
    penalty_text = " ".join(clean_interpretation.penalties)
    assert "18.0%" in penalty_text or "18%" in penalty_text


# =====================================================================
# 4. Strict Schema & Pydantic Validation Tests
# =====================================================================


def test_strict_schema_forbids_extra_fields():
    """Verify that StructuredClauseRecord and ClauseSemanticInterpretation forbid unexpected keys."""
    with pytest.raises(ValidationError):
        ClauseSemanticInterpretation(
            parties_affected=["Tenant"],
            unexpected_hallucinated_field="invalid",  # Must fail because extra="forbid"
        )

    with pytest.raises(ValidationError):
        StructuredClauseRecord(
            clause_id="C-01",
            section="Section 1",
            title="Title",
            page=1,
            clause_type="rental_covenant",
            category="rental",
            original_text="Raw clause text",
            simplified_explanation="Simple",
            evidence_location=EvidenceLocation(
                page_number=1, char_start=0, char_end=10, quote_snippet="Raw"
            ),
            deterministic_facts=DeterministicFacts(),
            structured_interpretation=ClauseSemanticInterpretation(),
            extraction_confidence=0.95,
            interpretation_confidence=0.90,
            unauthorized_extra_key="forbidden",  # Must fail
        )


def test_structured_clause_record_properties_and_flat_export():
    """Verify all 25+ detected legal fields are accessible via properties and flat export."""
    raw_text = (
        "Clause 12. Deliverables and Indemnity: The Service Provider shall deliver software deliverables according to the SLA, "
        "and shall indemnify Client up to ₹2,00,000 against liabilities. Governed by the laws of India. Courts at Bengaluru shall have jurisdiction. "
        "Subject to Arbitration and Conciliation Act 1996."
    )
    rec = analyze_clause_structured("C-12", raw_text, page_number=2, section_name="Clause 12")

    # Check top-level properties
    assert rec.clause_id == "C-12"
    assert rec.page == 2
    assert rec.section == "Clause 12"
    assert "Indemnity" in rec.title or "Covenant" in rec.title
    assert rec.category == "service_agreements"
    assert rec.original_text == raw_text
    assert len(rec.simplified_explanation) > 10
    assert rec.extraction_confidence > 0.9
    assert rec.interpretation_confidence > 0.9

    # Check semantic properties accessible directly
    assert isinstance(rec.parties_affected, list)
    assert isinstance(rec.obligations, list)
    assert isinstance(rec.rights, list)
    assert isinstance(rec.prohibitions, list)
    assert isinstance(rec.conditions, list)
    assert isinstance(rec.triggers, list)
    assert isinstance(rec.deadlines, list)
    assert any("200,000" in m or "INR" in m for m in rec.monetary_values)
    assert rec.indemnity is not None
    assert rec.jurisdiction is not None and "Bengaluru" in rec.jurisdiction
    assert rec.governing_law is not None and "India" in rec.governing_law
    assert rec.arbitration is not None

    # Check flat dictionary export
    flat = rec.to_full_dict()
    assert flat["clause_id"] == "C-12"
    assert "monetary_values" in flat
    assert "jurisdiction" in flat
    assert "arbitration" in flat
    assert "obligations" in flat


# =====================================================================
# 5. Synthetic Legal Documents Benchmarks
# =====================================================================

SYNTHETIC_RESIDENTIAL_LEASE = """
RESIDENTIAL LEASE AGREEMENT

1. Demised Premises & Term
The Landlord hereby leases to the Tenant the residential apartment situated at Flat 402, Green Meadows, Bengaluru for a term of 11 months commencing from 1st October 2024.

2. Monthly Rent & Maintenance
The Tenant shall pay a monthly rent of ₹30,000 on or before the 5th day of each calendar month. The Tenant shall also pay ₹3,000 monthly maintenance.

3. Refundable Security Deposit
The Tenant has deposited with the Landlord a sum of INR 1,50,000 as refundable security deposit. The Landlord shall refund this deposit within 14 days of peaceful handover of vacant possession.

4. Default & Late Payment Penalty
In the event rent is delayed past the 5th of any month, the Tenant shall pay a compounding penalty of 18% p.a. calculated daily, along with a flat late charge of ₹500.

5. Termination & Notice
Either party may terminate this Agreement by providing 30 days written notice to the other party. In the event Tenant vacates without notice, one month rent shall be forfeited.

6. Governing Law & Dispute Resolution
This Agreement shall be governed by the laws of India. Any disputes arising hereunder shall be subject to the exclusive jurisdiction of the Courts at Bengaluru.
"""

SYNTHETIC_EMPLOYMENT_AGREEMENT = """
EMPLOYMENT OFFER & APPOINTMENT LETTER

Clause 1. Designation & Compensation
The Company is pleased to appoint you as Senior Software Engineer at an annual CTC of 15 Lakhs. You will be on probation for a period of 90 days.

Clause 2. Notice Period & Termination
During probation, either party may terminate employment with 15 days notice. Post confirmation, the notice period shall be 60 days.

Clause 3. Intellectual Property Assignment
All software codes, inventions, and patentable discoveries conceived during employment belong exclusively to the Company as work for hire.

Clause 4. Non-Compete & Restraint of Trade
The Employee agrees not to join or consult for any competing business post-termination for a period of 12 months within India.

Clause 5. Confidential Information
The Employee shall maintain strict confidentiality regarding source codes and proprietary algorithms in perpetuity.
"""


def test_synthetic_residential_lease_end_to_end():
    records = process_document_clauses(SYNTHETIC_RESIDENTIAL_LEASE, default_page=1)
    assert len(records) >= 5

    # Check Rent clause
    rent_clause = next((r for r in records if "30,000" in r.original_text), None)
    assert rent_clause is not None
    assert rent_clause.category == "rental"
    assert any("30,000" in m for m in rent_clause.monetary_values)

    # Check Security Deposit clause
    deposit_clause = next((r for r in records if "1,50,000" in r.original_text), None)
    assert deposit_clause is not None
    assert any("150,000" in m for m in deposit_clause.monetary_values)

    # Check Late Penalty clause (must be flagged as unfair / unconscionable under Model Tenancy Act)
    penalty_clause = next((r for r in records if "18%" in r.original_text), None)
    assert penalty_clause is not None
    assert penalty_clause.is_unfair is True
    assert penalty_clause.risk_level in ["HIGH", "CRITICAL", "SEVERE"]
    assert penalty_clause.statutory_cross_reference is not None

    # Check Jurisdiction clause
    jur_clause = next(
        (
            r
            for r in records
            if "Courts at Bengaluru" in r.original_text or "jurisdiction" in r.original_text.lower()
        ),
        None,
    )
    assert jur_clause is not None
    assert jur_clause.jurisdiction is not None
    assert "Bengaluru" in jur_clause.jurisdiction


def test_synthetic_employment_agreement_end_to_end():
    records = process_document_clauses(SYNTHETIC_EMPLOYMENT_AGREEMENT, default_page=1)
    assert len(records) >= 4

    # Check CTC clause
    ctc_clause = next((r for r in records if "15 Lakhs" in r.original_text), None)
    assert ctc_clause is not None
    assert any(
        "15,000,000" in m or "15000000" in m or "1,500,000" in m for m in ctc_clause.monetary_values
    )

    # Check Non-compete clause (must be flagged void under Section 27 Indian Contract Act)
    non_compete = next((r for r in records if "non-compete" in r.original_text.lower()), None)
    assert non_compete is not None
    assert non_compete.is_unfair is True
    assert "27" in (non_compete.statutory_cross_reference or "")


# =====================================================================
# 6. API Endpoint Integration Tests
# =====================================================================


@pytest.mark.asyncio
async def test_api_single_clause_extract_endpoint(client: AsyncClient, auth_headers: dict):
    payload = {
        "clause_text": "Clause 8. Jurisdiction: This Agreement shall be governed by the laws of India and Courts at Mumbai shall have exclusive jurisdiction.",
        "clause_id": "C-08",
        "page_number": 3,
        "section_name": "Clause 8. Jurisdiction",
    }
    resp = await client.post("/api/v1/analysis/clause/extract", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["clause_id"] == "C-08"
    assert data["page"] == 3
    assert data["structured_interpretation"]["governing_law"] == "Laws of India"
    assert "Mumbai" in (data["structured_interpretation"]["jurisdiction"] or "")
    assert data["extraction_confidence"] >= 0.95

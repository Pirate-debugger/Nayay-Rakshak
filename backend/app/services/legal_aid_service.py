from typing import Dict, List

from app.schemas.legal_aid import (
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    LegalAidResource,
)

LEGAL_AID_RESOURCES: List[LegalAidResource] = [
    LegalAidResource(
        id="NALSA-NAT",
        name="National Legal Services Authority (NALSA)",
        organization_type="NALSA",
        jurisdiction="All India (National)",
        phone_or_helpline="15100 (National Legal Aid Toll-Free Helpline)",
        portal_url="https://nalsa.gov.in",
        description="Apex statutory authority established under the Legal Services Authorities Act, 1987 to provide free competent legal services to the weaker sections of society.",
        services_offered=[
            "Free advocate appointment in Supreme Court, High Courts, and Subordinate Courts",
            "Payment of court fees, process fees, and advocate charges",
            "Free supply of certified copies and translation of legal documents",
            "Pre-litigation mediation and settlement",
        ],
        physical_address="B-Block, Additional Building Complex, Supreme Court of India, New Delhi - 110001",
    ),
    LegalAidResource(
        id="DSLSA-DEL",
        name="Delhi State Legal Services Authority (DSLSA)",
        organization_type="SLSA",
        jurisdiction="Delhi NCR",
        phone_or_helpline="1516 / +91-11-23384781",
        portal_url="https://dslsa.org",
        description="Provides free legal counsel, legal literacy clinics, and victim compensation across all 11 Delhi districts.",
        services_offered=[
            "District Legal Services Clinics across all Delhi Court complexes (Tis Hazari, Saket, Patiala House, Karkardooma, Rohini, Dwarka)",
            "Free representation in rent, civil, matrimonial, and criminal disputes",
            "Permanent Lok Adalats for public utility disputes",
        ],
        physical_address="Central Office, Rouse Avenue Court Complex, Pandit Deen Dayal Upadhyaya Marg, New Delhi - 110002",
    ),
    LegalAidResource(
        id="KSLSA-BLR",
        name="Karnataka State Legal Services Authority (KSLSA)",
        organization_type="SLSA",
        jurisdiction="Karnataka",
        phone_or_helpline="1800-425-90900 / +91-80-22111714",
        portal_url="https://kslsa.kar.nic.in",
        description="Coordinates legal aid and Mega Lok Adalats across Bengaluru Urban, Bengaluru Rural, and all Karnataka districts.",
        services_offered=[
            "Free advocate representation in High Court of Karnataka and District Courts",
            "Pre-litigation counseling for employment and tenant disputes",
            "Lok Adalat settlement facilitation",
        ],
        physical_address="Nyaya Degula, 1st Floor, Siddaiah Road, Bangalore - 560027",
    ),
    LegalAidResource(
        id="MSLSA-MUM",
        name="Maharashtra State Legal Services Authority (MSLSA)",
        organization_type="SLSA",
        jurisdiction="Maharashtra",
        phone_or_helpline="+91-22-22691358 / 15100",
        portal_url="https://legalservices.maharashtra.gov.in",
        description="Legal aid authority serving Mumbai, Pune, Nagpur, and all Maharashtra districts.",
        services_offered=[
            "Free counsel panel for civil, tenancy, and criminal trials",
            "Lok Adalat dispute resolution",
            "Legal aid clinics in prisons and talukas",
        ],
        physical_address="P.W.D. Building, High Court Personnel Dept, Fort, Mumbai - 400032",
    ),
    LegalAidResource(
        id="TELE-LAW",
        name="Tele-Law (Ministry of Law and Justice, GoI)",
        organization_type="TELE_LAW",
        jurisdiction="All India (Rural & Urban)",
        phone_or_helpline="Access via nearest Common Service Centre (CSC) or Mobile App",
        portal_url="https://www.tele-law.in",
        description="Connects citizens in rural, remote, and urban areas directly to panel lawyers via video conferencing and telephone at Common Service Centres.",
        services_offered=[
            "Free pre-litigation legal advice from panel lawyers",
            "Multilingual consultation (Hindi, English, regional languages)",
            "Referral to DLSA if formal litigation is needed",
        ],
    ),
    LegalAidResource(
        id="NCH-CONS",
        name="National Consumer Helpline (NCH - Ministry of Consumer Affairs)",
        organization_type="CONSUMER_FORUM",
        jurisdiction="All India",
        phone_or_helpline="1915 / SMS to 8800001915",
        portal_url="https://consumerhelpline.gov.in",
        description="National statutory redressal mechanism for consumer disputes, unfair contracts, warranty refusal, and e-commerce fraud.",
        services_offered=[
            "Instant registration of consumer grievances against service providers and sellers",
            "Pre-litigation mediation with registered convergence companies",
            "Guidance for filing on e-Daakhil (online consumer commission)",
        ],
    ),
    LegalAidResource(
        id="EDAAKHIL",
        name="e-Daakhil Portal (Consumer Commission Online Filing)",
        organization_type="CONSUMER_FORUM",
        jurisdiction="All India",
        phone_or_helpline="Available 24x7 online",
        portal_url="https://edaakhil.nic.in",
        description="Official Government of India portal for filing consumer complaints online before District, State, and National Consumer Commissions without physical presence.",
        services_offered=[
            "Online complaint submission and digital evidence upload",
            "Online payment of nominal consumer court fees",
            "Digital case status tracking and order downloads",
        ],
    ),
    LegalAidResource(
        id="CYBER-1930",
        name="National Cyber Crime Reporting Portal",
        organization_type="CYBER_HELPLINE",
        jurisdiction="All India",
        phone_or_helpline="1930 (Helpline for Financial Cyber Fraud)",
        portal_url="https://cybercrime.gov.in",
        description="Centralized portal by Ministry of Home Affairs to report financial cyber fraud, online cheating, identity theft, and unauthorized transactions.",
        services_offered=[
            "Immediate freezing of stolen funds in transit (within Golden Hour)",
            "Registration of formal cyber FIR",
            "Assistance with digital evidence documentation",
        ],
    ),
]

STATE_INCOME_LIMITS: Dict[str, float] = {
    "delhi": 300000.0,
    "karnataka": 300000.0,
    "maharashtra": 300000.0,
    "tamil nadu": 300000.0,
    "uttar pradesh": 300000.0,
    "west bengal": 300000.0,
    "default": 300000.0,
}


def evaluate_free_legal_aid_eligibility(req: EligibilityCheckRequest) -> EligibilityCheckResponse:
    reasons = []
    eligible = False
    state_key = req.state.strip().lower()
    income_limit = STATE_INCOME_LIMITS.get(state_key, STATE_INCOME_LIMITS["default"])

    # Statutory entitlements under Section 12 of Legal Services Authorities Act, 1987
    if req.is_woman_or_child:
        eligible = True
        reasons.append(
            "Entitled as a Woman or Child under Section 12(c) of the Legal Services Authorities Act, 1987, irrespective of income."
        )

    if req.is_sc_or_st:
        eligible = True
        reasons.append(
            "Entitled as a member of Scheduled Caste (SC) or Scheduled Tribe (ST) under Section 12(a)."
        )

    if req.is_disabled:
        eligible = True
        reasons.append("Entitled as a person with disability under Section 12(d) of the Act.")

    if req.is_trafficking_victim:
        eligible = True
        reasons.append("Entitled as a victim of human trafficking or beggar under Section 12(g).")

    if req.is_in_custody:
        eligible = True
        reasons.append("Entitled as a person in custody or protective home under Section 12(h).")

    if req.is_industrial_workman:
        eligible = True
        reasons.append("Entitled as an industrial workman under Section 12(e).")

    if not eligible:
        if req.annual_income <= income_limit:
            eligible = True
            reasons.append(
                f"Eligible under Section 12(h) based on annual income of ₹{req.annual_income:,.2f}, which is below the ₹{income_limit:,.2f} state threshold for {req.state.title()}."
            )
        else:
            reasons.append(
                f"Annual income (₹{req.annual_income:,.2f}) exceeds the free legal aid threshold of ₹{income_limit:,.2f} for {req.state.title()}. However, you can still access Tele-Law for low-cost advice or Lok Adalats for dispute settlement."
            )

    checklist = [
        "Identity proof (Aadhaar, Voter ID, or Ration Card)",
        "Income certificate (if applying under the income criteria)",
        "Category certificate (if applying under SC/ST or Disability criteria)",
        "Copy of the legal document, notice, or agreement in dispute",
        "Chronological timeline of key events and communications",
    ]

    return EligibilityCheckResponse(
        is_eligible_for_free_legal_aid=eligible,
        governing_statute="Legal Services Authorities Act, 1987 (Act No. 39 of 1987)",
        statutory_clause="Section 12 - Criteria for Giving Legal Services",
        eligibility_reasons=reasons,
        annual_income_limit_for_state=income_limit,
        recommended_authorities=LEGAL_AID_RESOURCES[:4],
        action_checklist=checklist,
    )

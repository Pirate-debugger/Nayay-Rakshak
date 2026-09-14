from typing import List, Optional

from pydantic import BaseModel


class StatuteProvision(BaseModel):
    statute: str
    section: str
    title: str
    description: str
    historical_reference: Optional[str] = None  # e.g., "Formerly Section 420 IPC"
    key_principles: List[str]
    citizen_advice: str


INDIAN_STATUTORY_REGISTRY: List[StatuteProvision] = [
    # Criminal Law Transitions: BNS 2023 vs IPC
    StatuteProvision(
        statute="Bharatiya Nyaya Sanhita, 2023 (BNS)",
        section="Section 318",
        title="Cheating",
        description="Cheating and dishonestly inducing delivery of property.",
        historical_reference="Formerly Section 420 of the Indian Penal Code (IPC)",
        key_principles=[
            "Deceiving any person fraudulently or dishonestly",
            "Inducing delivery of property or consent to retain property",
            "Punishable with imprisonment up to 7 years and fine",
        ],
        citizen_advice="If someone deceived you into transferring money or property with fraudulent intent, file a police complaint referencing BNS Section 318.",
    ),
    StatuteProvision(
        statute="Bharatiya Nyaya Sanhita, 2023 (BNS)",
        section="Section 303",
        title="Theft",
        description="Dishonest taking of any movable property out of the possession of any person without consent.",
        historical_reference="Formerly Section 378 & 379 of IPC",
        key_principles=[
            "Moving property in order to take it dishonestly",
            "Lack of consent of possessor",
        ],
        citizen_advice="Report theft immediately at the nearest police station or file an e-FIR.",
    ),
    StatuteProvision(
        statute="Bharatiya Nyaya Sanhita, 2023 (BNS)",
        section="Section 356",
        title="Defamation",
        description="Making or publishing imputations intending to harm reputation.",
        historical_reference="Formerly Section 499 & 500 of IPC",
        key_principles=[
            "Harming reputation of person",
            "Includes community service as alternative penalty",
        ],
        citizen_advice="Truth for public good and opinions expressed in good faith regarding public servants or conduct are statutory exceptions.",
    ),
    # Criminal Procedure: BNSS 2023 vs CrPC
    StatuteProvision(
        statute="Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        section="Section 173",
        title="Information in Cognizable Cases (Zero FIR & e-FIR)",
        description="Registration of FIR irrespective of territorial jurisdiction, with transfer to competent police station within 3 days.",
        historical_reference="Formerly Section 154 of CrPC, now with statutory recognition of Zero FIR",
        key_principles=[
            "Zero FIR can be filed at ANY police station in India",
            "Mandatory electronic or physical registration of cognizable complaints",
            "Free copy of FIR must be given to complainant immediately",
        ],
        citizen_advice="No police officer can refuse to register an FIR on grounds of territorial jurisdiction. Insist on a Zero FIR.",
    ),
    StatuteProvision(
        statute="Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        section="Section 35",
        title="Arrest Rights and Designated Police Officer",
        description="Designation of a police officer in every district to maintain information about arrested persons.",
        historical_reference="Expands Section 41B & 41D of CrPC",
        key_principles=[
            "Right to inform a relative or friend immediately upon arrest",
            "Right to meet an advocate of choice during interrogation",
            "Display of arrested persons at district police control rooms",
        ],
        citizen_advice="If arrested or detained, demand immediate notification to family and access to a legal counsel or legal aid advocate.",
    ),
    # Consumer Protection Act, 2019
    StatuteProvision(
        statute="Consumer Protection Act, 2019",
        section="Section 2(46)",
        title="Unfair Contract Terms",
        description="Contracts between a consumer and manufacturer/service provider that cause significant change in consumer rights.",
        historical_reference="Enacted in 2019, replacing 1986 Act",
        key_principles=[
            "Requiring excessive security deposits for performance",
            "Imposing disproportionate penalty on consumer for breach compared to seller",
            "Refusing to accept early repayment of debts",
            "Entitling unilateral termination without reasonable cause",
            "Permitting unilateral variation of contract without consent",
        ],
        citizen_advice="Clauses like 'no refund under any condition' or 18% late fees on consumers when the company delays without penalty are illegal and voidable.",
    ),
    StatuteProvision(
        statute="Consumer Protection Act, 2019",
        section="Section 34 & 35",
        title="Jurisdiction and Filing of Consumer Complaints (e-Daakhil)",
        description="Filing consumer complaints where the consumer resides or works, physically or via the e-Daakhil portal.",
        historical_reference="Replaced strict seller-location jurisdiction of 1986 Act",
        key_principles=[
            "District Commission jurisdiction up to INR 50 Lakhs",
            "Consumer can file where they currently reside (no need to travel to seller's city)",
            "Online complaint submission via e-Daakhil (edaakhil.nic.in)",
            "Limitation period of 2 years from date on which cause of action arose",
        ],
        citizen_advice="You can file a formal consumer grievance online without hiring an expensive lawyer via edaakhil.nic.in.",
    ),
    # Tenancy & Rental Laws: Model Tenancy Act & State Rent Laws
    StatuteProvision(
        statute="Model Tenancy Act (Principles applicable in Delhi, UP, Karnataka, etc.)",
        section="Section 11 & Section 13",
        title="Security Deposit Cap & Entry Restrictions",
        description="Caps residential security deposit to maximum 2 months' rent and restricts landlord entry without prior notice.",
        historical_reference="Standardized national model framework for rental housing",
        key_principles=[
            "Residential security deposit capped at maximum 2 months of rent",
            "Refund of security deposit within specified timeline after vacant possession",
            "Mandatory 24 hours prior written notice before landlord entry for inspection",
            "Inspection strictly during daylight hours (7:00 AM to 8:00 PM)",
            "Prohibition of cutting off essential services (water, electricity) by landlord",
        ],
        citizen_advice="Landlords cannot demand 6 to 10 months security deposit or barge into your rental home without 24 hours notice.",
    ),
    # Employment & Contract Law
    StatuteProvision(
        statute="Indian Contract Act, 1872",
        section="Section 27",
        title="Agreement in Restraint of Trade Void",
        description="Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.",
        historical_reference="Percept D'Mark v. Zaheer Khan (Supreme Court of India, 2006)",
        key_principles=[
            "Post-employment non-compete clauses are completely void under Indian law",
            "Employers cannot stop an employee from joining a competitor after resignation",
            "Only reasonable non-compete covenants DURING active employment or sale of goodwill are enforceable",
        ],
        citizen_advice="If an IT or corporate company threatens you with a '1-year post-exit non-compete', remember Indian courts consistently hold this void under Section 27.",
    ),
    # Data Protection: DPDP Act 2023
    StatuteProvision(
        statute="Digital Personal Data Protection Act, 2023 (DPDP Act)",
        section="Section 6 & Section 12",
        title="Consent Notice and Right to Grievance Redressal",
        description="Notice requirements before processing personal data and user right to readily available grievance redressal.",
        historical_reference="Act No. 22 of 2023",
        key_principles=[
            "Data Fiduciaries must give clear notice in plain language",
            "Consent must be free, specific, informed, unconditional and unambiguous",
            "Users have right to access, correct, erase their data and nominate a representative",
        ],
        citizen_advice="Entities cannot withhold essential services for refusing non-essential data permissions.",
    ),
    # Legal Services Authorities Act, 1987 (Free Legal Aid)
    StatuteProvision(
        statute="Legal Services Authorities Act, 1987",
        section="Section 12",
        title="Criteria for Giving Legal Services (Free Legal Aid)",
        description="Statutory entitlement to free legal representation, court fees exemption, and advocates paid by the State.",
        historical_reference="Constitutional mandate under Article 39A of Constitution of India",
        key_principles=[
            "Women and children are entitled to free legal aid irrespective of income",
            "Members of Scheduled Castes (SC) or Scheduled Tribes (ST)",
            "Persons with disability under Rights of Persons with Disabilities Act",
            "Victims of human trafficking, beggar, or disaster/communal violence",
            "Industrial workmen",
            "Persons in custody or protective homes",
            "General citizens whose annual income does not exceed the state threshold (typically INR 3,00,000 in Delhi/Karnataka/Maharashtra)",
        ],
        citizen_advice="If you qualify under Section 12, you are legally entitled to a free government advocate through DLSA/SLSA. Call national helpline 15100.",
    ),
]


def search_statutory_kb(query: str) -> List[StatuteProvision]:
    """Search statutory knowledge base for matching provisions."""
    query_lower = query.lower()
    matches = []
    for item in INDIAN_STATUTORY_REGISTRY:
        section_lower = item.section.lower()
        title_lower = item.title.lower()
        statute_short = (
            "bns"
            if "bharatiya nyaya" in item.statute.lower()
            else ("bnss" if "nagarik" in item.statute.lower() else "")
        )

        if (
            section_lower in query_lower
            or title_lower in query_lower
            or (statute_short and statute_short in query_lower)
            or (
                item.historical_reference
                and any(term in query_lower for term in ["ipc", "crpc", "420", "302", "section 27"])
            )
        ):
            matches.append(item)
    return matches

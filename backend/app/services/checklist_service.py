from typing import Dict

LEGAL_ACTION_CHECKLISTS: Dict[str, Dict] = {
    "lease": {
        "title": "Tenant Pre-Signing & Move-In Checklist",
        "jurisdiction": "India (Model Tenancy Act & State Rent Laws)",
        "items": [
            {
                "id": "chk-l1",
                "title": "Landlord Ownership Verification",
                "description": "Request a copy of the electricity bill, property tax receipt, or sale deed to verify the lessor actually owns or has authority to let the property.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-l2",
                "title": "Security Deposit Cap Check",
                "description": "Ensure the security deposit does not exceed 2 months' rent for residential premises under Model Tenancy Act principles.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-l3",
                "title": "Mutual 30-Day Termination Notice",
                "description": "Verify both tenant and landlord have identical notice periods (typically 30 days) and neither party has unilateral 7-day termination power.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-l4",
                "title": "Initial Inventory & Condition Report",
                "description": "Take photographic and video evidence of all walls, electrical fittings, plumbing, and fixtures on move-in day to prevent unwarranted deposit deductions.",
                "importance": "RECOMMENDED",
            },
            {
                "id": "chk-l5",
                "title": "Electricity & Water Meter Initial Readings",
                "description": "Record the exact meter readings on handover day with landlord acknowledgment to avoid paying previous occupants' dues.",
                "importance": "RECOMMENDED",
            },
            {
                "id": "chk-l6",
                "title": "Tenant Police Verification",
                "description": "Submit the standard tenant verification form at the local police station as legally mandated in major Indian metros.",
                "importance": "MANDATORY",
            },
        ],
    },
    "employment": {
        "title": "Employment Offer & Exit Checklist",
        "jurisdiction": "India (Indian Contract Act 1872 & Labor Laws)",
        "items": [
            {
                "id": "chk-e1",
                "title": "Notice Period Parity & Buyout Option",
                "description": "Confirm notice period is reciprocal and allows notice pay buyout if you receive an urgent joining requirement elsewhere.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-e2",
                "title": "Post-Employment Non-Compete Review",
                "description": "Note that non-compete clauses restricting your right to join a competitor after leaving are void under Section 27 of the Indian Contract Act.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-e3",
                "title": "Intellectual Property Ownership Scope",
                "description": "Ensure IP assignment applies strictly to work created during official duties and does not claim ownership over personal projects built on personal time.",
                "importance": "RECOMMENDED",
            },
            {
                "id": "chk-e4",
                "title": "Statutory EPF & Gratuity Allocation",
                "description": "Verify your CTC breakdown clearly specifies Employee Provident Fund (12% + 12%) and Gratuity eligibility after 5 years continuous service.",
                "importance": "MANDATORY",
            },
        ],
    },
    "consumer": {
        "title": "Consumer Grievance & Redressal Checklist",
        "jurisdiction": "India (Consumer Protection Act, 2019)",
        "items": [
            {
                "id": "chk-c1",
                "title": "Gather Proof of Transaction",
                "description": "Collect GST tax invoice, payment gateway receipt/UTR, warranty card, and product serial number.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-c2",
                "title": "Formal Written Notice to Company",
                "description": "Send a formal email giving 15 days notice to rectify the deficiency in service or refund the amount.",
                "importance": "CRITICAL",
            },
            {
                "id": "chk-c3",
                "title": "National Consumer Helpline (NCH - 1915) Complaint",
                "description": "Register a complaint online at consumerhelpline.gov.in or call 1915 to attempt pre-litigation resolution.",
                "importance": "RECOMMENDED",
            },
            {
                "id": "chk-c4",
                "title": "File Formal Petition on e-Daakhil",
                "description": "If unresolved after 15 days, file a formal complaint before the District Consumer Commission via edaakhil.nic.in without paying hefty court fees.",
                "importance": "MANDATORY_IF_UNRESOLVED",
            },
        ],
    },
}


def get_action_checklist(category: str) -> Dict:
    cat_clean = category.strip().lower()
    if "lease" in cat_clean or "rent" in cat_clean or "tenant" in cat_clean:
        return LEGAL_ACTION_CHECKLISTS["lease"]
    elif "employ" in cat_clean or "job" in cat_clean or "hr" in cat_clean:
        return LEGAL_ACTION_CHECKLISTS["employment"]
    return LEGAL_ACTION_CHECKLISTS["consumer"]

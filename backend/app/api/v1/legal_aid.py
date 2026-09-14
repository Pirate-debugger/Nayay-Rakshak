from typing import List, Optional

from fastapi import APIRouter, Query

from app.schemas.legal_aid import (
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    LegalAidResource,
)
from app.services.legal_aid_service import LEGAL_AID_RESOURCES, evaluate_free_legal_aid_eligibility

router = APIRouter(prefix="/legal-aid", tags=["Legal Aid & Resources"])


@router.get("/resources", response_model=List[LegalAidResource])
async def list_legal_aid_resources(
    query: Optional[str] = Query(None, description="Search query for name, state, or service"),
    organization_type: Optional[str] = Query(
        None, description="Filter by NALSA, SLSA, TELE_LAW, CONSUMER_FORUM, CYBER_HELPLINE"
    ),
):
    """
    Search directory of authoritative Indian legal aid institutions and helplines.
    """
    results = LEGAL_AID_RESOURCES
    if organization_type:
        results = [r for r in results if r.organization_type.upper() == organization_type.upper()]
    if query:
        q = query.lower()
        results = [
            r
            for r in results
            if q in r.name.lower()
            or q in r.jurisdiction.lower()
            or q in r.description.lower()
            or any(q in s.lower() for s in r.services_offered)
        ]
    return results


@router.post("/check-eligibility", response_model=EligibilityCheckResponse)
async def check_eligibility_endpoint(req: EligibilityCheckRequest):
    """
    Evaluate eligibility for free legal aid under Section 12 of the Legal Services Authorities Act, 1987.
    """
    return evaluate_free_legal_aid_eligibility(req)

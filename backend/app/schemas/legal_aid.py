from typing import List, Optional

from pydantic import BaseModel


class LegalAidResource(BaseModel):
    id: str
    name: str
    organization_type: (
        str  # NALSA, SLSA, DLSA, LOK_ADALAT, TELE_LAW, CONSUMER_FORUM, CYBER_HELPLINE
    )
    jurisdiction: str
    phone_or_helpline: str
    portal_url: str
    description: str
    services_offered: List[str]
    physical_address: Optional[str] = None


class EligibilityCheckRequest(BaseModel):
    annual_income: float
    state: str
    is_woman_or_child: bool = False
    is_sc_or_st: bool = False
    is_in_custody: bool = False
    is_disabled: bool = False
    is_trafficking_victim: bool = False
    is_industrial_workman: bool = False


class EligibilityCheckResponse(BaseModel):
    is_eligible_for_free_legal_aid: bool
    governing_statute: str
    statutory_clause: str
    eligibility_reasons: List[str]
    annual_income_limit_for_state: float
    recommended_authorities: List[LegalAidResource]
    action_checklist: List[str]

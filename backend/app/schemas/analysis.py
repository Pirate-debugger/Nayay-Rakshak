from typing import List, Optional

from pydantic import BaseModel


class ClauseItem(BaseModel):
    clause_id: str
    category: str  # e.g., "Termination", "Indemnity", "Rent Escalation", "Dispute Resolution", "Non-Compete", etc.
    title: str
    original_text: str
    plain_english: str
    plain_hindi: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "SEVERE"
    page_number: int
    recommendations: Optional[str] = None

class RiskItem(BaseModel):
    risk_id: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "SEVERE"
    category: str
    title: str
    description: str
    clause_reference: str
    countermeasure: str

class ObligationItem(BaseModel):
    obligation_id: str
    responsible_party: str
    action: str
    deadline_or_frequency: str
    penalty_for_breach: str

class MissingClauseItem(BaseModel):
    clause_name: str
    importance: str  # "CRITICAL", "RECOMMENDED", "STANDARD"
    why_needed: str
    suggested_language: str
    risk_if_missing: str

class AnalysisResponse(BaseModel):
    document_id: int
    summary_citizen: str
    summary_legal: str
    summary_hindi: str
    flesch_kincaid_score: float
    reading_level: str
    clauses: List[ClauseItem]
    risks: List[RiskItem]
    obligations: List[ObligationItem]
    missing_clauses: List[MissingClauseItem]

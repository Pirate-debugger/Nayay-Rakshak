"""
NYAYA RAKSHAK - Query Intent Classifier & Jurisdiction/Temporal Guard
Classifies incoming legal queries to optimize routing between User Documents,
Statutory Authorities, and Secondary Information.
"""

from datetime import datetime, timezone
import re
from typing import Optional, Tuple

from app.schemas.retrieval import QueryIntent, RetrievalFilter


class QueryClassifier:
    """Classifies user queries into retrieval intents and extracts temporal/jurisdiction filters."""

    def classify(self, query: str, has_user_document: bool = False) -> Tuple[QueryIntent, RetrievalFilter]:
        q_lower = query.lower()

        # 1. Temporal Detection
        as_of_date: Optional[datetime] = None
        if any(k in q_lower for k in ["ipc", "indian penal code", "crpc", "prior to 2024", "before july 2024", "old criminal law"]):
            as_of_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        elif any(k in q_lower for k in ["bns", "bnss", "bsa", "new law", "current law", "2024", "2025", "2026"]):
            as_of_date = datetime(2024, 7, 2, tzinfo=timezone.utc)

        # 2. Jurisdiction Detection
        jurisdiction = "Union of India"  # default federal
        if "delhi" in q_lower:
            jurisdiction = "NCT of Delhi"
        elif "maharashtra" in q_lower or "mumbai" in q_lower:
            jurisdiction = "Maharashtra"
        elif "karnataka" in q_lower or "bengaluru" in q_lower or "bangalore" in q_lower:
            jurisdiction = "Karnataka"

        # 3. Domain Detection
        legal_domain = None
        if any(k in q_lower for k in ["rent", "lease", "tenant", "landlord", "eviction", "security deposit"]):
            legal_domain = "tenancy"
        elif any(k in q_lower for k in ["cheating", "theft", "crime", "fir", "police", "bns", "ipc", "fraud"]):
            legal_domain = "criminal"
        elif any(k in q_lower for k in ["non-compete", "salary", "employment", "employee", "notice period"]):
            legal_domain = "employment"
        elif any(k in q_lower for k in ["consumer", "defective", "unfair contract", "product liability"]):
            legal_domain = "consumer"
        elif any(k in q_lower for k in ["privacy", "data", "dpdp", "personal data", "tracking"]):
            legal_domain = "privacy"

        # 4. Intent Classification
        is_document_ref = any(k in q_lower for k in [
            "my agreement", "my contract", "my lease", "this clause", "clause", "section in my",
            "page", "my rent", "my deposit", "the document", "in this document"
        ])
        is_statute_ref = any(k in q_lower for k in [
            "bns", "ipc", "crpc", "contract act", "section 27", "section 318", "section 420",
            "statute", "supreme court", "high court", "law in india", "act 20", "dpdp", "under indian law"
        ])

        if has_user_document and is_document_ref and is_statute_ref:
            intent = QueryIntent.HYBRID
        elif has_user_document and is_document_ref:
            intent = QueryIntent.DOCUMENT_ONLY
        elif is_statute_ref:
            intent = QueryIntent.LEGAL_SOURCE
        elif has_user_document:
            intent = QueryIntent.DOCUMENT_ONLY
        else:
            intent = QueryIntent.GENERAL_INFORMATION

        filters = RetrievalFilter(
            jurisdiction=jurisdiction,
            allow_cross_jurisdiction=False,
            legal_domain=legal_domain,
            as_of_date=as_of_date
        )

        return intent, filters


query_classifier = QueryClassifier()

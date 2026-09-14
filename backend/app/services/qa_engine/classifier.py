"""
NYAYA RAKSHAK - Q&A Context & Requirement Classifier
Identifies:
1. Question requirement type: DOCUMENT_EVIDENCE, LEGAL_AUTHORITY, BOTH, GENERAL_INFORMATION
2. 5-Factor Context:
   - Jurisdiction (State vs Federal)
   - Document context (Agreement type, parties, domain)
   - Relevant dates and notice timelines
   - Legal domain
   - Missing critical facts
RULE: When critical information is missing, state the limitation rather than inventing it.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.qa import QAContextMetadata, QuestionRequirementType


class QAClassifier:
    """Classifies user inquiries and extracts jurisdiction, temporal bounds, domain, and missing facts."""

    def classify_and_extract_context(
        self,
        question: str,
        document_chunks: Optional[List[Dict[str, Any]]] = None,
        explicit_jurisdiction: Optional[str] = None,
    ) -> Tuple[QuestionRequirementType, QAContextMetadata]:
        q_lower = question.lower()
        has_doc = bool(document_chunks and len(document_chunks) > 0)

        # 1. Detect Jurisdiction
        jurisdiction = explicit_jurisdiction or "Union of India"
        if not explicit_jurisdiction:
            if "delhi" in q_lower:
                jurisdiction = "NCT of Delhi"
            elif "maharashtra" in q_lower or "mumbai" in q_lower or "pune" in q_lower:
                jurisdiction = "Maharashtra"
            elif "karnataka" in q_lower or "bengaluru" in q_lower or "bangalore" in q_lower:
                jurisdiction = "Karnataka"
            elif "tamil nadu" in q_lower or "chennai" in q_lower:
                jurisdiction = "Tamil Nadu"

        # 2. Detect Legal Domain
        domain = "general"
        if any(
            k in q_lower
            for k in [
                "rent",
                "lease",
                "tenant",
                "landlord",
                "eviction",
                "security deposit",
                "premises",
            ]
        ):
            domain = "tenancy"
        elif any(
            k in q_lower
            for k in [
                "employee",
                "employer",
                "salary",
                "resignation",
                "non-compete",
                "notice period",
                "probation",
            ]
        ):
            domain = "employment"
        elif any(
            k in q_lower
            for k in [
                "cheating",
                "theft",
                "fir",
                "police",
                "crime",
                "bns",
                "ipc",
                "criminal",
                "bail",
            ]
        ):
            domain = "criminal"
        elif any(
            k in q_lower for k in ["consumer", "defective", "refund", "unfair trade", "e-daakhil"]
        ):
            domain = "consumer"
        elif any(k in q_lower for k in ["data", "privacy", "dpdp", "personal data", "tracking"]):
            domain = "privacy"
        elif any(k in q_lower for k in ["arbitration", "arbitrator", "dispute", "award"]):
            domain = "arbitration"

        # 3. Detect Relevant Dates & Timelines
        dates_found = []
        date_patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b",
            r"\b\d{1,2}\s+(?:months?|days?|years?)\b",
            r"\b(?:2024|2025|2026)\b",
        ]
        for dp in date_patterns:
            for m in re.finditer(dp, question, flags=re.IGNORECASE):
                dates_found.append(m.group(0).strip())

        # 4. Detect Document Context
        doc_context = None
        if has_doc:
            doc_text = " ".join([c.get("content", "")[:200] for c in document_chunks[:3]]).lower()
            if any(k in doc_text for k in ["lease", "rent", "lessor", "tenant"]):
                doc_context = "Residential / Commercial Tenancy Lease"
            elif any(k in doc_text for k in ["employment", "employee", "salary", "covenant"]):
                doc_context = "Employment Service Agreement"
            elif any(k in doc_text for k in ["terms of service", "privacy policy", "consumer"]):
                doc_context = "Consumer Terms of Service"
            else:
                doc_context = "Uploaded Legal Document"

        # 5. Determine Question Requirement Type
        is_doc_focused = any(
            k in q_lower
            for k in [
                "my agreement",
                "my contract",
                "my lease",
                "this clause",
                "clause",
                "page",
                "what does the document say",
                "in my agreement",
                "my notice period",
                "my deposit",
            ]
        )
        is_statute_focused = any(
            k in q_lower
            for k in [
                "indian law",
                "law in india",
                "under law",
                "statute",
                "section",
                "act",
                "bns",
                "ipc",
                "contract act",
                "supreme court",
                "high court",
                "legal right",
                "legal",
                "valid",
                "enforceable",
                "legally valid",
                "penalty",
                "punishment",
                "allowed under law",
                "court",
            ]
        )

        if has_doc and is_doc_focused and is_statute_focused:
            req_type = QuestionRequirementType.BOTH
        elif has_doc and is_doc_focused:
            req_type = QuestionRequirementType.DOCUMENT_EVIDENCE
        elif is_statute_focused:
            req_type = QuestionRequirementType.LEGAL_AUTHORITY
        elif has_doc:
            # If a document is loaded and user asks a contextual question, treat as BOTH or DOCUMENT
            req_type = (
                QuestionRequirementType.BOTH
                if any(k in q_lower for k in ["valid", "allowed", "legal", "can they"])
                else QuestionRequirementType.DOCUMENT_EVIDENCE
            )
        else:
            req_type = QuestionRequirementType.GENERAL_INFORMATION

        # 6. Identify Missing Critical Facts (Mandate: state limitations rather than inventing)
        missing_facts = self._identify_missing_facts(domain, q_lower, has_doc, jurisdiction)

        context_meta = QAContextMetadata(
            jurisdiction=jurisdiction,
            document_context=doc_context,
            relevant_dates=list(dict.fromkeys(dates_found)),
            legal_domain=domain,
            missing_facts=missing_facts,
        )

        return req_type, context_meta

    def _identify_missing_facts(
        self, domain: str, q_lower: str, has_doc: bool, jurisdiction: str
    ) -> List[str]:
        """Identifies essential factual gaps that prevent categorical legal answers."""
        missing = []

        if domain == "tenancy":
            if not any(
                k in q_lower
                for k in ["delhi", "mumbai", "maharashtra", "bangalore", "karnataka", "chennai"]
            ):
                missing.append(
                    "Specific state or union territory where the rented property is physically situated (state rent control acts differ significantly)."
                )
            if not any(k in q_lower for k in ["written", "verbal", "registered"]):
                missing.append(
                    "Whether the tenancy agreement is officially registered or an unregistered/verbal understanding."
                )
            if "deposit" in q_lower and not any(
                k in q_lower for k in ["month", "amount", "₹", "rs"]
            ):
                missing.append("The exact quantum of security deposit and monthly rent amount.")

        elif domain == "employment":
            if "notice" in q_lower and not any(
                k in q_lower for k in ["probation", "confirmed", "permanent"]
            ):
                missing.append(
                    "Whether the employee is currently in their probation period or has been confirmed as permanent staff."
                )
            if "non-compete" in q_lower and not any(
                k in q_lower for k in ["during", "after", "post"]
            ):
                missing.append(
                    "Whether the non-compete restriction applies during active employment or post-cessation (post-service covenants face strict unenforceability under Section 27)."
                )

        elif domain == "criminal":
            if not any(k in q_lower for k in ["before", "after", "2024", "2023", "bns", "ipc"]):
                missing.append(
                    "The exact date when the alleged offence occurred (determines whether legacy IPC 1860 or Bharatiya Nyaya Sanhita 2023 applies)."
                )
            if not any(k in q_lower for k in ["fir", "complaint", "police"]):
                missing.append(
                    "Whether an FIR, e-FIR, or formal police complaint has already been registered."
                )

        elif domain == "consumer":
            if not any(k in q_lower for k in ["notice", "written", "complaint"]):
                missing.append(
                    "Whether a formal written legal notice has been served upon the trader/service provider giving reasonable cure time."
                )

        if not has_doc and any(
            k in q_lower for k in ["my clause", "my contract", "valid", "can my landlord"]
        ):
            missing.append(
                "The exact signed text of the agreement is not available; analysis is based solely on general legal principles."
            )

        return missing


qa_classifier = QAClassifier()

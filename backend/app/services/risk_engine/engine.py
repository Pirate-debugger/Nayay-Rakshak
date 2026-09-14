"""
NYAYA RAKSHAK - Hybrid Deterministic + AI-Assisted Risk Engine
Coordinates rule-based detection for objective conditions with AI semantic pattern detection.
Rule: DO NOT let the LLM alone determine risk. Every risk must have verifiable textual evidence.
Mandatory Language Hedging: Use 'Potential concern', 'Worth reviewing', 'Appears broader than...'
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional

from app.schemas.clause_intelligence import StructuredClauseRecord
from app.schemas.risk import (
    EvidenceLocation,
    FindingType,
    RiskCategory,
    RiskEngineResult,
    RiskRecord,
    RiskSeverity,
    RiskSummary,
)
from app.services.clause_intelligence import (
    analyze_clause_structured_async,
    extract_deterministic_facts,
    segment_clauses_from_text,
)
from app.services.risk_engine.rules import (
    RULESET_VERSION,
    risk_rule_registry,
)

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Hybrid Legal Risk Analysis Engine.
    Combines:
    1. Versioned Deterministic Rules (objective numerical, temporal, statutory bounds)
    2. Cross-Clause Conflict Detector (contradictory covenants across sections)
    3. AI-Assisted Semantic Pattern Detector (with strict verbatim evidence verification)
    4. Missing Protection Heuristics
    """

    def __init__(self, registry=None):
        self.registry = registry or risk_rule_registry
        self.engine_version = "2024.1.0"
        self.ruleset_version = self.registry.version

    async def analyze_document_risks(
        self,
        document_text: str,
        document_id: Optional[int] = None,
        document_title: Optional[str] = None,
        ai_provider=None,
        structured_clauses: Optional[List[StructuredClauseRecord]] = None
    ) -> RiskEngineResult:
        """
        Execute comprehensive hybrid risk analysis on a document.
        """
        all_risks: List[RiskRecord] = []
        missing_protections: List[RiskRecord] = []
        audit_trail: List[Dict[str, Any]] = []

        # 1. Segment clauses if not already supplied
        if structured_clauses:
            clauses = structured_clauses
        else:
            raw_clauses = segment_clauses_from_text(document_text)
            clauses = []
            for i, rc in enumerate(raw_clauses):
                cid = f"C-{i+1:02d}"
                c_record = await analyze_clause_structured_async(
                    clause_id=cid,
                    raw_text=rc["text"],
                    page_number=rc.get("page", 1),
                    section_name=rc.get("section_heading", "General Covenants"),
                    char_offset=rc.get("start_char", 0)
                )
                clauses.append(c_record)

        # 2. DETERMINISTIC PHASE: Run versioned rules on each clause
        for clause in clauses:
            facts = clause.deterministic_facts.model_dump()
            is_camouflaged = self._is_clause_camouflaged(clause)

            for rule in self.registry.list_rules():
                res = rule.evaluate(
                    text=clause.original_text,
                    deterministic_facts=facts,
                    doc_context={"clause_id": clause.clause_id, "category": clause.category},
                    page_number=clause.page,
                    section_heading=clause.section
                )
                if res:
                    res.is_camouflaged = is_camouflaged
                    all_risks.append(res)
                    audit_trail.append({
                        "rule_id": rule.rule_id,
                        "rule_version": rule.version,
                        "clause_id": clause.clause_id,
                        "status": "TRIGGERED",
                        "severity": res.severity.value,
                        "category": res.category.value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    audit_trail.append({
                        "rule_id": rule.rule_id,
                        "rule_version": rule.version,
                        "clause_id": clause.clause_id,
                        "status": "EVALUATED_NO_TRIGGER",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

        # 3. DOCUMENT-LEVEL RULES (e.g. Missing dispute resolution, Force Majeure, etc.)
        doc_facts = extract_deterministic_facts(document_text)
        for rule in self.registry.list_rules():
            doc_res = rule.evaluate(
                text=document_text,
                deterministic_facts=doc_facts,
                doc_context={"is_whole_document": True},
                page_number=1,
                section_heading="Entire Document"
            )
            if doc_res:
                if doc_res.category == RiskCategory.MISSING_PROTECTION:
                    missing_protections.append(doc_res)
                else:
                    all_risks.append(doc_res)
                audit_trail.append({
                    "rule_id": rule.rule_id,
                    "rule_version": rule.version,
                    "scope": "DOCUMENT_LEVEL",
                    "status": "TRIGGERED",
                    "severity": doc_res.severity.value,
                    "category": doc_res.category.value,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        # 4. CROSS-CLAUSE CONFLICT DETECTION
        conflict_risks = self._detect_conflicting_clauses(clauses)
        all_risks.extend(conflict_risks)
        for cr in conflict_risks:
            audit_trail.append({
                "rule_id": cr.rule_id or "RULE-AMB-001",
                "rule_version": cr.rule_version or self.ruleset_version,
                "scope": "CROSS_CLAUSE",
                "status": "TRIGGERED",
                "severity": cr.severity.value,
                "category": cr.category.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # 5. AI-ASSISTED SEMANTIC PATTERN PHASE (Evidence-Grounded with strict rejection of ungrounded risks)
        if ai_provider:
            try:
                ai_risks = await self._evaluate_ai_patterns_with_evidence(
                    ai_provider=ai_provider,
                    document_text=document_text,
                    clauses=clauses,
                    audit_trail=audit_trail
                )
                # Deduplicate against deterministic risks (deterministic takes priority)
                for air in ai_risks:
                    if not any(r.category == air.category and r.title == air.title for r in all_risks):
                        all_risks.append(air)
            except Exception as e:
                logger.warning(f"AI semantic risk evaluation skipped: {e}")

        # 6. Deduplicate risks by category, rule_id, and evidence quote
        unique_risks = self._deduplicate_risks(all_risks)

        # 7. Compute Summary
        summary = self._compute_summary(unique_risks)

        return RiskEngineResult(
            document_id=document_id,
            engine_version=self.engine_version,
            ruleset_version=self.ruleset_version,
            summary=summary,
            risks=unique_risks,
            missing_protections=missing_protections,
            audit_trail=audit_trail
        )

    def _is_clause_camouflaged(self, clause: StructuredClauseRecord) -> bool:
        """
        Detects if high-risk covenants are buried under deceptive headings
        such as 'Miscellaneous', 'General', 'Boilerplate', or 'Other'.
        """
        deceptive_headings = ["miscellaneous", "general", "other", "standard terms", "boilerplate"]
        sec = (clause.section or "").lower()
        if any(dh in sec for dh in deceptive_headings):
            t_lower = clause.original_text.lower()
            if any(k in t_lower for k in ["indemn", "non-compete", "penalty", "waive", "liquidated damages"]):
                return True
        return False

    def _detect_conflicting_clauses(self, clauses: List[StructuredClauseRecord]) -> List[RiskRecord]:
        """
        Detects internal contractual contradictions (e.g. 30-day notice vs immediate lock-in).
        """
        conflicts = []
        notice_clauses = []
        lock_in_clauses = []

        for c in clauses:
            t = c.original_text.lower()
            if "notice" in t and any(k in t for k in ["30 days", "month", "terminate"]):
                notice_clauses.append(c)
            if any(k in t for k in ["lock-in", "no right to terminate", "cannot vacate prior", "liable for rent for the entire unexpired term"]):
                lock_in_clauses.append(c)

        if notice_clauses and lock_in_clauses:
            n_clause = notice_clauses[0]
            l_clause = lock_in_clauses[0]
            conflicts.append(RiskRecord(
                risk_id="RISK-RULE-AMB-001",
                category=RiskCategory.AMBIGUITY,
                severity=RiskSeverity.HIGH,
                title="Potential Concern: Conflicting Clause Terms (Notice vs Lock-In)",
                finding=(
                    f"Contradiction detected between {n_clause.clause_id} ('{n_clause.title}') "
                    f"and {l_clause.clause_id} ('{l_clause.title}')."
                ),
                plain_language_explanation=(
                    "Potential concern: One clause states you can terminate by giving notice, while another clause states "
                    "you are bound to an unexpired lock-in period. Definitive legal validity cannot be established without judicial determination."
                ),
                why_it_matters="Conflicting terms create legal ambiguity, allowing the stronger party to enforce whichever clause is more advantageous to them.",
                evidence=EvidenceLocation(
                    page_number=n_clause.page,
                    section_heading=f"{n_clause.section} vs {l_clause.section}",
                    verbatim_quote=f"{n_clause.original_text[:90]}... CONFLICTS WITH: {l_clause.original_text[:90]}...",
                    char_start=0,
                    char_end=180
                ),
                affected_party="Signatory / Citizen",
                confidence=0.95,
                recommended_question="Which clause supersedes the other: the notice provision or the absolute lock-in prohibition?",
                professional_review_recommended=True,
                rule_id="RULE-AMB-001",
                rule_version=self.ruleset_version,
                finding_type=FindingType.CROSS_CLAUSE_CONFLICT,
                statutory_cross_reference="Indian Contract Act, 1872 § 29 (Agreements Void for Uncertainty)"
            ))

        return conflicts

    async def _evaluate_ai_patterns_with_evidence(
        self,
        ai_provider,
        document_text: str,
        clauses: List[StructuredClauseRecord],
        audit_trail: List[Dict[str, Any]]
    ) -> List[RiskRecord]:
        """
        Evaluates semantic patterns with AI.
        RULE: AI MAY NOT invent risks without exact verbatim evidence in document text.
        Ungrounded AI findings are strictly rejected.
        """
        ai_findings = await ai_provider.interpret_clause(document_text[:3000], {})
        ai_risks = []
        raw_risks = ai_findings.get("risks", [])

        for idx, r in enumerate(raw_risks):
            quote = r.get("evidence_quote") or r.get("verbatim_quote") or ""
            quote_clean = quote.strip()

            # GROUNDING CHECK: Verbatim quote must exist in document text
            if quote_clean and quote_clean in document_text:
                cat_str = r.get("category", "AMBIGUITY").upper()
                sev_str = r.get("severity", "MEDIUM").upper()
                try:
                    cat = RiskCategory(cat_str)
                except ValueError:
                    cat = RiskCategory.AMBIGUITY

                try:
                    sev = RiskSeverity(sev_str)
                except ValueError:
                    sev = RiskSeverity.MEDIUM

                # Enforce Language Hedging on Title
                raw_title = r.get("title", "Unusual Contractual Covenant")
                hedged_title = self._apply_language_hedging(raw_title)

                char_start = document_text.find(quote_clean)
                char_end = char_start + len(quote_clean)

                ai_risks.append(RiskRecord(
                    risk_id=f"RISK-AI-{idx+1:02d}",
                    category=cat,
                    severity=sev,
                    title=hedged_title,
                    finding=f"Potential concern: {r.get('finding', 'Semantic pattern of potential concern identified in clause language.')}",
                    plain_language_explanation=r.get("plain_language_explanation", "This clause contains language worth clarifying before signing. Note: Legal validity cannot be established without judicial review."),
                    why_it_matters=r.get("why_it_matters", "May create operational friction or unexpected liability exposure."),
                    evidence=EvidenceLocation(
                        page_number=1,
                        section_heading=r.get("section", "Clause Pattern"),
                        verbatim_quote=quote_clean,
                        char_start=char_start,
                        char_end=char_end
                    ),
                    affected_party=r.get("affected_party", "Signatory"),
                    confidence=0.88,
                    recommended_question=r.get("recommended_question", "Can this clause be clarified with specific reciprocal definitions?"),
                    professional_review_recommended=sev in [RiskSeverity.HIGH, RiskSeverity.CRITICAL],
                    rule_id=None,
                    rule_version=self.ruleset_version,
                    finding_type=FindingType.AI_ASSISTED_PATTERN,
                    statutory_cross_reference=None
                ))
                audit_trail.append({
                    "source": "AI_ASSISTED_PATTERN",
                    "status": "ACCEPTED_GROUNDED",
                    "quote_length": len(quote_clean),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                # Reject ungrounded AI risk
                audit_trail.append({
                    "source": "AI_ASSISTED_PATTERN",
                    "status": "REJECTED_UNGROUNDED_AI_FINDING",
                    "reason": "Verbatim quote not found in source text",
                    "rejected_quote": quote_clean[:80] if quote_clean else "EMPTY",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        return ai_risks

    def _apply_language_hedging(self, title: str) -> str:
        """Ensures titles adhere to mandatory hedging guidelines."""
        hedging_prefixes = ["Potential concern", "Worth reviewing", "Appears broader than"]
        if any(title.lower().startswith(p.lower()) for p in hedging_prefixes):
            return title
        # Replace definitive words
        clean_title = re.sub(r"(?i)\b(illegal|void|unlawful|prohibited)\b", "unusual", title)
        return f"Potential Concern: {clean_title}"

    def _deduplicate_risks(self, risks: List[RiskRecord]) -> List[RiskRecord]:
        """Deduplicates risks by category and verbatim quote or rule_id."""
        seen = set()
        unique = []
        for r in risks:
            key = (r.category, r.rule_id, r.evidence.verbatim_quote[:50])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique

    def _compute_summary(self, risks: List[RiskRecord]) -> RiskSummary:
        crit = sum(1 for r in risks if r.severity == RiskSeverity.CRITICAL)
        high = sum(1 for r in risks if r.severity == RiskSeverity.HIGH)
        med = sum(1 for r in risks if r.severity == RiskSeverity.MEDIUM)
        low = sum(1 for r in risks if r.severity == RiskSeverity.LOW)

        if crit > 0:
            verdict = "CRITICAL_ATTENTION_REQUIRED"
        elif high > 0:
            verdict = "HIGH_RISK_TERMS_DETECTED"
        elif med > 0:
            verdict = "MODERATE_TERMS_REQUIRING_REVIEW"
        else:
            verdict = "BALANCED_CONTRACT_TERMS"

        return RiskSummary(
            total_risks=len(risks),
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            overall_health_verdict=verdict
        )


# Global singleton instance
risk_engine = RiskEngine()

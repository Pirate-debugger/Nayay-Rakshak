"""
Action Navigator — Orchestrator Engine
=======================================
Coordinates all extractors, mappers, and the escalation evaluator to produce
a complete ActionNavigatorResponse.

Data flow:
  1. Receive pre-loaded AnalysisResult + RiskEngineResult
  2. Run all deterministic extractors (no LLM calls)
  3. Evaluate escalation triggers (deterministic)
  4. Assemble and return ActionNavigatorResponse

No AI inference happens in this engine.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.schemas.action_navigator import (
    NAVIGATOR_DISCLAIMER,
    ActionNavigatorResponse,
)
from app.services.action_navigator.escalation import (
    compute_professional_review_urgency,
    evaluate_escalation,
)
from app.services.action_navigator.extractors import (
    extract_important_dates,
    extract_important_documents,
    extract_known_facts,
    extract_unknown_facts,
)
from app.services.action_navigator.issue_mapper import map_risks_to_issues
from app.services.action_navigator.step_generator import (
    build_next_steps,
    build_questions,
)

logger = logging.getLogger("nyaya_rakshak.action_navigator")


class ActionNavigatorEngine:
    """
    Deterministic Action Navigator orchestrator.

    Usage:
        engine = ActionNavigatorEngine()
        response = engine.generate(
            document_id=1,
            document_title="Residential Lease Agreement",
            document_full_text="...",
            analysis_clauses_json="[...]",
            analysis_risks_json="[...]",
            analysis_obligations_json="[...]",
            analysis_missing_clauses_json="[...]",
            risk_engine_result=RiskEngineResult(...),
        )
    """

    VERSION = "2024.1.0"

    def generate(
        self,
        *,
        document_id: int,
        document_title: str,
        document_full_text: str,
        analysis_clauses_json: str,
        analysis_risks_json: str,
        analysis_obligations_json: str,
        analysis_missing_clauses_json: str,
        risk_engine_result: Any,  # RiskEngineResult
    ) -> ActionNavigatorResponse:

        # ── Deserialize ──────────────────────────────────────────────────────
        clauses: List[Dict] = self._safe_json(analysis_clauses_json)
        analysis_risks: List[Dict] = self._safe_json(analysis_risks_json)
        obligations: List[Dict] = self._safe_json(analysis_obligations_json)
        missing_clauses: List[Dict] = self._safe_json(analysis_missing_clauses_json)

        risk_records = getattr(risk_engine_result, "risks", [])
        missing_protections = getattr(risk_engine_result, "missing_protections", [])

        logger.info(
            "ActionNavigator generating plan",
            extra={
                "document_id": document_id,
                "clauses": len(clauses),
                "analysis_risks": len(analysis_risks),
                "obligations": len(obligations),
                "risk_engine_risks": len(risk_records),
            },
        )

        # ── Section 1: Known Facts ────────────────────────────────────────────
        known_facts = extract_known_facts(clauses, obligations)

        # ── Section 2: Unknown Facts ──────────────────────────────────────────
        unknown_facts = extract_unknown_facts(analysis_risks, missing_clauses, risk_records)

        # ── Section 3: Important Documents ───────────────────────────────────
        important_documents = extract_important_documents(clauses, analysis_risks, obligations)

        # ── Section 4: Important Dates ────────────────────────────────────────
        important_dates = extract_important_dates(clauses, obligations)

        # ── Section 5: Potential Issues ───────────────────────────────────────
        potential_issues = map_risks_to_issues(analysis_risks, risk_records, missing_protections)

        # ── Section 6 & 7: Questions + Next Steps ────────────────────────────
        # Escalation must be evaluated first (some steps depend on it)
        escalation_triggers = evaluate_escalation(
            risk_engine_result=risk_engine_result,
            analysis_risks=analysis_risks,
            document_full_text=document_full_text,
        )

        questions_to_ask = build_questions(risk_records, missing_protections, analysis_risks)

        next_steps = build_next_steps(
            risk_records=risk_records,
            missing_protections=missing_protections,
            analysis_risks=analysis_risks,
            obligations=obligations,
            missing_clauses=missing_clauses,
            escalation_triggers=escalation_triggers,
        )

        # ── Section 8: Escalation / Professional Help ─────────────────────────
        professional_review_recommended = bool(escalation_triggers)
        professional_review_urgency = compute_professional_review_urgency(escalation_triggers)

        return ActionNavigatorResponse(
            document_id=document_id,
            document_title=document_title,
            engine_version=self.VERSION,
            known_facts=known_facts,
            unknown_facts=unknown_facts,
            important_documents=important_documents,
            important_dates=important_dates,
            potential_issues=potential_issues,
            questions_to_ask=questions_to_ask,
            possible_next_steps=next_steps,
            when_to_seek_professional_help=escalation_triggers,
            professional_review_recommended=professional_review_recommended,
            professional_review_urgency=professional_review_urgency,
            disclaimer=NAVIGATOR_DISCLAIMER,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_json(raw: Optional[str]) -> List[Dict]:
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            logger.warning("ActionNavigatorEngine: failed to parse JSON field")
            return []


# Module-level singleton
action_navigator_engine = ActionNavigatorEngine()

"""
NYAYA RAKSHAK - Safety Gate
Enforces strict epistemic humility and verification gating:
1. NEVER display unsupported claims as established facts; hedge appropriately.
2. Transparently present conflicting statutory/documentary assertions.
3. CRITICAL RULE: NEVER claim to be "hallucination-free" or promise 100% legal infallibility.
"""

import re
from typing import List, Tuple
from app.schemas.verification import (
    ClaimVerificationDetail,
    VerificationStatus,
)


class SafetyGate:
    """Gates generated responses, injects hedging on unverified claims, and suppresses false accuracy guarantees."""

    FORBIDDEN_ACCURACY_CLAIMS = [
        r"100%\s*(?:hallucination-?free|error-?free|accurate)",
        r"(?:zero|no)\s+hallucination",
        r"completely\s+(?:error-?free|hallucination-?free)",
        r"guaranteed\s+(?:to\s+be\s+)?legally\s+binding",
        r"infallible\s+legal\s+advice",
        r"certified\s+legal\s+truth"
    ]

    def gate_and_finalize(
        self,
        draft_answer: str,
        claims: List[ClaimVerificationDetail]
    ) -> Tuple[str, str, bool]:
        """
        Evaluates draft response against verified claims.
        Returns:
        (final_response_text, safety_gate_action, never_hallucination_free_compliance)
        """
        actions = []
        final_text = draft_answer
        compliance = True

        # 1. Enforce NEVER CLAIM HALLUCINATION-FREE rule
        for pattern in self.FORBIDDEN_ACCURACY_CLAIMS:
            if re.search(pattern, final_text, flags=re.IGNORECASE):
                final_text = re.sub(
                    pattern,
                    "evidence-grounded legal clarity (advocate consultation recommended)",
                    final_text,
                    flags=re.IGNORECASE
                )
                actions.append("REDACTED_HALLUCINATION_FREE_CLAIM")

        # 2. Process Unsupported and Conflicting Claims
        hedged_paragraphs = []
        has_unsupported = False
        has_conflicting = False

        for claim in claims:
            if claim.verification_status == VerificationStatus.UNSUPPORTED:
                has_unsupported = True
                claim.hedged_text = (
                    f"Note on unverified assertion: '{claim.claim_text}' — "
                    "This claim is NOT confirmed by authoritative statutory records or uploaded document evidence. "
                    "It should not be relied upon as established legal fact."
                )
            elif claim.verification_status == VerificationStatus.CONFLICTING:
                has_conflicting = True
                claim.hedged_text = (
                    f"Statutory Conflict: '{claim.claim_text}' appears to directly conflict with governing Indian legal provisions "
                    f"(e.g. {claim.matched_evidence_id or 'applicable statutory doctrine'}). "
                    "Under Indian jurisprudence, statutory mandates typically override conflicting contractual stipulations, "
                    "though judicial determination is necessary."
                )
            elif claim.verification_status == VerificationStatus.PARTIALLY_SUPPORTED:
                claim.hedged_text = (
                    f"Partially supported: '{claim.claim_text}' is partially grounded in retrieved sources, "
                    "but specific scope or procedural conditions require caution."
                )

        if has_unsupported:
            actions.append("HEDGED_UNSUPPORTED_CLAIMS")
            unsupported_notes = "\n".join([
                f"- ⚠️ {c.hedged_text}" for c in claims if c.verification_status == VerificationStatus.UNSUPPORTED
            ])
            final_text += f"\n\n### ⚠️ Verification Caveats & Unverified Assertions\n{unsupported_notes}"

        if has_conflicting:
            actions.append("CONFLICT_HIGHLIGHTED")
            conflict_notes = "\n".join([
                f"- ⚖️ {c.hedged_text}" for c in claims if c.verification_status == VerificationStatus.CONFLICTING
            ])
            final_text += f"\n\n### ⚖️ Identified Legal & Document Conflicts\n{conflict_notes}"

        if not actions:
            actions.append("PASSED")

        safety_gate_action = " & ".join(actions)
        return final_text, safety_gate_action, compliance


safety_gate = SafetyGate()

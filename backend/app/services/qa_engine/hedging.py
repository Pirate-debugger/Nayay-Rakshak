"""
NYAYA RAKSHAK - Q&A Epistemic Hedging & Outcome Gate
Enforces strict prohibitions against outcome guarantees:
NEVER SAY:
  - "You will win."
  - "This is definitely legal."
  - "Your case will succeed."
  - "This clause is void/invalid as a matter of fact."
  - "You have no liability."
PREFER:
  - "Based on the available information..."
  - "This appears to..."
  - "I could not verify..."
  - "This should be confirmed by a qualified professional..."
"""

import re
from typing import List, Tuple


class QAHedgingGate:
    """Detects and replaces outcome guarantees and absolute certainty assertions in legal answers."""

    FORBIDDEN_OUTCOME_PATTERNS = [
        (r"(?i)\byou\s+will\s+(?:definitely\s+)?win\b", "your position may find statutory support, though outcomes depend on judicial determination"),
        (r"(?i)\bthis\s+is\s+definitely\s+legal\b", "this appears consistent with customary statutory principles based on current information"),
        (r"(?i)\bthis\s+is\s+definitely\s+(?:illegal|unlawful)\b", "this appears problematic under governing Indian statutory provisions"),
        (r"(?i)\byour\s+case\s+will\s+succeed\b", "your matter presents tenable legal arguments, subject to evidence and court discretion"),
        (r"(?i)\b(?:guaranteed|certain)\s+to\s+(?:win|succeed)\b", "strongly arguable, but never guaranteed in legal proceedings"),
        (r"(?i)\bthis\s+clause\s+is\s+(?:completely\s+)?void\b", "this clause appears vulnerable to challenge under statutory grounds"),
        (r"(?i)\byou\s+have\s+no\s+liability\b", "your liability appears limited based on the available terms"),
        (r"(?i)\b100%\s*(?:legal|binding|winnable)\b", "substantially supported by available documentation"),
    ]

    def enforce_hedging(self, text: str) -> Tuple[str, bool]:
        """
        Rewrites absolute assertions into epistemically responsible legal phrasing.
        Returns: (hedged_text, was_modified)
        """
        modified = False
        hedged = text

        for pattern, replacement in self.FORBIDDEN_OUTCOME_PATTERNS:
            if re.search(pattern, hedged):
                hedged = re.sub(pattern, replacement, hedged)
                modified = True

        # Prepend epistemic qualifier if text begins too assertively without hedging
        hedged_lower = hedged.lower()
        if not any(k in hedged_lower for k in [
            "based on the available information",
            "this appears to",
            "could not verify",
            "should be confirmed by a qualified",
            "under governing statutory principles"
        ]):
            # If plain language explanation doesn't contain a gentle epistemic frame, add one
            if len(hedged.strip()) > 0 and not hedged.startswith("Note:") and not hedged.startswith("Based on"):
                hedged = f"Based on the available information, {hedged[0].lower() + hedged[1:]}"
                modified = True

        return hedged, modified


qa_hedging_gate = QAHedgingGate()

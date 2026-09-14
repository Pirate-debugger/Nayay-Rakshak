"""
NYAYA RAKSHAK - Versioned Deterministic Risk Rules
Implements rule-based risk detection for objective conditions.
All rules are versioned, documented, and auditable.
DO NOT let the LLM alone determine risk.
"""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional

from app.schemas.risk import (
    EvidenceLocation,
    FindingType,
    RiskCategory,
    RiskRecord,
    RiskSeverity,
    RuleChangelogEntry,
    RuleVersionInfo,
)


RULESET_VERSION = "2024.1.0"


class BaseRiskRule(ABC):
    """Abstract base class for all versioned deterministic risk rules."""
    rule_id: str
    version: str = RULESET_VERSION
    category: RiskCategory
    default_severity: RiskSeverity
    title: str
    description: str
    statutory_cross_reference: Optional[str] = None
    changelog: List[RuleChangelogEntry] = []

    @abstractmethod
    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        """
        Evaluate a clause or document section.
        Returns a RiskRecord if an objective risk condition is met, else None.
        """
        pass

    def get_info(self) -> RuleVersionInfo:
        return RuleVersionInfo(
            rule_id=self.rule_id,
            version=self.version,
            category=self.category,
            default_severity=self.default_severity,
            title=self.title,
            description=self.description,
            statutory_reference=self.statutory_cross_reference,
            changelog=self.changelog
        )


# =====================================================================
# 1. LIABILITY RULES
# =====================================================================

class UnlimitedLiabilityRule(BaseRiskRule):
    """Detects absence of liability caps or explicit unlimited liability."""
    rule_id = "RULE-LIA-001"
    category = RiskCategory.LIABILITY
    default_severity = RiskSeverity.CRITICAL
    title = "Potential Concern: Unlimited or Uncapped Liability Exposure"
    description = "Clause imposes unlimited liability or expressly disclaims any monetary cap on damages."
    statutory_cross_reference = "Indian Contract Act, 1872 § 73 (Remoteness of Damages)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial versioned rule detecting uncapped liability and cap disclaimers."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"unlimited\s+liability",
            r"liability\s+shall\s+(?:not\s+be\s+limited|be\s+unlimited)",
            r"without\s+limitation\s+of\s+liability",
            r"no\s+cap\s+(?:on|of)\s+liability",
            r"shall\s+be\s+liable\s+for\s+any\s+and\s+all\s+(?:losses|damages)\s+without\s+limit",
            r"in\s+no\s+event\s+shall.*be\s+constrained\s+by\s+any\s+monetary\s+(?:cap|ceiling|limit)",
        ]
        match = None
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                match = m
                break

        if match:
            start_idx = match.start()
            end_idx = match.end()
            snippet = text[max(0, start_idx - 30):min(len(text), end_idx + 80)].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding="Clause appears broader than standard commercial practice by disclaiming liability caps and exposing the party to unlimited claims.",
                plain_language_explanation="Potential concern: Under this clause, if a dispute arises, the counterparty could theoretically demand uncapped compensation, risking your finances. Note that definitive legal validity cannot be established without judicial review.",
                why_it_matters="Without a reasonable liability cap (e.g., capped at fees paid over the preceding 12 months), a single dispute can cause severe financial distress.",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=start_idx,
                    char_end=end_idx
                ),
                affected_party="Signatory / Service Provider / Tenant",
                confidence=0.98,
                recommended_question="Can we cap aggregate liability under this agreement to fees paid over the preceding 6 or 12 months?",
                professional_review_recommended=True,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.DETERMINISTIC_RULE,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


class GrossNegligenceWaiverRule(BaseRiskRule):
    """Detects broad liability waivers that purport to excuse gross negligence or willful default."""
    rule_id = "RULE-LIA-002"
    category = RiskCategory.LIABILITY
    default_severity = RiskSeverity.CRITICAL
    title = "Potential Concern: Waiver of Liability for Gross Negligence or Willful Misconduct"
    description = "Clause disclaims liability even for deliberate default, intentional misconduct, or gross negligence."
    statutory_cross_reference = "Indian Contract Act, 1872 § 23 (Agreements Opposed to Public Policy)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying waivers of gross negligence and public policy overreach."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"not\s+be\s+liable\s+for.*(?:gross\s+negligence|willful\s+misconduct)",
            r"waiv\w*\s+(?:any\s+and\s+all\s+)?claims.*regardless\s+of\s+(?:negligence|fault)",
            r"regardless\s+of\s+(?:negligence|fault)",
            r"no\s+liability.*even\s+if\s+caused\s+by.*intentional\s+acts",
        ]
        match = None
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                match = m
                break

        if match:
            snippet = text[max(0, match.start() - 20):min(len(text), match.end() + 80)].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding="Clause appears broader than customary legal bounds by attempting to exculpate a party from liability for intentional fault or gross negligence.",
                plain_language_explanation="Potential concern: The clause suggests the other side cannot be held liable even if they cause harm through reckless or intentional acts. Legal validity cannot be established without judicial determination.",
                why_it_matters="Clauses that attempt to excuse gross negligence or fraud are commonly challenged under public policy (Section 23 of ICA 1872).",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=match.start(),
                    char_end=match.end()
                ),
                affected_party="Citizen / Client / Tenant",
                confidence=0.96,
                recommended_question="Can we explicitly carve out gross negligence, fraud, and willful misconduct from any liability exclusion?",
                professional_review_recommended=True,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.DETERMINISTIC_RULE,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


# =====================================================================
# 2. TIME / DEADLINE RULES
# =====================================================================

class ShortNoticePeriodRule(BaseRiskRule):
    """Detects unusually short notice periods (< 7 days or immediate without cure)."""
    rule_id = "RULE-TIM-001"
    category = RiskCategory.TIME_DEADLINE
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Unusually Short Notice Period (< 7 Days)"
    description = "Requires exit, termination, or cure on unreasonably short notice of less than 7 days or immediately."
    statutory_cross_reference = "Model Tenancy Act, 2021 § 21 (Notice Standards)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying sub-7-day notice and immediate eviction triggers."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        durations = deterministic_facts.get("durations", [])
        short_dur = False
        matched_str = ""

        for d in durations:
            days = d.get("days_equivalent") or d.get("duration_days") or 0
            if 0 < days < 7 and any(k in t_lower for k in ["notice", "terminate", "evict", "vacate", "cure"]):
                short_dur = True
                matched_str = d.get("raw_text") or d.get("raw_match") or f"{days} days"
                break

        patterns = [
            r"\b(?:immediate(?:ly)?|instant(?:aneous)?)\s+(?:terminate|cancel|vacate|evict)\b",
            r"(?:terminate|cancel|vacate)\s+(?:with\s+immediate\s+effect|on\s+immediate\s+notice)",
            r"(?:notice\s+of\s+less\s+than\s+7\s+days|[1-6]\s+days?\s+notice)",
            r"\b(?:24|48|72)\s+hours?\s+notice\b",
            r"forthwith\s+without\s+(?:prior\s+)?(?:notice|intimation)"
        ]
        match = None
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                match = m
                matched_str = text[m.start():m.end()]
                break

        if short_dur or match:
            snippet = text[:180].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding=f"Clause establishes a precipitous notice timeframe ({matched_str}) under 7 days, which appears narrower than customary commercial standards.",
                plain_language_explanation="Potential concern: The contract allows the counterparty to terminate or demand action on extremely short notice, leaving little time to respond or cure defaults. Worth reviewing before signing.",
                why_it_matters="Customary residential and commercial standards require a minimum 15 to 30 days notice to prevent abrupt disruption.",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=0,
                    char_end=len(snippet)
                ),
                affected_party="Tenant / Employee / Contractor",
                confidence=0.96,
                recommended_question="Can we establish a reciprocal 30-day written notice requirement and a minimum 15-day cure period for remediable defaults?",
                professional_review_recommended=False,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.DETERMINISTIC_RULE,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


class UnreasonableCurePeriodRule(BaseRiskRule):
    """Detects absence of cure period or unreasonable cure timeframe (< 7 days)."""
    rule_id = "RULE-TIM-002"
    category = RiskCategory.TIME_DEADLINE
    default_severity = RiskSeverity.MEDIUM
    title = "Worth Reviewing: Insufficient or Absent Breach Cure Period"
    description = "Provides less than 7 days or zero opportunity to rectify a remediable breach before immediate termination."
    statutory_cross_reference = "Indian Contract Act, 1872 § 39"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule checking for absence or shortness of breach cure periods."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"without\s+(?:any\s+)?(?:cure\s+period|opportunity\s+to\s+cure|grace\s+period)",
            r"cure\s+(?:the\s+breach\s+)?within\s+(?:[1-4]\s+days|24\s+hours|48\s+hours)",
            r"immediate\s+forfeiture\s+upon\s+(?:any\s+)?breach",
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears narrower than standard commercial practice by omitting a reasonable cure window for remediable breaches.",
                    plain_language_explanation="Worth reviewing: You may not be given adequate time to fix minor or accidental administrative defaults before severe contract penalties or termination take effect.",
                    why_it_matters="Standard contracts provide a 15 to 30 day written notice and cure period before declaring an incurable breach.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Signatory / Tenant / Service Provider",
                    confidence=0.91,
                    recommended_question="Can we stipulate that any notice of default must provide at least 15 business days to cure remediable non-compliance?",
                    professional_review_recommended=False,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 3. INDEMNITY RULES
# =====================================================================

class UncappedIndemnityRule(BaseRiskRule):
    """Detects broad or uncapped indemnification obligations."""
    rule_id = "RULE-IND-001"
    category = RiskCategory.INDEMNITY
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Uncapped or Asymmetric Indemnity Covenant"
    description = "Imposes broad obligation to indemnify against consequential or third-party claims without reciprocal protection."
    statutory_cross_reference = "Indian Contract Act, 1872 § 124 & § 125 (Contract of Indemnity)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying broad or uncapped indemnification provisions."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if "indemn" in t_lower:
            patterns = [
                r"indemnify.*hold\s+harmless.*(?:all|any)\s+claims",
                r"indemnify.*consequential.*indirect.*punitive",
                r"solely\s+indemnify",
                r"indemnif.*without\s+(?:cap|limit)",
                r"fullest\s+extent\s+permitted\s+by\s+law.*indemnif",
                r"unconditionally\s+agrees\s+to\s+indemnify",
            ]
            for p in patterns:
                m = re.search(p, t_lower)
                if m:
                    snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                    return RiskRecord(
                        risk_id=f"RISK-{self.rule_id}",
                        category=self.category,
                        severity=self.default_severity,
                        title=self.title,
                        finding="Clause appears broader than standard commercial practice by imposing broad indemnification covering indirect or third-party liabilities without explicit limitation.",
                        plain_language_explanation="Potential concern: You are agreeing to pay all legal costs and damages the other party suffers, even if caused by third parties or indirect factors outside your direct operational control.",
                        why_it_matters="An uncapped indemnity bypasses statutory mitigation requirements and can hold you liable for legal fees far exceeding the contract value.",
                        evidence=EvidenceLocation(
                            page_number=page_number,
                            section_heading=section_heading,
                            verbatim_quote=snippet,
                            char_start=m.start(),
                            char_end=m.end()
                        ),
                        affected_party="Indemnifying Party / Citizen",
                        confidence=0.94,
                        recommended_question="Can we limit indemnity strictly to direct damages caused solely by our gross negligence or willful misconduct, subject to our overall liability cap?",
                        professional_review_recommended=True,
                        rule_id=self.rule_id,
                        rule_version=self.version,
                        finding_type=FindingType.DETERMINISTIC_RULE,
                        statutory_cross_reference=self.statutory_cross_reference
                    )
        return None


class IndemnityForCounterpartyFaultRule(BaseRiskRule):
    """Detects clauses where a party indemnifies the counterparty for the counterparty's own negligence."""
    rule_id = "RULE-IND-002"
    category = RiskCategory.INDEMNITY
    default_severity = RiskSeverity.CRITICAL
    title = "Potential Concern: Indemnification for Counterparty's Own Acts or Negligence"
    description = "Requires one party to indemnify the other party even when damages arise from the other party's own negligence or structural defaults."
    statutory_cross_reference = "Indian Contract Act, 1872 § 23 & § 124"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying indemnity for counterparty's own fault."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if "indemn" in t_lower:
            patterns = [
                r"indemnify.*regardless\s+of\s+(?:lessor|company|landlord)\s*(?:'s)?\s+(?:negligence|fault)",
                r"indemnify.*whether\s+or\s+not\s+caused\s+by\s+(?:the\s+)?(?:lessor|company|landlord)",
                r"indemnify.*even\s+if\s+arising\s+from.*acts\s+of\s+(?:the\s+)?(?:lessor|company|landlord)"
            ]
            for p in patterns:
                m = re.search(p, t_lower)
                if m:
                    snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                    return RiskRecord(
                        risk_id=f"RISK-{self.rule_id}",
                        category=self.category,
                        severity=self.default_severity,
                        title=self.title,
                        finding="Clause appears broader than customary legal practice by requiring you to pay damages caused by the counterparty's own negligence or building defects.",
                        plain_language_explanation="Potential concern: Under this clause, if the counterparty causes damage through their own carelessness, you are still obligated to pay for it. Legal validity cannot be established without judicial review.",
                        why_it_matters="Compelling one party to pay for the other's own reckless acts violates standard indemnity principles under Section 124 of the ICA.",
                        evidence=EvidenceLocation(
                            page_number=page_number,
                            section_heading=section_heading,
                            verbatim_quote=snippet,
                            char_start=m.start(),
                            char_end=m.end()
                        ),
                        affected_party="Indemnifying Party / Tenant",
                        confidence=0.97,
                        recommended_question="Can we explicitly carve out the counterparty's own negligence, omission, or breach from the indemnity obligation?",
                        professional_review_recommended=True,
                        rule_id=self.rule_id,
                        rule_version=self.version,
                        finding_type=FindingType.DETERMINISTIC_RULE,
                        statutory_cross_reference=self.statutory_cross_reference
                    )
        return None


# =====================================================================
# 4. RENEWAL RULES
# =====================================================================

class AutomaticRenewalRule(BaseRiskRule):
    """Detects automatic evergreen renewal with restrictive opt-out provisions."""
    rule_id = "RULE-REN-001"
    category = RiskCategory.RENEWAL
    default_severity = RiskSeverity.MEDIUM
    title = "Worth Reviewing: Automatic Evergreen Renewal Clause"
    description = "Contract renews automatically for successive periods unless formal notice is given in a narrow window."
    statutory_cross_reference = "Consumer Protection Act, 2019 § 2(46) (Unfair Contract Terms)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying evergreen renewal clauses."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"automatic(?:ally)?\s+renew(?:al|s|ed)?",
            r"shall\s+renew\s+automatically",
            r"deemed\s+renewed",
            r"evergreen\s+(?:clause|provision|term)"
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 100)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause contains an automatic evergreen renewal mechanism that binds the party to successive terms unless affirmative cancellation is submitted.",
                    plain_language_explanation="Worth reviewing: If you forget to send an explicit written cancellation notice before the deadline, you may be automatically locked into paying for another full term.",
                    why_it_matters="Citizens and small businesses frequently lose money on forgotten auto-renewals that escalate fees without fresh affirmative consent.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Consumer / Tenant / Client",
                    confidence=0.92,
                    recommended_question="Can renewal require mutual affirmative written consent at least 30 days prior to expiry rather than automatic extension?",
                    professional_review_recommended=False,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 5. OBLIGATION ASYMMETRY RULES
# =====================================================================

class UnilateralAmendmentRule(BaseRiskRule):
    """Detects unilateral amendment rights without requirement of mutual consent."""
    rule_id = "RULE-ASY-001"
    category = RiskCategory.OBLIGATION_ASYMMETRY
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Unilateral Right to Amend Contract Terms"
    description = "Permits one party to modify terms, rates, or obligations unilaterally without prior approval."
    statutory_cross_reference = "Consumer Protection Act, 2019 § 2(46)(v) (Unilateral alteration of terms)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying unilateral amendment rights."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"(?:may|reserves\s+the\s+right\s+to)\s+(?:amend|modify|alter|change|increase)\s+.*(?:sole\s+discretion|at\s+any\s+time\s+without\s+notice|unilateral)",
            r"amend(?:ments)?\s+effective\s+immediately\s+upon\s+posting",
            r"without\s+(?:prior\s+)?(?:consent|approval|agreement)\s+of\s+the\s+(?:tenant|employee|client|user)",
            r"unilaterally\s+(?:alter|modify|amend|revise|increase)",
            r"reserves\s+the\s+unilateral\s+right\s+to\s+increase\s+rent",
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than standard bilateral contracts by granting one party the unconstrained power to alter contract obligations, fees, or rules without counterparty consent.",
                    plain_language_explanation="Potential concern: The other side claims the right to change key terms whenever they want, while you remain bound. Worth reviewing with legal counsel.",
                    why_it_matters="Contracts must be founded on mutual consensus (consensus ad idem). Unilateral amendment rights create severe obligation asymmetry.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Consumer / Tenant / User",
                    confidence=0.97,
                    recommended_question="Can all modifications require written agreement signed by both parties, with a right to terminate if changes are proposed?",
                    professional_review_recommended=True,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


class AsymmetricTerminationRule(BaseRiskRule):
    """Detects where one party has broad exit rights while counterparty is strictly locked in."""
    rule_id = "RULE-ASY-002"
    category = RiskCategory.OBLIGATION_ASYMMETRY
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Asymmetric Termination Rights (One-Sided Exit Privilege)"
    description = "One party retains an unfettered right to exit on short notice while the counterparty is denied termination rights or locked in."
    statutory_cross_reference = "Consumer Protection Act, 2019 § 2(46)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying one-sided termination privileges."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"(?:lessee|tenant|employee)\s+shall\s+have\s+no\s+right\s+to\s+terminate",
            r"(?:landlord|lessor|company)\s+(?:may|can)\s+terminate.*(?:tenant|lessee|employee)\s+(?:cannot|is\s+locked\s+in)",
            r"unfettered\s+right\s+to\s+terminate.*(?:lessee|tenant)\s+shall\s+have\s+no\s+right",
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than reciprocal commercial standards by reserving termination privileges exclusively for one party while locking in the other.",
                    plain_language_explanation="Potential concern: The counterparty can cancel the agreement at their convenience, but you are barred from exiting even if circumstances change drastically.",
                    why_it_matters="Asymmetric termination privileges expose the locked-in party to major commercial and operational vulnerability.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Tenant / Consumer / Employee",
                    confidence=0.96,
                    recommended_question="Can both parties have reciprocal rights to terminate on equal written notice (e.g. 30 or 60 days)?",
                    professional_review_recommended=True,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 6. FINANCIAL RULES
# =====================================================================

class MaterialFinancialPenaltyRule(BaseRiskRule):
    """Detects excessive late fees, interest >= 18% p.a., or daily flat fines."""
    rule_id = "RULE-FIN-001"
    category = RiskCategory.FINANCIAL
    default_severity = RiskSeverity.CRITICAL
    title = "Potential Concern: Exorbitant Financial Penalty or Interest Rate"
    description = "Imposes penal interest exceeding 18% per annum, compounding daily fines, or disproportionate forfeitures."
    statutory_cross_reference = "Indian Contract Act, 1872 § 74 (Compensation for Breach where Penalty Stipulated)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying penal interest rates and excessive daily compounding fines."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        percentages = deterministic_facts.get("percentages", [])
        high_pct = False
        pct_val = 0.0

        for p in percentages:
            val = p.get("value") or p.get("value_percent") or 0.0
            if val >= 18.0 and any(k in t_lower for k in ["interest", "penalty", "late", "default", "delay"]):
                high_pct = True
                pct_val = val
                break

        patterns = [
            r"(?:1[89]|[2-9][0-9])%\s*(?:p\.?a\.?|per\s+annum)?",
            r"(?:₹|rs\.?|inr)\s*(?:[5-9][0-9]{2}|[1-9][0-9]{3,})\s*(?:per|each)\s+day",
            r"daily\s+(?:compounding\s+)?penalty\s+of",
            r"forfeiture\s+of\s+(?:entire|all)\s+security\s+deposit",
            r"entire\s+security\s+deposit\s+shall\s+stand\s+(?:unconditionally\s+)?forfeited"
        ]
        match = None
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                match = m
                break

        if high_pct or match:
            snippet = text[:180].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding=f"Clause appears broader than reasonable compensatory damages by imposing severe penal charges ({pct_val if high_pct else 'daily fines/forfeiture'}) for delay or default.",
                plain_language_explanation="Potential concern: The contract charges steep compounding late fees or threatens total forfeiture of your deposit for payment delays. Legal validity cannot be established without judicial review.",
                why_it_matters="Under Section 74 of the Indian Contract Act, stipulations by way of penalty cannot exceed reasonable compensation for actual damage proved.",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=0,
                    char_end=len(snippet)
                ),
                affected_party="Borrower / Tenant / Payer",
                confidence=0.98,
                recommended_question="Can we align the late interest rate with commercial lending norms (e.g. 10-12% simple interest p.a.) with a 7-day grace period?",
                professional_review_recommended=True,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.DETERMINISTIC_RULE,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


class ExcessiveSecurityDepositRule(BaseRiskRule):
    """Detects security deposits exceeding 2 months rent or 90-day delayed return."""
    rule_id = "RULE-FIN-002"
    category = RiskCategory.FINANCIAL
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Excessive Security Deposit or Delayed Refund"
    description = "Deposit exceeds customary limits (2 months under Model Tenancy Act) or allows refund delays exceeding 30 days."
    statutory_cross_reference = "Model Tenancy Act, 2021 § 21 (Security Deposit Cap & Refund Timeline)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying excessive security deposits and delayed refund windows."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if any(k in t_lower for k in ["security deposit", "caution deposit"]):
            patterns = [
                r"(?:[3-9]|1[0-2])\s+months?\s+(?:rent\s+as\s+security\s+deposit|deposit)",
                r"(?:60|90|120|180)\s+days?\s+(?:to\s+refund|after\s+vacat|for\s+return)",
                r"refund(?:ed)?\s+within\s+(?:60|90|120)\s+days",
                r"non-refundable\s+security\s+deposit",
                r"equivalent\s+to\s+[3-9]\s+months\'?\s+rent",
            ]
            for p in patterns:
                m = re.search(p, t_lower)
                if m:
                    snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                    return RiskRecord(
                        risk_id=f"RISK-{self.rule_id}",
                        category=self.category,
                        severity=self.default_severity,
                        title=self.title,
                        finding="Clause appears broader than standard residential guidelines by demanding an excessive deposit (>2 months) or a prolonged refund window (>30 days).",
                        plain_language_explanation="Potential concern: Your money may be tied up for months after vacating, with arbitrary deductions. Worth reviewing before signing.",
                        why_it_matters="Section 21 of the Model Tenancy Act caps residential deposits to maximum 2 months rent and mandates prompt return upon handover.",
                        evidence=EvidenceLocation(
                            page_number=page_number,
                            section_heading=section_heading,
                            verbatim_quote=snippet,
                            char_start=m.start(),
                            char_end=m.end()
                        ),
                        affected_party="Tenant / Licensee",
                        confidence=0.95,
                        recommended_question="Can the security deposit be capped at 2 months rent, with return mandated within 14 days of keys handover post joint inspection?",
                        professional_review_recommended=False,
                        rule_id=self.rule_id,
                        rule_version=self.version,
                        finding_type=FindingType.DETERMINISTIC_RULE,
                        statutory_cross_reference=self.statutory_cross_reference
                    )
        return None


# =====================================================================
# 7. TERMINATION RULES
# =====================================================================

class SubjectiveTerminationRule(BaseRiskRule):
    """Detects subjective 'sole satisfaction' termination triggers."""
    rule_id = "RULE-TRM-001"
    category = RiskCategory.TERMINATION
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Subjective or Discretionary Termination Trigger"
    description = "Permits termination based on unprovable subjective standards like 'sole satisfaction' or 'deemed unsuitable'."
    statutory_cross_reference = "Indian Contract Act, 1872 § 39"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying subjective termination triggers."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"in\s+(?:its|the\s+company\'?s|the\s+landlord\'?s)\s+sole\s+(?:satisfaction|discretion|opinion)",
            r"if\s+(?:the\s+company|the\s+landlord)\s+deems?\s+(?:unfit|unsuitable|improper)",
            r"without\s+assigning\s+any\s+(?:reason|cause)\s+whatsoever",
            r"unfettered\s+right\s+to\s+terminate.*without\s+assigning"
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than standard objective breach criteria by enabling termination on purely subjective discretion.",
                    plain_language_explanation="Potential concern: You could be terminated or evicted simply because the other party 'feels' unsatisfied, even if you met all written contractual standards.",
                    why_it_matters="Subjective termination strips away contract stability and makes dispute challenges difficult without objective breach definitions.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Employee / Contractor / Tenant",
                    confidence=0.93,
                    recommended_question="Can termination for cause be conditioned upon specific, objective, and material breach criteria after written notice and cure period?",
                    professional_review_recommended=False,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


class RestraintOfTradeRule(BaseRiskRule):
    """Detects post-termination non-compete covenants."""
    rule_id = "RULE-TRM-002"
    category = RiskCategory.TERMINATION
    default_severity = RiskSeverity.CRITICAL
    title = "Potential Concern: Post-Employment Non-Compete Restraint"
    description = "Restricts the employee from working for competitors or in the same industry after termination of employment."
    statutory_cross_reference = "Indian Contract Act, 1872 § 27 (Agreement in Restraint of Trade Void)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying post-employment non-compete covenants."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"post-?(?:termination|employment)\s+non-?compete",
            r"(?:shall\s+not|agrees\s+not\s+to)\s+.*?(?:work\s+for|join|engage\s+with|consult).*?competitor",
            r"for\s+a\s+period\s+of\s+.*post-?termination.*shall\s+not",
            r"restrain(?:ed)?\s+from\s+exercising\s+a\s+lawful\s+profession",
            r"following\s+cessation\s+of\s+employment.*(?:shall\s+not|agrees\s+not\s+to).*?competitor",
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 100)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than permitted statutory bounds by attempting to restrain post-employment professional mobility and lawful livelihood.",
                    plain_language_explanation="Potential concern: The contract threatens to block you from taking another job in your field after leaving this company. Under Indian contract law principles, post-service non-compete clauses are routinely contested; however, legal validity cannot be established without judicial determination.",
                    why_it_matters="Under Section 27 of the Indian Contract Act, 1872 and Supreme Court jurisprudence (Percept D'Mark v. Zaheer Khan), post-service non-compete covenants face severe enforceability hurdles.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Employee / Consultant",
                    confidence=0.99,
                    recommended_question="Can this non-compete clause be clarified to apply only during active employment, in accordance with Section 27?",
                    professional_review_recommended=True,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


class UnclearTerminationConditionsRule(BaseRiskRule):
    """Detects vague, ambiguous, or undefined termination triggers."""
    rule_id = "RULE-TRM-003"
    category = RiskCategory.TERMINATION
    default_severity = RiskSeverity.HIGH
    title = "Worth Reviewing: Unclear or Undefined Termination Conditions"
    description = "Clause permits termination on vague triggers such as undefined material breach or at-will discretion without clear guidelines."
    statutory_cross_reference = "Indian Contract Act, 1872 § 29 (Agreements Void for Uncertainty)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying unclear termination triggers and undefined at-will clauses."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"terminate\s+(?:at\s+will|without\s+cause|at\s+any\s+time\s+without\s+reason)",
            r"terminated\s+for\s+any\s+breach\s+deemed\s+material",
            r"such\s+other\s+grounds\s+as\s+may\s+be\s+determined",
            r"terminate.*without\s+any\s+objective\s+standards"
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears ambiguous regarding the precise operational triggers required to invoke termination.",
                    plain_language_explanation="Worth reviewing: The contract uses vague phrasing for how and why termination can occur, creating uncertainty about your rights and notice obligations.",
                    why_it_matters="Ambiguous termination standards allow the stronger party to manufacture defaults without clear evidentiary proof.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Signatory / Tenant / Employee",
                    confidence=0.92,
                    recommended_question="Can we define an exhaustive list of specific 'Material Breaches' with a mandatory written cure window?",
                    professional_review_recommended=True,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 8. JURISDICTION RULES
# =====================================================================

class InconvenientJurisdictionRule(BaseRiskRule):
    """Detects foreign or distant jurisdiction clauses for domestic agreements."""
    rule_id = "RULE-JUR-001"
    category = RiskCategory.JURISDICTION
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Distant or Foreign Dispute Jurisdiction"
    description = "Designates distant state or overseas courts (e.g. Singapore, London, New York) for domestic Indian parties."
    statutory_cross_reference = "Code of Civil Procedure, 1908 § 20 (Place of Suing)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying foreign or distant domestic court designations."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if any(k in t_lower for k in ["jurisdiction", "governing law", "courts of"]):
            foreign_places = ["singapore", "london", "england", "new york", "delaware", "california", "dubai"]
            for place in foreign_places:
                if place in t_lower:
                    snippet = text[:150].strip()
                    return RiskRecord(
                        risk_id=f"RISK-{self.rule_id}",
                        category=self.category,
                        severity=self.default_severity,
                        title=self.title,
                        finding=f"Clause specifies foreign jurisdiction ({place.title()}) for resolving disputes under this agreement.",
                        plain_language_explanation=f"Potential concern: If a disagreement arises, you may be compelled to hire foreign lawyers and litigate in {place.title()} at prohibitive expense. Worth reviewing before signing.",
                        why_it_matters="For domestic agreements between Indian residents, foreign jurisdiction clauses create a severe practical and financial barrier to seeking justice.",
                        evidence=EvidenceLocation(
                            page_number=page_number,
                            section_heading=section_heading,
                            verbatim_quote=snippet,
                            char_start=0,
                            char_end=len(snippet)
                        ),
                        affected_party="Domestic Citizen / Indian Counterparty",
                        confidence=0.96,
                        recommended_question="Can the jurisdiction be modified to local courts in the city where services are rendered or property is situated?",
                        professional_review_recommended=True,
                        rule_id=self.rule_id,
                        rule_version=self.version,
                        finding_type=FindingType.DETERMINISTIC_RULE,
                        statutory_cross_reference=self.statutory_cross_reference
                    )
        return None


# =====================================================================
# 9. ARBITRATION RULES
# =====================================================================

class SoleArbitratorRule(BaseRiskRule):
    """Detects unilateral appointment of sole arbitrator."""
    rule_id = "RULE-ARB-001"
    category = RiskCategory.ARBITRATION
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Unilateral Appointment of Sole Arbitrator"
    description = "Grants one party exclusive authority to appoint the sole arbitrator."
    statutory_cross_reference = "Arbitration and Conciliation Act, 1996 § 12(5) (Ineligibility of Arbitrator)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying unilateral sole arbitrator appointments."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"sole\s+arbitrator\s+appointed\s+(?:solely\s+by|exclusively\s+by|at\s+the\s+discretion\s+of)\s+(?:the\s+company|the\s+landlord|the\s+lessor)",
            r"arbitrator\s+nominated\s+by\s+(?:the\s+managing\s+director|the\s+first\s+party)\s+alone",
            r"unilateral\s+appointment\s+of\s+arbitrator",
            r"sole\s+arbitrator\s+unilaterally\s+appointed"
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than impartial dispute guidelines by allowing one party to unilaterally select the sole arbitrator.",
                    plain_language_explanation="Potential concern: The sole arbitrator deciding your case would be chosen entirely by the other side. The Supreme Court has expressed serious concerns regarding arbitrator impartiality in unilateral appointments.",
                    why_it_matters="The Supreme Court of India (Perkins Eastman Architects v. HSCC) ruled that a party interested in the dispute outcome cannot unilaterally appoint the sole arbitrator.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Citizen / Counterparty",
                    confidence=0.98,
                    recommended_question="Can the arbitration clause specify mutual agreement on a retired judicial officer or appointment through the High Court Arbitration Centre?",
                    professional_review_recommended=True,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 10. PRIVACY RULES
# =====================================================================

class BroadDataPrivacyRule(BaseRiskRule):
    """Detects unconsented third-party data sharing or perpetual retention."""
    rule_id = "RULE-PRV-001"
    category = RiskCategory.PRIVACY
    default_severity = RiskSeverity.MEDIUM
    title = "Potential Concern: Unrestricted Personal Data Sharing or Retention"
    description = "Permits perpetual retention or sharing of user personal data with unspecified third parties."
    statutory_cross_reference = "Digital Personal Data Protection Act, 2023 § 6 & § 8"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule checking DPDP Act consent and retention boundaries."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if any(k in t_lower for k in ["personal data", "user data", "privacy", "information"]):
            patterns = [
                r"share.*personal\s+data.*third\s+parties.*without\s+notice",
                r"retain.*data.*in\s+perpetuity",
                r"unrestricted\s+right\s+to\s+monetize.*data",
                r"waives?\s+(?:all\s+)?privacy\s+rights"
            ]
            for p in patterns:
                m = re.search(p, t_lower)
                if m:
                    snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                    return RiskRecord(
                        risk_id=f"RISK-{self.rule_id}",
                        category=self.category,
                        severity=self.default_severity,
                        title=self.title,
                        finding="Clause appears broader than statutory data minimization principles by claiming expansive rights to retain or transfer personal data without granular purpose limitation.",
                        plain_language_explanation="Potential concern: The provider claims the right to keep your personal records indefinitely or share them with marketing affiliates without separate notice.",
                        why_it_matters="Under Section 6 & 8 of the DPDP Act 2023, data fiduciaries must specify clear purposes and erase personal data once the purpose is fulfilled.",
                        evidence=EvidenceLocation(
                            page_number=page_number,
                            section_heading=section_heading,
                            verbatim_quote=snippet,
                            char_start=m.start(),
                            char_end=m.end()
                        ),
                        affected_party="Data Principal / Consumer",
                        confidence=0.92,
                        recommended_question="Can you clarify data retention periods and provide explicit opt-in consent for any third-party disclosures under DPDP Act 2023?",
                        professional_review_recommended=False,
                        rule_id=self.rule_id,
                        rule_version=self.version,
                        finding_type=FindingType.DETERMINISTIC_RULE,
                        statutory_cross_reference=self.statutory_cross_reference
                    )
        return None


# =====================================================================
# 11. INTELLECTUAL PROPERTY RULES
# =====================================================================

class OverbroadIPAssignmentRule(BaseRiskRule):
    """Detects overbroad assignment of pre-existing or personal IP."""
    rule_id = "RULE-IP-001"
    category = RiskCategory.IP
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Overbroad Assignment of Background IP or Moral Rights"
    description = "Assigns personal inventions created outside working hours or demands waiver of inalienable moral rights."
    statutory_cross_reference = "Copyright Act, 1957 § 57 (Author's Special Rights)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying overbroad personal IP assignments."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"all\s+inventions.*whether\s+or\s+not\s+(?:made\s+during\s+working\s+hours|related\s+to\s+employment)",
            r"waives?\s+(?:all\s+)?moral\s+rights",
            r"assigns?\s+all\s+prior\s+and\s+future\s+intellectual\s+property",
            r"exclusive\s+ownership\s+of\s+all\s+ideas\s+conceived",
            r"whether\s+during\s+office\s+hours\s+or\s+personal\s+time"
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than standard employment scopes by claiming ownership over independent personal creative works developed on personal time.",
                    plain_language_explanation="Potential concern: The company claims ownership of things you build on your own personal time using your own equipment, even if unrelated to your company duties.",
                    why_it_matters="Section 57 of the Indian Copyright Act recognizes author moral rights. Standard employment assignments should carve out pre-existing and unrelated personal inventions.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Employee / Creator",
                    confidence=0.94,
                    recommended_question="Can we explicitly carve out pre-existing inventions and limit IP assignment strictly to works created directly for company projects using company resources?",
                    professional_review_recommended=True,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 12. AMBIGUITY RULES
# =====================================================================

class ConflictingClausesRule(BaseRiskRule):
    """Detects internal contractual contradictions (e.g. 30-day notice vs immediate lock-in)."""
    rule_id = "RULE-AMB-001"
    category = RiskCategory.AMBIGUITY
    default_severity = RiskSeverity.HIGH
    title = "Potential Concern: Conflicting Clause Terms in Contract"
    description = "Contradictory covenants across sections create legal ambiguity."
    statutory_cross_reference = "Indian Contract Act, 1872 § 29 (Agreements Void for Uncertainty)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying cross-clause internal contradictions."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if "lock-in" in t_lower and any(k in t_lower for k in ["notice of termination", "30 days notice", "terminate by giving notice"]):
            snippet = text[:150].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding="Clause appears ambiguous due to internal tension between an absolute lock-in restriction and a discretionary notice termination provision.",
                plain_language_explanation="Potential concern: One part of the agreement suggests you can terminate with notice, while another imposes an absolute lock-in prohibition.",
                why_it_matters="Conflicting terms create legal ambiguity, allowing the stronger party to enforce whichever clause is more advantageous to them.",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=0,
                    char_end=len(snippet)
                ),
                affected_party="Signatory / Tenant / Employee",
                confidence=0.95,
                recommended_question="Which clause supersedes the other: the notice provision or the absolute lock-in prohibition?",
                professional_review_recommended=True,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.CROSS_CLAUSE_CONFLICT,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


class AmbiguousDiscretionRule(BaseRiskRule):
    """Detects vague standards of performance or unilateral interpretation clauses."""
    rule_id = "RULE-AMB-002"
    category = RiskCategory.AMBIGUITY
    default_severity = RiskSeverity.MEDIUM
    title = "Worth Reviewing: Ambiguous Performance Standards or Sole Discretion"
    description = "Terms rely on undefined phrases like 'reasonable satisfaction' or unilateral interpretation powers."
    statutory_cross_reference = "Indian Contract Act, 1872 § 29"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule identifying vague discretionary standards."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        patterns = [
            r"sole\s+and\s+unreviewable\s+discretion",
            r"decision\s+of\s+(?:the\s+)?(?:company|landlord)\s+shall\s+be\s+final\s+and\s+binding",
            r"as\s+(?:the\s+)?(?:company|landlord)\s+may\s+deem\s+fit\s+from\s+time\s+to\s+time",
        ]
        for p in patterns:
            m = re.search(p, t_lower)
            if m:
                snippet = text[max(0, m.start() - 20):min(len(text), m.end() + 80)].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause appears broader than objective contracting norms by declaring one party's discretionary interpretation 'final and binding'.",
                    plain_language_explanation="Worth reviewing: The contract gives the other side the power to settle questions about performance without neutral dispute procedures.",
                    why_it_matters="Unilateral interpretation clauses undermine consensus ad idem and impede fair resolution of contractual disagreements.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=m.start(),
                        char_end=m.end()
                    ),
                    affected_party="Signatory / Tenant / Client",
                    confidence=0.90,
                    recommended_question="Can disputed interpretations be subject to mutual consultation and standard mediation rather than unilateral determination?",
                    professional_review_recommended=False,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.DETERMINISTIC_RULE,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


# =====================================================================
# 13. MISSING PROTECTION RULES
# =====================================================================

class MissingDisputeResolutionRule(BaseRiskRule):
    """Detects total absence of dispute resolution or governing law in the document."""
    rule_id = "RULE-MIS-001"
    category = RiskCategory.MISSING_PROTECTION
    default_severity = RiskSeverity.MEDIUM
    title = "Potential Concern: Missing Dispute Resolution or Governing Law Clause"
    description = "The agreement completely lacks a dispute resolution mechanism or defined governing law."
    statutory_cross_reference = "Code of Civil Procedure, 1908 § 20"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule checking document-level dispute resolution covenants."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        if doc_context and doc_context.get("is_whole_document"):
            doc_lower = text.lower()
            has_dispute = any(k in doc_lower for k in ["dispute resolution", "arbitration", "jurisdiction", "governing law", "courts of"])
            if not has_dispute:
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Document contains no defined dispute resolution procedure, forum, or governing law.",
                    plain_language_explanation="Potential concern: If a conflict occurs, there is no agreed roadmap (such as mediation or specified courts) for how to resolve it legally.",
                    why_it_matters="Without a clear dispute forum, civil litigation can become mired in jurisdictional challenges before reaching substantive merits.",
                    evidence=EvidenceLocation(
                        page_number=1,
                        section_heading="Document Structure",
                        verbatim_quote="Entire document lacks dispute resolution / governing law clause.",
                        char_start=0,
                        char_end=0
                    ),
                    affected_party="Both Parties",
                    confidence=0.95,
                    recommended_question="Can we add standard mediation and local court jurisdiction clauses to clarify dispute procedure?",
                    professional_review_recommended=False,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.MISSING_STATUTORY_PROTECTION,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


class MissingForceMajeureNoticeRule(BaseRiskRule):
    """Detects absence of clear force majeure notice or mitigation procedures."""
    rule_id = "RULE-MIS-002"
    category = RiskCategory.MISSING_PROTECTION
    default_severity = RiskSeverity.LOW
    title = "Worth Reviewing: Missing Force Majeure Notice Procedure"
    description = "Clause invokes Force Majeure but does not define written notice timelines or mitigation duties."
    statutory_cross_reference = "Indian Contract Act, 1872 § 56 (Frustration of Contract)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule checking Force Majeure procedural completeness."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if "force majeure" in t_lower and not any(k in t_lower for k in ["written notice", "within 7 days", "within 14 days", "mitigat"]):
            snippet = text[:150].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding="Clause mentions Force Majeure but omits defined written notice deadlines or reasonable mitigation duties.",
                plain_language_explanation="Worth reviewing: Neither party has a clear timeframe for declaring or verifying an uncontrollable event like a flood or pandemic.",
                why_it_matters="Without defined notice deadlines, either party could belatedly claim force majeure to excuse avoidable defaults.",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=0,
                    char_end=len(snippet)
                ),
                affected_party="Both Parties",
                confidence=0.90,
                recommended_question="Can we stipulate that written notice of force majeure must be submitted within 7 days with reasonable mitigation efforts?",
                professional_review_recommended=False,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.MISSING_STATUTORY_PROTECTION,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


class MissingDataReturnRule(BaseRiskRule):
    """Detects absence of post-termination confidential data return or deletion obligation."""
    rule_id = "RULE-MIS-003"
    category = RiskCategory.MISSING_PROTECTION
    default_severity = RiskSeverity.MEDIUM
    title = "Worth Reviewing: Missing Data Return or Destruction Obligation"
    description = "Agreement covers confidential information or personal data but lacks a mandatory return/destruction covenant upon termination."
    statutory_cross_reference = "Digital Personal Data Protection Act, 2023 § 8(7)"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule checking for missing post-termination data return or destruction clauses."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if any(k in t_lower for k in ["confidential information", "proprietary data", "personal data"]):
            if "terminat" in t_lower and not any(k in t_lower for k in ["return or destroy", "delete", "purge", "surrender"]):
                snippet = text[:150].strip()
                return RiskRecord(
                    risk_id=f"RISK-{self.rule_id}",
                    category=self.category,
                    severity=self.default_severity,
                    title=self.title,
                    finding="Clause references confidential or personal data but omits a mandatory post-termination return or destruction covenant.",
                    plain_language_explanation="Worth reviewing: When the contract ends, there is no explicit instruction requiring the party to return or delete your sensitive records.",
                    why_it_matters="Under Section 8(7) of the DPDP Act 2023, data fiduciaries must erase personal data once the commercial purpose is fulfilled.",
                    evidence=EvidenceLocation(
                        page_number=page_number,
                        section_heading=section_heading,
                        verbatim_quote=snippet,
                        char_start=0,
                        char_end=len(snippet)
                    ),
                    affected_party="Data Principal / Disclosing Party",
                    confidence=0.89,
                    recommended_question="Can we add an explicit clause requiring return or certified destruction of all confidential and personal data within 14 days of termination?",
                    professional_review_recommended=False,
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    finding_type=FindingType.MISSING_STATUTORY_PROTECTION,
                    statutory_cross_reference=self.statutory_cross_reference
                )
        return None


class MissingDepositReturnSLARule(BaseRiskRule):
    """Detects absence of clear deposit refund timeframe in tenancy agreement."""
    rule_id = "RULE-MIS-004"
    category = RiskCategory.MISSING_PROTECTION
    default_severity = RiskSeverity.MEDIUM
    title = "Worth Reviewing: Missing Deposit Refund Timeframe (SLA)"
    description = "Lease agreement demands a security deposit but fails to define an explicit timeline for refund upon surrender."
    statutory_cross_reference = "Model Tenancy Act, 2021 § 21"
    changelog = [
        RuleChangelogEntry(
            version="2024.1.0",
            effective_date="2024-01-01",
            description="Initial rule checking for missing deposit return deadlines."
        )
    ]

    def evaluate(
        self,
        text: str,
        deterministic_facts: Dict[str, Any],
        doc_context: Optional[Dict[str, Any]] = None,
        page_number: int = 1,
        section_heading: Optional[str] = None
    ) -> Optional[RiskRecord]:
        t_lower = text.lower()
        if "security deposit" in t_lower and not any(k in t_lower for k in ["within 7 days", "within 14 days", "within 30 days", "on vacating", "date of handing over"]):
            snippet = text[:150].strip()
            return RiskRecord(
                risk_id=f"RISK-{self.rule_id}",
                category=self.category,
                severity=self.default_severity,
                title=self.title,
                finding="Clause requires a security deposit but omits an explicit calendar deadline for inspection and refund upon handover.",
                plain_language_explanation="Worth reviewing: The contract mentions paying a deposit, but does not state exactly how many days the landlord has to return it after you move out.",
                why_it_matters="Without a contractual deadline, landlords can delay deposit refunds indefinitely without committing an explicit contractual breach.",
                evidence=EvidenceLocation(
                    page_number=page_number,
                    section_heading=section_heading,
                    verbatim_quote=snippet,
                    char_start=0,
                    char_end=len(snippet)
                ),
                affected_party="Tenant / Licensee",
                confidence=0.91,
                recommended_question="Can we stipulate that the security deposit must be refunded within 14 days of keys handover post joint inspection?",
                professional_review_recommended=False,
                rule_id=self.rule_id,
                rule_version=self.version,
                finding_type=FindingType.MISSING_STATUTORY_PROTECTION,
                statutory_cross_reference=self.statutory_cross_reference
            )
        return None


# =====================================================================
# RULE REGISTRY
# =====================================================================

class RiskRuleRegistry:
    """Registry maintaining all active versioned risk rules."""

    def __init__(self, version: str = RULESET_VERSION):
        self.version = version
        self._rules: Dict[str, BaseRiskRule] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        default_classes = [
            UnlimitedLiabilityRule,
            GrossNegligenceWaiverRule,
            ShortNoticePeriodRule,
            UnreasonableCurePeriodRule,
            UncappedIndemnityRule,
            IndemnityForCounterpartyFaultRule,
            AutomaticRenewalRule,
            UnilateralAmendmentRule,
            AsymmetricTerminationRule,
            MaterialFinancialPenaltyRule,
            ExcessiveSecurityDepositRule,
            SubjectiveTerminationRule,
            RestraintOfTradeRule,
            UnclearTerminationConditionsRule,
            InconvenientJurisdictionRule,
            SoleArbitratorRule,
            BroadDataPrivacyRule,
            OverbroadIPAssignmentRule,
            ConflictingClausesRule,
            AmbiguousDiscretionRule,
            MissingDisputeResolutionRule,
            MissingForceMajeureNoticeRule,
            MissingDataReturnRule,
            MissingDepositReturnSLARule,
        ]
        for cls in default_classes:
            inst = cls()
            self._rules[inst.rule_id] = inst

    def register(self, rule: BaseRiskRule) -> None:
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[BaseRiskRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> List[BaseRiskRule]:
        return list(self._rules.values())

    def get_rule_info(self, rule_id: str) -> Optional[RuleVersionInfo]:
        rule = self.get_rule(rule_id)
        return rule.get_info() if rule else None

    def get_all_rule_infos(self) -> List[RuleVersionInfo]:
        return [r.get_info() for r in self._rules.values()]


# Global default registry instance
risk_rule_registry = RiskRuleRegistry()

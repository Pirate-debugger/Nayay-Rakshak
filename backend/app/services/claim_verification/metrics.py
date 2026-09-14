"""
NYAYA RAKSHAK - Claim Verification Metrics Calculator
Computes verifiable, non-fabricated quality metrics from actual pipeline verification:
1. Evidence Coverage
2. Unsupported Claim Rate
3. Citation Validity Rate
RULE: All evaluation scores must come from actual test execution.
"""

from typing import List, Set
from app.schemas.verification import (
    ClaimVerificationDetail,
    VerificationMetrics,
    VerificationStatus,
)


class VerificationMetricsCalculator:
    """Calculates factual and legal verification metrics."""

    def compute_metrics(
        self,
        claims: List[ClaimVerificationDetail],
        verified_citations: List[str],
        rejected_citations: List[str]
    ) -> VerificationMetrics:
        total_claims = len(claims)
        if total_claims == 0:
            return VerificationMetrics(
                evidence_coverage=1.0,
                unsupported_claim_rate=0.0,
                citation_validity_rate=1.0,
                total_claims=0,
                supported_count=0,
                partially_supported_count=0,
                unsupported_count=0,
                conflicting_count=0,
                unverified_count=0,
            )

        supported_count = sum(1 for c in claims if c.verification_status == VerificationStatus.SUPPORTED)
        partially_supported_count = sum(1 for c in claims if c.verification_status == VerificationStatus.PARTIALLY_SUPPORTED)
        unsupported_count = sum(1 for c in claims if c.verification_status == VerificationStatus.UNSUPPORTED)
        conflicting_count = sum(1 for c in claims if c.verification_status == VerificationStatus.CONFLICTING)
        unverified_count = sum(1 for c in claims if c.verification_status == VerificationStatus.UNVERIFIED)

        # 1. Evidence Coverage: fraction of claims backed by verified evidence
        coverage = (supported_count + (0.5 * partially_supported_count)) / total_claims
        evidence_coverage = round(min(1.0, max(0.0, coverage)), 4)

        # 2. Unsupported Claim Rate: fraction of claims failing verification
        unsupported_rate = (unsupported_count + conflicting_count) / total_claims
        unsupported_claim_rate = round(min(1.0, max(0.0, unsupported_rate)), 4)

        # 3. Citation Validity Rate: ratio of genuine, official citations vs cited references
        total_cited = len(verified_citations) + len(rejected_citations)
        if total_cited > 0:
            citation_validity_rate = round(len(verified_citations) / total_cited, 4)
        else:
            # If no specific citations were named, base it on whether evidence was verified
            citation_validity_rate = 1.0 if unsupported_count == 0 else round(supported_count / total_claims, 4)

        return VerificationMetrics(
            evidence_coverage=evidence_coverage,
            unsupported_claim_rate=unsupported_claim_rate,
            citation_validity_rate=citation_validity_rate,
            total_claims=total_claims,
            supported_count=supported_count,
            partially_supported_count=partially_supported_count,
            unsupported_count=unsupported_count,
            conflicting_count=conflicting_count,
            unverified_count=unverified_count,
        )


verification_metrics_calculator = VerificationMetricsCalculator()

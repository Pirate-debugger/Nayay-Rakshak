from typing import Any, Dict, List, Optional

from app.schemas.comparison import (
    ClauseDiffItem,
    ComparisonCategory,
    ComparisonFindingItem,
    ComparisonResponse,
    DifferenceDimension,
    MaterialityLevel,
    RiskDeltaSummary,
    StructuralDiff,
)
from app.services.comparison.difference_analyzer import analyze_aligned_clause_pair
from app.services.comparison.matcher import match_document_clauses
from app.services.comparison.segmenter import ComparisonClause, segment_document_for_comparison


class SemanticComparisonEngine:
    """
    Deterministic + Semantic legal document comparison engine.
    Aligns clauses, detects structural shifts, and conducts deep multi-dimensional
    gap analysis across 9 dimensions.
    """

    def compare(
        self,
        base_document_id: int,
        base_title: str,
        base_text: str,
        target_document_id: int,
        target_title: str,
        target_text: str,
        base_chunks: Optional[List[Any]] = None,
        target_chunks: Optional[List[Any]] = None
    ) -> ComparisonResponse:
        # 1. Segment both documents
        clauses_a = segment_document_for_comparison(
            text=base_text,
            document_id=base_document_id,
            document_title=base_title,
            chunks=base_chunks
        )
        clauses_b = segment_document_for_comparison(
            text=target_text,
            document_id=target_document_id,
            document_title=target_title,
            chunks=target_chunks
        )

        # 2. Bipartite clause matching and structural diff
        aligned_pairs, structural_diff = match_document_clauses(clauses_a, clauses_b)

        # 3. Analyze each aligned pair
        findings: List[ComparisonFindingItem] = []
        dimensions_set = set()
        critical_warnings: List[str] = []
        target_high_risks = 0
        base_high_risks = 0

        for idx, pair in enumerate(aligned_pairs, start=1):
            finding = analyze_aligned_clause_pair(pair, idx)
            findings.append(finding)
            dimensions_set.add(finding.dimension.value)

            if finding.materiality == MaterialityLevel.CRITICAL or finding.category == ComparisonCategory.CONFLICTING:
                target_high_risks += 1
                critical_warnings.append(f"{finding.title}: {finding.difference_explanation}")
            elif finding.materiality == MaterialityLevel.MATERIAL and finding.category in [ComparisonCategory.MODIFIED, ComparisonCategory.NEW]:
                target_high_risks += 1

        # Check if documents are completely different
        is_completely_different = (
            structural_diff.aligned_clause_count == 0
            or (structural_diff.structural_alignment_score < 0.15 and len(clauses_a) > 2 and len(clauses_b) > 2)
        )

        # 4. Synthesize overall verdict
        if is_completely_different:
            net_verdict = "COMPLETELY_DIFFERENT_DOCUMENTS"
            overall_verdict = (
                f"The documents '{base_title}' and '{target_title}' appear to be completely different legal instruments. "
                f"Structural alignment is only {structural_diff.structural_alignment_score * 100:.0f}%, "
                f"with {structural_diff.missing_in_b_count} clauses unique to '{base_title}' and {structural_diff.new_in_b_count} clauses unique to '{target_title}'."
            )
            critical_warnings.insert(0, "Warning: These two documents are completely different legal instruments with almost no common clauses.")
        elif all(f.category == ComparisonCategory.IDENTICAL for f in findings):
            net_verdict = "IDENTICAL"
            overall_verdict = f"Documents '{base_title}' and '{target_title}' are semantically identical with zero material discrepancies across all {len(findings)} evaluated clauses."
        elif all(f.category in [ComparisonCategory.IDENTICAL, ComparisonCategory.SIMILAR] for f in findings):
            net_verdict = "BALANCED"
            overall_verdict = f"Documents '{base_title}' and '{target_title}' share substantially identical legal covenants with only minor stylistic variations and no material risk variance."
        elif target_high_risks > base_high_risks:
            net_verdict = "TARGET_MORE_HARSH"
            overall_verdict = (
                f"Comparison indicates that '{target_title}' introduces {target_high_risks} significant high-risk or conflicting modifications "
                f"compared to '{base_title}'. Key changes affect {', '.join(sorted(dimensions_set)[:4])}."
            )
        else:
            net_verdict = "BALANCED"
            overall_verdict = f"Comparison between '{base_title}' and '{target_title}' shows balanced terms without net escalation of citizen liability."

        summary = RiskDeltaSummary(
            base_high_risks=base_high_risks,
            target_high_risks=target_high_risks,
            net_risk_verdict=net_verdict,
            critical_warnings=critical_warnings
        )

        # 5. Assemble backwards-compatible ClauseDiffItem list
        clause_diffs: List[ClauseDiffItem] = []
        for f in findings:
            change_type_map = {
                ComparisonCategory.IDENTICAL: "UNCHANGED",
                ComparisonCategory.SIMILAR: "UNCHANGED",
                ComparisonCategory.MODIFIED: "MODIFIED",
                ComparisonCategory.CONFLICTING: "MODIFIED",
                ComparisonCategory.NEW: "ADDED",
                ComparisonCategory.REMOVED: "REMOVED",
                ComparisonCategory.MISSING: "REMOVED",
            }
            risk_delta_map = {
                MaterialityLevel.CRITICAL: "INCREASED_RISK",
                MaterialityLevel.MATERIAL: "INCREASED_RISK",
                MaterialityLevel.MEDIUM: "NEUTRAL",
                MaterialityLevel.MINOR: "NEUTRAL",
                MaterialityLevel.NEGLIGIBLE: "NEUTRAL",
            }

            b_text = f.document_a_evidence.verbatim_quote if f.document_a_evidence else None
            t_text = f.document_b_evidence.verbatim_quote if f.document_b_evidence else None

            clause_diffs.append(ClauseDiffItem(
                category=f.title,
                change_type=change_type_map.get(f.category, "MODIFIED"),
                base_text=b_text,
                target_text=t_text,
                risk_delta=risk_delta_map.get(f.materiality, "NEUTRAL"),
                impact_analysis=f.risk_implications or f.difference_explanation
            ))

        return ComparisonResponse(
            base_document_id=base_document_id,
            target_document_id=target_document_id,
            base_title=base_title,
            target_title=target_title,
            overall_verdict=overall_verdict,
            summary=summary,
            clause_diffs=clause_diffs,
            structural_diff=structural_diff,
            findings=findings,
            dimensions_analyzed=sorted(list(dimensions_set))
        )


def compare_legal_documents(
    base_document_id: int,
    base_title: str,
    base_text: str,
    target_document_id: int,
    target_title: str,
    target_text: str,
    base_chunks: Optional[List[Any]] = None,
    target_chunks: Optional[List[Any]] = None
) -> ComparisonResponse:
    """Convenience helper function to run semantic comparison."""
    engine = SemanticComparisonEngine()
    return engine.compare(
        base_document_id=base_document_id,
        base_title=base_title,
        base_text=base_text,
        target_document_id=target_document_id,
        target_title=target_title,
        target_text=target_text,
        base_chunks=base_chunks,
        target_chunks=target_chunks
    )

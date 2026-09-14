"""
Nyaya Rakshak - Semantic Legal Document Comparison Subsystem.
Provides structural diffs, bipartite clause matching, multi-dimensional semantic difference analysis,
and high-fidelity clause-level evidence.
"""

from app.services.comparison.engine import SemanticComparisonEngine, compare_legal_documents

__all__ = ["SemanticComparisonEngine", "compare_legal_documents"]

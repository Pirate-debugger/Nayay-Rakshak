"""
NYAYA RAKSHAK - Tier-Weighted Legal Reranker
Applies Reciprocal Rank Fusion (RRF) combined with statutory authority tier boosts.
Prioritizes Tier 1 (Official Legislation & Supreme Court) over secondary or web sources.
"""

from typing import Dict, List

from app.schemas.retrieval import RetrievalResultItem, SourceTier


class TierWeightedReranker:
    """Reranks candidate items from multiple retrieval streams using Tier Boosts and RRF."""

    TIER_WEIGHTS: Dict[SourceTier, float] = {
        SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS: 1.0,
        SourceTier.TIER_2_OFFICIAL_INSTITUTIONS: 0.8,
        SourceTier.TIER_3_REPUTABLE_SECONDARY: 0.5,
        SourceTier.TIER_4_GENERAL_WEB: 0.2,
    }

    def rerank(
        self,
        keyword_results: List[RetrievalResultItem],
        semantic_results: List[RetrievalResultItem],
        top_k: int = 5,
        rrf_k: int = 60,
    ) -> List[RetrievalResultItem]:
        """
        Combines keyword and semantic ranking streams using RRF boosted by source tier.
        Score = sum(1 / (rrf_k + rank_i)) * Tier_Weight
        """
        combined: Dict[str, RetrievalResultItem] = {}
        rrf_scores: Dict[str, float] = {}

        # 1. Process keyword stream
        for rank, item in enumerate(keyword_results):
            combined[item.item_id] = item
            rrf_scores[item.item_id] = rrf_scores.get(item.item_id, 0.0) + (
                1.0 / (rrf_k + rank + 1)
            )

        # 2. Process semantic stream
        for rank, item in enumerate(semantic_results):
            if item.item_id not in combined:
                combined[item.item_id] = item
            rrf_scores[item.item_id] = rrf_scores.get(item.item_id, 0.0) + (
                1.0 / (rrf_k + rank + 1)
            )

        # 3. Apply Tier Weighting
        reranked: List[RetrievalResultItem] = []
        for item_id, base_item in combined.items():
            tier_weight = self.TIER_WEIGHTS.get(base_item.tier, 0.5)
            final_rrf = rrf_scores[item_id] * tier_weight

            # Update final score
            updated_item = base_item.model_copy(
                update={"tier_boost": tier_weight, "final_score": round(final_rrf * 100, 4)}
            )
            reranked.append(updated_item)

        # 4. Sort descending
        reranked.sort(key=lambda x: x.final_score, reverse=True)
        return reranked[:top_k]


tier_weighted_reranker = TierWeightedReranker()

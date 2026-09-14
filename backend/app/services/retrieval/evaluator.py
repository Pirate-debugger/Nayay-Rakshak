"""
NYAYA RAKSHAK - Retrieval Evaluator
Computes standard Information Retrieval (IR) metrics:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (NDCG@K)
Evaluates statutory and document grounding against benchmark test queries.
"""

import math
from typing import Any, Dict, List

from app.schemas.retrieval import RetrievalResponse
from app.services.retrieval.retriever import legal_retriever


# Research Benchmark Test Queries with known ground-truth statutory targets
STANDARD_LEGAL_BENCHMARKS = [
    {
        "query": "What is the legal punishment for cheating under BNS 2023?",
        "expected_source_ids": ["BNS-2023-SEC-318"],
        "expected_intent": "legal-source"
    },
    {
        "query": "Is a post-employment non-compete clause enforceable under Indian law?",
        "expected_source_ids": ["ICA-1872-SEC-27", "SC-2006-PERCEPT-ZAHEER"],
        "expected_intent": "legal-source"
    },
    {
        "query": "What is the maximum residential security deposit allowed under Model Tenancy Act?",
        "expected_source_ids": ["MTA-2021-SEC-21"],
        "expected_intent": "legal-source"
    },
    {
        "query": "Can an interested party unilaterally appoint the sole arbitrator?",
        "expected_source_ids": ["SC-2019-PERKINS-EASTMAN"],
        "expected_intent": "legal-source"
    },
    {
        "query": "How to register an e-FIR for a stolen mobile under BNSS?",
        "expected_source_ids": ["BNSS-2023-SEC-173"],
        "expected_intent": "legal-source"
    }
]


class RetrievalEvaluator:
    """Evaluates IR performance of the Legal Retrieval engine."""

    def __init__(self, retriever=None):
        self.retriever = retriever or legal_retriever

    async def evaluate_benchmarks(
        self,
        benchmarks: List[Dict[str, Any]] = None,
        k_values: List[int] = None
    ) -> Dict[str, float]:
        benchmarks = benchmarks or STANDARD_LEGAL_BENCHMARKS
        k_values = k_values or [1, 3, 5]

        reciprocal_ranks: List[float] = []
        precisions_at_k: Dict[int, List[float]] = {k: [] for k in k_values}
        recalls_at_k: Dict[int, List[float]] = {k: [] for k in k_values}
        ndcgs_at_k: Dict[int, List[float]] = {k: [] for k in k_values}

        for item in benchmarks:
            q = item["query"]
            expected_ids = set(item["expected_source_ids"])
            resp: RetrievalResponse = await self.retriever.retrieve(query=q, top_k=max(k_values))
            retrieved_ids = [r.item_id for r in resp.reranked_items]

            # 1. Reciprocal Rank (MRR)
            first_rel_rank = 0
            for idx, rid in enumerate(retrieved_ids):
                if rid in expected_ids:
                    first_rel_rank = idx + 1
                    break
            rr = 1.0 / first_rel_rank if first_rel_rank > 0 else 0.0
            reciprocal_ranks.append(rr)

            # 2. Precision & Recall at K
            for k in k_values:
                top_k_ids = retrieved_ids[:k]
                relevant_found = sum(1 for rid in top_k_ids if rid in expected_ids)
                prec = relevant_found / k
                rec = relevant_found / max(1, len(expected_ids))
                precisions_at_k[k].append(prec)
                recalls_at_k[k].append(rec)

                # 3. NDCG at K
                dcg = 0.0
                for rank_idx, rid in enumerate(top_k_ids):
                    rel = 1.0 if rid in expected_ids else 0.0
                    dcg += rel / math.log2(rank_idx + 2)

                idcg = sum(1.0 / math.log2(i + 2) for i in range(min(k, len(expected_ids))))
                ndcg = dcg / idcg if idcg > 0 else 0.0
                ndcgs_at_k[k].append(ndcg)

        # Aggregate metrics
        metrics: Dict[str, float] = {
            "mrr": round(sum(reciprocal_ranks) / max(1, len(reciprocal_ranks)), 4),
        }
        for k in k_values:
            metrics[f"precision@{k}"] = round(sum(precisions_at_k[k]) / max(1, len(precisions_at_k[k])), 4)
            metrics[f"recall@{k}"] = round(sum(recalls_at_k[k]) / max(1, len(recalls_at_k[k])), 4)
            metrics[f"ndcg@{k}"] = round(sum(ndcgs_at_k[k]) / max(1, len(ndcgs_at_k[k])), 4)

        return metrics


retrieval_evaluator = RetrievalEvaluator()

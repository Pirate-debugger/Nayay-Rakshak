from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAIProvider(ABC):
    """Abstract interface for legal intelligence providers."""

    @abstractmethod
    async def analyze_document(self, text: str, title: str) -> Dict[str, Any]:
        """Extract clauses, risks, obligations, summaries, and missing protections."""
        pass

    @abstractmethod
    async def answer_question(self, question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Answer question strictly grounded in the document chunks."""
        pass

    @abstractmethod
    async def verify_claim(self, claim: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify factual/legal claim against document evidence & statutory knowledge base."""
        pass

    @abstractmethod
    async def compare_documents(
        self,
        base_title: str,
        base_text: str,
        target_title: str,
        target_text: str
    ) -> Dict[str, Any]:
        """Compare two documents semantically and produce risk delta analysis."""
        pass

    @abstractmethod
    async def interpret_clause(
        self,
        clause_text: str,
        deterministic_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Semantic interpretation of a clause, extracting obligations, rights, conditions, etc."""
        pass


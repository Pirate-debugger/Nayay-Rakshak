"""
NYAYA RAKSHAK - Legal Q&A Engine
Orchestrates the complete evidence-first, 8-part structured legal answering pipeline:
1. Question Requirement Determination (DOCUMENT_EVIDENCE, LEGAL_AUTHORITY, BOTH, GENERAL_INFORMATION)
2. 5-Factor Context & Missing Fact Identification (jurisdiction, document context, dates, domain, missing facts)
3. Multi-stream Evidence Retrieval (User Document + Statutory Registry)
4. 8-Part Structured Answer Synthesis:
   - Plain-language answer
   - What the uploaded document says
   - Applicable legal information/source
   - Evidence (verbatim quotes with page numbers & URLs)
   - Important uncertainty & limitations
   - Potential next steps
   - Questions for a professional
   - Legal disclaimer
5. Epistemic Humility Enforcement (suppress outcome guarantees; prefer "Based on available information...")
6. English & Hindi Localization Architecture (without reasoning from translated law)
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional

from app.core.exceptions import PromptInjectionDetected
from app.core.prompt_security import prompt_security_manager
from app.schemas.qa import (
    CitationItem,
    QAContextMetadata,
    QAEvidenceItem,
    QARequest,
    QAResponse,
    QuestionRequirementType,
    StructuredAnswerSections,
)
from app.schemas.retrieval import EvidenceType, RetrievalFilter, RetrievalResponse
from app.services.qa_engine.classifier import qa_classifier
from app.services.qa_engine.hedging import qa_hedging_gate
from app.services.qa_engine.localizer import qa_localizer
from app.services.retrieval.retriever import legal_retriever

LEGAL_DISCLAIMER_TEXT = (
    "Nyaya Rakshak is an AI-powered legal clarity and educational assistance platform. "
    "It does NOT provide formal legal advice, does NOT constitute an attorney-client relationship, "
    "and cannot guarantee legal outcomes. Consult a qualified advocate for official representation."
)


class LegalQAEngine:
    """Enterprise Legal Q&A Orchestrator."""

    def __init__(
        self,
        classifier=None,
        retriever=None,
        hedging_gate=None,
        localizer=None
    ):
        self.classifier = classifier or qa_classifier
        self.retriever = retriever or legal_retriever
        self.hedging_gate = hedging_gate or qa_hedging_gate
        self.localizer = localizer or qa_localizer

    async def answer_legal_question(
        self,
        req: QARequest,
        document_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> QAResponse:
        """
        Executes the end-to-end evidence-first legal Q&A pipeline.
        """
        # 1. Prompt Injection Defense
        is_inj, pattern = prompt_security_manager.inspect_text_for_injection(req.question)
        if is_inj:
            raise PromptInjectionDetected(f"Security Alert: Suspicious prompt pattern detected in question: '{pattern}'")

        # 2. Classify Question Requirement & Identify Context
        req_type, context_meta = self.classifier.classify_and_extract_context(
            question=req.question,
            document_chunks=document_chunks,
            explicit_jurisdiction=req.jurisdiction
        )

        # 3. Evidence-First Retrieval
        retrieval_filters = RetrievalFilter(
            jurisdiction=context_meta.jurisdiction,
            legal_domain=context_meta.legal_domain if context_meta.legal_domain != "general" else None,
        )

        retrieval_res: RetrievalResponse = await self.retriever.retrieve(
            query=req.question,
            document_chunks=document_chunks,
            custom_filters=retrieval_filters,
            top_k=5
        )

        user_doc_items = retrieval_res.user_document_items
        legal_authority_items = retrieval_res.legal_authority_items

        # 4. Synthesize 8-Part Structured Sections
        sections, is_found, conf_score = self._synthesize_sections(
            question=req.question,
            req_type=req_type,
            context_meta=context_meta,
            user_doc_items=user_doc_items,
            legal_authority_items=legal_authority_items,
            has_uploaded_doc=bool(document_chunks and len(document_chunks) > 0)
        )

        # 5. Enforce Epistemic Hedging & Suppress Outcome Guarantees
        hedged_plain, _ = self.hedging_gate.enforce_hedging(sections.plain_language_answer)
        sections.plain_language_answer = hedged_plain

        hedged_doc, _ = self.hedging_gate.enforce_hedging(sections.what_the_document_says)
        sections.what_the_document_says = hedged_doc

        # 6. Build Legacy Citations for backward compatibility
        legacy_citations = []
        for doc_item in user_doc_items:
            legacy_citations.append(CitationItem(
                page_number=doc_item.citation.provenance.get("page", 1),
                section_title=doc_item.title,
                verbatim_quote=doc_item.citation.supporting_text,
                relevance_score=round(doc_item.final_score, 2)
            ))

        # 7. Localization (English or Hindi)
        target_lang = req.language.lower() if req.language else "en"
        localized_data = None
        if target_lang == "hi":
            localized_data = self.localizer.localize_sections(sections, target_language="hi")

        # 8. Assemble Formatted Markdown Answer
        formatted_answer = self._format_markdown_answer(sections, target_lang=target_lang, localized_data=localized_data)

        return QAResponse(
            question=req.question,
            answer=formatted_answer,
            confidence_score=conf_score,
            citations=legacy_citations,
            is_found_in_document=is_found,
            requirement_type=req_type,
            identified_context=context_meta,
            structured_sections=sections,
            language=target_lang,
            localized_sections=localized_data
        )

    def _synthesize_sections(
        self,
        question: str,
        req_type: QuestionRequirementType,
        context_meta: QAContextMetadata,
        user_doc_items: List[Any],
        legal_authority_items: List[Any],
        has_uploaded_doc: bool
    ) -> Tuple[StructuredAnswerSections, bool, float]:
        evidence_list: List[QAEvidenceItem] = []
        is_found_in_doc = False
        conf_score = 0.0

        # Section 2: What the uploaded document says
        if has_uploaded_doc:
            if user_doc_items and user_doc_items[0].final_score >= 0.25:
                is_found_in_doc = True
                top_doc = user_doc_items[0]
                conf_score = max(conf_score, top_doc.final_score)
                what_doc_says = f"Clause excerpt: \"{top_doc.content.strip()}\""
                evidence_list.append(QAEvidenceItem(
                    source_title=top_doc.title,
                    citation_ref=top_doc.citation.section_or_page,
                    page_number=top_doc.citation.provenance.get("page", 1),
                    section_or_clause=top_doc.title,
                    verbatim_quote=top_doc.content.strip()[:300],
                    relevance_score=round(top_doc.final_score, 2),
                    provenance_url=top_doc.citation.url_or_reference
                ))
            else:
                what_doc_says = "I could not verify this from the available sources in the uploaded document. The document text does not contain explicit provisions addressing this specific query."
        else:
            what_doc_says = "No uploaded document was provided for this question. The analysis is conducted based on general Indian legal authority."

        # Section 3: Applicable legal information / source
        if legal_authority_items:
            top_auth = legal_authority_items[0]
            conf_score = max(conf_score, 0.85)
            applicable_law = (
                f"Under {top_auth.title} ({top_auth.citation.authority}), "
                f"the law stipulates that {top_auth.content.strip()} "
                f"Key principles: {'; '.join(top_auth.citation.provenance.get('key_principles', [])) or 'Statutory mandate enforced by Indian courts.'}"
            )
            evidence_list.append(QAEvidenceItem(
                source_title=top_auth.title,
                citation_ref=top_auth.citation.section_or_page or top_auth.title,
                page_number=None,
                section_or_clause=top_auth.citation.section_or_page,
                verbatim_quote=top_auth.content.strip()[:300],
                relevance_score=0.90,
                provenance_url=top_auth.citation.url_or_reference
            ))
        else:
            applicable_law = "No specific statutory provision or Supreme Court ruling directly matching these parameters was retrieved from the canonical registry."

        # Section 1: Plain language answer
        if has_uploaded_doc and not is_found_in_doc:
            plain_answer = "I could not verify this from the available sources in the uploaded document."
            conf_score = 0.0
        elif is_found_in_doc and legal_authority_items:
            plain_answer = (
                f"Based on the available information, your document contains provisions regarding this subject, "
                f"which should be evaluated against governing Indian law ({legal_authority_items[0].title})."
            )
        elif is_found_in_doc and user_doc_items:
            plain_answer = f"Based on the available information in your document, the text specifies: {user_doc_items[0].content.strip()[:180]}."
        elif legal_authority_items:
            plain_answer = f"Based on the available information under Indian law, {legal_authority_items[0].content.strip()[:180]}."
        else:
            plain_answer = "Based on the available information, authoritative confirmation could not be verified from the retrieved records."

        # Section 5: Important uncertainty & missing facts
        uncertainty_parts = []
        if context_meta.missing_facts:
            uncertainty_parts.append("Important factual limitations to note:")
            for mf in context_meta.missing_facts:
                uncertainty_parts.append(f"- {mf}")
        uncertainty_parts.append("- Judicial determination: Contractual terms may be interpreted differently depending on specific evidentiary context and regional High Court rulings.")
        important_uncertainty = "\n".join(uncertainty_parts)

        # Section 6: Potential next steps
        potential_next_steps = [
            "Review the exact written notices and correspondence exchanged between parties.",
            "Maintain dated receipts, payment logs, and email records.",
            "If in dispute, avoid unilateral verbal agreements; preserve all communications in writing.",
            "If eligible under NALSA guidelines, seek assistance from your District Legal Services Authority (DLSA)."
        ]

        # Section 7: Questions for a professional
        questions_for_professional = [
            f"How does the High Court with jurisdiction over {context_meta.jurisdiction} interpret this specific clause?",
            "What statutory protections or exemptions apply given the specific factual dates of this transaction?",
            "What formal written legal notice should be issued prior to any dispute resolution or tribunal filing?"
        ]

        sections = StructuredAnswerSections(
            plain_language_answer=plain_answer,
            what_the_document_says=what_doc_says,
            applicable_legal_information=applicable_law,
            evidence=evidence_list,
            important_uncertainty=important_uncertainty,
            potential_next_steps=potential_next_steps,
            questions_for_professional=questions_for_professional,
            legal_disclaimer=LEGAL_DISCLAIMER_TEXT
        )

        return sections, is_found_in_doc, round(conf_score, 2)

    def _format_markdown_answer(
        self,
        sections: StructuredAnswerSections,
        target_lang: str = "en",
        localized_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Assembles the full structured markdown answer."""
        if target_lang == "hi" and localized_data:
            s = localized_data
            steps = "\n".join([f"- {step}" for step in s.get("potential_next_steps", [])])
            questions = "\n".join([f"- {q}" for q in s.get("questions_for_professional", [])])
            return (
                f"### 📋 सादा भाषा में कानूनी सारांश\n{s.get('plain_language_answer')}\n\n"
                f"### 📄 आपके अपलोड किए गए दस्तावेज़ में क्या लिखा है\n{s.get('what_the_document_says')}\n\n"
                f"### ⚖️ लागू कानूनी जानकारी व स्रोत\n{s.get('applicable_legal_information')}\n\n"
                f"### 🔍 महत्वपूर्ण अनिश्चितताएं एवं आवश्यक तथ्य\n{s.get('important_uncertainty')}\n\n"
                f"### 💡 नागरिक के लिए संभावित अगले कदम\n{steps}\n\n"
                f"### ❓ वकील या विशेषज्ञ से पूछने हेतु प्रश्न\n{questions}\n\n"
                f"---\n*{s.get('legal_disclaimer')}*"
            )

        steps = "\n".join([f"- {step}" for step in sections.potential_next_steps])
        questions = "\n".join([f"- {q}" for q in sections.questions_for_professional])

        return (
            f"### 📋 Plain-Language Answer\n{sections.plain_language_answer}\n\n"
            f"### 📄 What the Uploaded Document Says\n{sections.what_the_document_says}\n\n"
            f"### ⚖️ Applicable Legal Information / Source\n{sections.applicable_legal_information}\n\n"
            f"### 🔍 Important Uncertainty & Missing Facts\n{sections.important_uncertainty}\n\n"
            f"### 💡 Potential Next Steps\n{steps}\n\n"
            f"### ❓ Questions for a Professional\n{questions}\n\n"
            f"---\n*{sections.legal_disclaimer}*"
        )


qa_engine = LegalQAEngine()

"""
NYAYA RAKSHAK - Claim Verification Subsystem & Safety Gate Orchestrator
Implements the 8-stage evidence-first verification pipeline:
USER QUESTION
  → RETRIEVAL
  → DRAFT ANSWER
  → CLAIM EXTRACTION
  → EVIDENCE MATCHING
  → VERIFICATION (6 Checks)
  → SAFETY GATE
  → FINAL RESPONSE
"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from app.schemas.retrieval import (
    EvidenceType,
    RetrievalFilter,
    RetrievalResponse,
    RetrievalResultItem,
)
from app.schemas.verification import (
    ClaimVerificationCheck,
    ClaimVerificationDetail,
    ClaimVerificationPipelineRequest,
    ClaimVerificationPipelineResponse,
    VerificationMetrics,
    VerificationStatus,
)
from app.services.claim_verification.claim_extractor import ExtractedClaim, claim_extractor
from app.services.claim_verification.metrics import verification_metrics_calculator
from app.services.claim_verification.safety_gate import safety_gate
from app.services.retrieval.registry import source_registry
from app.services.retrieval.retriever import legal_retriever


class ClaimVerificationEngine:
    """Enterprise 8-Stage Claim Verification and Response Hardening Engine."""

    def __init__(self, retriever=None, extractor=None, metrics_calc=None, gate=None):
        self.retriever = retriever or legal_retriever
        self.extractor = extractor or claim_extractor
        self.metrics_calc = metrics_calc or verification_metrics_calculator
        self.gate = gate or safety_gate

    async def execute_pipeline(
        self, req: ClaimVerificationPipelineRequest
    ) -> ClaimVerificationPipelineResponse:
        """Runs the complete 8-stage pipeline."""
        # STAGE 1 & 2: USER QUESTION → RETRIEVAL
        custom_filters = None
        if req.jurisdiction or req.as_of_date:
            custom_filters = RetrievalFilter(
                jurisdiction=req.jurisdiction, as_of_date=req.as_of_date
            )

        retrieval_res: RetrievalResponse = await self.retriever.retrieve(
            query=req.user_question,
            document_chunks=req.document_chunks,
            custom_filters=custom_filters,
            top_k=8,
        )

        # STAGE 3: DRAFT ANSWER
        draft_answer = req.draft_answer
        if not draft_answer:
            draft_answer = self._synthesize_draft_answer(req.user_question, retrieval_res)

        # STAGE 4: CLAIM EXTRACTION
        extracted_claims: List[ExtractedClaim] = self.extractor.extract_claims(draft_answer)

        # STAGE 5 & 6: EVIDENCE MATCHING & 6-CHECK VERIFICATION
        verified_details: List[ClaimVerificationDetail] = []
        verified_citations: List[str] = []
        rejected_citations: List[str] = []

        all_evidence_items: List[RetrievalResultItem] = retrieval_res.reranked_items

        for claim in extracted_claims:
            detail, v_cites, r_cites = self._verify_single_claim(
                claim=claim,
                all_evidence=all_evidence_items,
                query_jurisdiction=retrieval_res.applied_filters.jurisdiction or "Union of India",
                as_of_date=retrieval_res.applied_filters.as_of_date,
            )
            verified_details.append(detail)
            verified_citations.extend(v_cites)
            rejected_citations.extend(r_cites)

        # Remove citation duplicates
        verified_citations = list(dict.fromkeys(verified_citations))
        rejected_citations = list(dict.fromkeys(rejected_citations))

        # METRICS CALCULATION
        metrics: VerificationMetrics = self.metrics_calc.compute_metrics(
            claims=verified_details,
            verified_citations=verified_citations,
            rejected_citations=rejected_citations,
        )

        # STAGE 7: SAFETY GATE
        final_response, safety_gate_action, compliance = self.gate.gate_and_finalize(
            draft_answer=draft_answer, claims=verified_details
        )

        # STAGE 8: FINAL RESPONSE
        return ClaimVerificationPipelineResponse(
            user_question=req.user_question,
            draft_answer=draft_answer,
            final_response=final_response,
            safety_gate_action=safety_gate_action,
            claims=verified_details,
            metrics=metrics,
            citations_verified=verified_citations,
            citations_rejected=rejected_citations,
            never_hallucination_free_compliance=compliance,
        )

    def _verify_single_claim(
        self,
        claim: ExtractedClaim,
        all_evidence: List[RetrievalResultItem],
        query_jurisdiction: str,
        as_of_date: Optional[datetime],
    ) -> Tuple[ClaimVerificationDetail, List[str], List[str]]:
        """
        Executes the 6-Check Verification on a single claim:
        1. Identify candidate evidence
        2. Compare claim with evidence (token & semantic overlap)
        3. Check source authority (tier/status)
        4. Check jurisdiction match
        5. Check date/version temporal validity
        6. Determine support status
        """
        v_cites = []
        r_cites = []

        best_match: Optional[RetrievalResultItem] = None
        best_score = 0.0
        claim_lower = claim.claim_text.lower()

        # Check 1: Candidate evidence identification
        c_words = set(re.findall(r"\w+", claim_lower)) - {
            "the",
            "and",
            "under",
            "for",
            "that",
            "this",
            "with",
        }

        for ev in all_evidence:
            ev_text_lower = f"{ev.title} {ev.content}".lower()
            ev_words = set(re.findall(r"\w+", ev_text_lower))
            overlap = len(c_words.intersection(ev_words)) / max(1, len(c_words))

            # Bonus for exact citation match
            for cite in claim.cited_references:
                if cite.lower() in ev_text_lower:
                    overlap += 0.4

            if overlap > best_score:
                best_score = overlap
                best_match = ev

        check_1_found = best_match is not None and best_score >= 0.25

        # Check 2: Comparison of claim vs evidence text
        comparison_reason = ""
        is_conflicting = False
        if check_1_found and best_match:
            # Check for direct contradictions (e.g. claim says 'non-refundable' but statute says 'must be refunded')
            if ("non-refundable" in claim_lower or "forfeit" in claim_lower) and (
                "refund" in best_match.content.lower()
                or "deposit shall be refunded" in best_match.content.lower()
            ):
                is_conflicting = True
                comparison_reason = "Direct conflict: Claim stipulates forfeiture or non-refundability, but governing legal authority mandates deposit refund."
            elif ("unilateral" in claim_lower or "at sole discretion" in claim_lower) and (
                "unfair contract" in best_match.content.lower()
                or "not have the power" in best_match.content.lower()
            ):
                is_conflicting = True
                comparison_reason = "Direct conflict: Claim asserts unilateral prerogative, but statutory authority classifies unilateral terms as unfair."
            elif best_score >= 0.5:
                comparison_reason = f"Substantial semantic and textual alignment ({best_score:.2f}) with {best_match.title}."
            else:
                comparison_reason = f"Partial overlap ({best_score:.2f}) with {best_match.title}."
        else:
            comparison_reason = (
                "No authoritative documentary or statutory evidence matches this claim."
            )

        # Check 3: Source authority check
        source_authority_desc = "None"
        if check_1_found and best_match:
            source_authority_desc = f"{best_match.tier.value} ({best_match.citation.authority})"

        # Check 4: Jurisdiction match check
        jurisdiction_match = True
        if query_jurisdiction != "Union of India":
            # Check if claim text itself references a conflicting state
            for state_name in [
                "maharashtra",
                "delhi",
                "karnataka",
                "tamil nadu",
                "west bengal",
                "gujarat",
            ]:
                if state_name in claim_lower and state_name not in query_jurisdiction.lower():
                    jurisdiction_match = False
                    comparison_reason += f" [JURISDICTION MISMATCH: Claim refers to {state_name.title()} while query applies to {query_jurisdiction}]."
            # Check if matched evidence source is from a conflicting state
            if check_1_found and best_match:
                if (
                    best_match.jurisdiction != "Union of India"
                    and best_match.jurisdiction != query_jurisdiction
                ):
                    jurisdiction_match = False
                    comparison_reason += f" [JURISDICTION MISMATCH: Source is {best_match.jurisdiction} but query applies to {query_jurisdiction}]."

        # Check 5: Temporal validity check
        temporal_valid = True
        if as_of_date:
            # Check if claim cites repealed statutes (e.g. IPC after July 1, 2024)
            if "ipc" in claim_lower or "indian penal code" in claim_lower or "420" in claim_lower:
                ipc_item = source_registry.get("IPC-1860-SEC-420")
                if ipc_item and not ipc_item.is_valid_as_of(as_of_date):
                    temporal_valid = False
                    comparison_reason += f" [TEMPORAL MISMATCH: Claim cites Indian Penal Code, which was repealed and replaced by BNS on July 1, 2024. Not valid as of {as_of_date.date()}]."
            elif check_1_found and best_match:
                reg_item = source_registry.get(best_match.item_id)
                if reg_item and not reg_item.is_valid_as_of(as_of_date):
                    temporal_valid = False
                    comparison_reason += f" [TEMPORAL MISMATCH: Source {best_match.item_id} was not active as of {as_of_date.date()}]."

        # Fabricated citation inspection (check cited references against registry & evidence)
        for ref in claim.cited_references:
            is_valid = self._check_citation_validity(ref, source_registry.list_all(), all_evidence)
            if is_valid:
                v_cites.append(ref)
            else:
                # Potential fabricated or unverified case/statute/clause!
                ref_lower = ref.lower()
                if any(
                    k in ref_lower
                    for k in ["v.", "vs.", "act", "sanhita", "code", "section", "scc"]
                ):
                    r_cites.append(ref)

        # Check 6: Support status determination
        if is_conflicting:
            status = VerificationStatus.CONFLICTING
            conf_score = round(min(1.0, best_score), 2)
        elif not check_1_found or not jurisdiction_match or not temporal_valid or len(r_cites) > 0:
            status = VerificationStatus.UNSUPPORTED
            conf_score = 0.1
        elif best_score >= 0.5:
            status = VerificationStatus.SUPPORTED
            conf_score = round(min(1.0, best_score), 2)
        else:
            status = VerificationStatus.PARTIALLY_SUPPORTED
            conf_score = round(min(1.0, best_score), 2)

        check_obj = ClaimVerificationCheck(
            check_1_evidence_found=check_1_found,
            check_2_claim_evidence_comparison=comparison_reason,
            check_3_source_authority=source_authority_desc,
            check_4_jurisdiction_match=jurisdiction_match,
            check_5_temporal_validity=temporal_valid,
            check_6_status_determined=status,
        )

        detail = ClaimVerificationDetail(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            verification_status=status,
            checks=check_obj,
            matched_evidence_id=best_match.item_id if best_match else None,
            matched_evidence_snippet=best_match.content[:200].strip() if best_match else None,
            matched_source_url=best_match.citation.url_or_reference if best_match else None,
            confidence_score=conf_score,
            explanation=comparison_reason,
        )

        return detail, v_cites, r_cites

    def _check_citation_validity(self, ref: str, source_list, evidence_list) -> bool:
        """Validates whether a cited statute, case, or clause exists in the official registry or document."""
        ref_lower = ref.lower().strip()

        # 1. Check against registered statutory sources
        for s in source_list:
            s_title_lower = s.title.lower()
            s_short_lower = s.short_name.lower()
            s_code_lower = s.code.lower()
            s_sec_lower = s.section_number.lower()

            # Check if case precedent
            if "percept" in ref_lower and "percept" in s_code_lower:
                return True
            if "perkins" in ref_lower and "perkins" in s_code_lower:
                return True

            # Match statute by name / abbreviation
            title_matches = (
                s_title_lower in ref_lower
                or s_short_lower in ref_lower
                or s_code_lower in ref_lower
                or ("bns" in ref_lower and "bns" in s_code_lower)
                or ("bharatiya nyaya sanhita" in ref_lower and "bns" in s_code_lower)
                or ("ipc" in ref_lower and "ipc" in s_code_lower)
                or ("indian penal code" in ref_lower and "ipc" in s_code_lower)
                or ("contract act" in ref_lower and "ica" in s_code_lower)
                or ("consumer protection" in ref_lower and "cpa" in s_code_lower)
                or ("model tenancy" in ref_lower and "mta" in s_code_lower)
                or ("delhi rent" in ref_lower and "drca" in s_code_lower)
                or ("maharashtra rent" in ref_lower and "mrca" in s_code_lower)
                or ("dpdp" in ref_lower and "dpdp" in s_code_lower)
            )

            # Match section if specified
            sec_matches = True
            if "section" in ref_lower or "sec" in ref_lower:
                sec_num = s.section_number.replace("Section", "").strip().lower()
                sec_matches = sec_num in ref_lower or s_sec_lower in ref_lower

            if title_matches and sec_matches:
                return True

        # 2. Check against user document chunks
        for ev in evidence_list:
            if ev.evidence_type == EvidenceType.USER_DOCUMENT_EVIDENCE:
                if "clause" in ref_lower or "paragraph" in ref_lower:
                    m = re.search(r"(?:clause|paragraph)\s+(\d+(?:\.\d+)?)", ref_lower)
                    if m and m.group(0) in ev.content.lower():
                        return True

        return False

    def _synthesize_draft_answer(self, query: str, retrieval_res: RetrievalResponse) -> str:
        """Synthesizes a simple draft answer from retrieved items when no draft is provided."""
        if not retrieval_res.reranked_items:
            return f"Regarding '{query}', no matching legal authorities were retrieved."

        top = retrieval_res.reranked_items[0]
        return f"Under {top.title}, the governing rule provides that {top.content}"


claim_verification_engine = ClaimVerificationEngine()

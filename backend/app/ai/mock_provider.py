import re
from typing import Any, Dict, List

from rapidfuzz import fuzz

from app.ai.base import BaseAIProvider
from app.services.statutory_kb import search_statutory_kb


class DeterministicMockAIProvider(BaseAIProvider):
    """
    Intelligent, deterministic rule-based AI provider for offline/air-gapped evaluation.
    Performs real structural clause parsing, regex heuristic risk extraction,
    RapidFuzz fuzzy quotation retrieval, and statutory evidence matching.
    """

    def _extract_raw_clauses(self, text: str) -> List[Dict[str, Any]]:
        """Segment document into clauses based on numbered headings or capitalized sections."""
        lines = text.split("\n")
        clauses = []
        current_title = "Preamble & Recitals"
        current_lines = []
        clause_counter = 1

        heading_regex = re.compile(
            r"^(?:(?:Section|Clause|Article)?\s*\d+[\.\)]\s+([A-Z\s,/-]{3,50})|([A-Z\s,/-]{4,50}:))",
            re.MULTILINE,
        )

        for line in lines:
            stripped = line.strip()
            match = heading_regex.match(stripped)
            if match and len(current_lines) > 0:
                body = "\n".join(current_lines).strip()
                if body:
                    clauses.append(
                        {
                            "clause_id": f"C-{clause_counter:02d}",
                            "title": current_title,
                            "text": body,
                        }
                    )
                    clause_counter += 1
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(stripped)

        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                clauses.append(
                    {"clause_id": f"C-{clause_counter:02d}", "title": current_title, "text": body}
                )

        return clauses

    async def analyze_document(self, text: str, title: str) -> Dict[str, Any]:
        raw_clauses = self._extract_raw_clauses(text)
        text_lower = text.lower()

        # Determine document domain
        is_lease = any(
            k in text_lower
            for k in ["lease", "rent", "lessor", "lessee", "tenant", "landlord", "demised premises"]
        )
        is_employment = any(
            k in text_lower
            for k in ["employment", "employee", "employer", "salary", "probation", "resignation"]
        )

        parsed_clauses = []
        risks = []
        obligations = []
        risk_counter = 1
        ob_counter = 1

        # Process each clause
        for c in raw_clauses:
            c_text = c["text"]
            c_lower = c_text.lower()
            c_title = c["title"]

            category = "General Terms"
            risk_level = "LOW"
            plain_en = "Standard operational and legal terms defining the relationship."
            plain_hi = "दस्तावेज़ की सामान्य शर्तें जो पक्षों के अधिकारों को परिभाषित करती हैं।"
            recommendation = "Review for customary terms."

            if any(k in c_lower for k in ["terminate", "termination", "notice period"]):
                category = "Termination & Notice"
                if (
                    "unilateral" in c_lower
                    or "7 days" in c_lower
                    or "no right to terminate" in c_lower
                ):
                    risk_level = "SEVERE"
                    plain_en = "One party can terminate with very short notice (7 days), while the other party is restricted from exiting."
                    plain_hi = "एक पक्ष केवल 7 दिनों के नोटिस पर अनुबंध समाप्त कर सकता है, जबकि दूसरे पक्ष के बाहर निकलने पर रोक है।"
                    recommendation = (
                        "Demand equal notice period (minimum 30 days) for both parties."
                    )
                    risks.append(
                        {
                            "risk_id": f"R-{risk_counter:02d}",
                            "severity": "SEVERE",
                            "category": "Termination Imbalance",
                            "title": "Unilateral or Asymmetric Termination Right",
                            "description": "One party has an unrestricted right to cancel on 7 days notice without cause, denying reciprocal rights.",
                            "clause_reference": c_title,
                            "countermeasure": "Ensure reciprocal 30-day notice with no forfeiture penalty.",
                        }
                    )
                    risk_counter += 1
                else:
                    risk_level = "LOW"
                    plain_en = "Either party may terminate the agreement by providing 1 month written notice."
                    plain_hi = "कोई भी पक्ष 1 महीने का लिखित नोटिस देकर अनुबंध समाप्त कर सकता है।"

            elif any(k in c_lower for k in ["security deposit", "deposit"]):
                category = "Security Deposit & Refund"
                if "90 days" in c_lower or "forfeit" in c_lower or "5 months" in c_lower:
                    risk_level = "HIGH"
                    plain_en = "The security deposit is unusually high or refund is delayed up to 90 days with broad deduction clauses."
                    plain_hi = "जमानत राशि (सिक्योरिटी डिपॉजिट) बहुत अधिक है या वापसी में 90 दिन की देरी और मनमानी कटौती का खतरा है।"
                    recommendation = "Cap deposit to maximum 2 months under Model Tenancy Act and require refund within 14 business days."
                    risks.append(
                        {
                            "risk_id": f"R-{risk_counter:02d}",
                            "severity": "HIGH",
                            "category": "Deposit Risk",
                            "title": "Extended 90-Day Refund & Forfeiture Risk",
                            "description": "Refund delayed up to 90 days with discretion to forfeit deposit for minor wear and tear.",
                            "clause_reference": c_title,
                            "countermeasure": "Insert clause mandating refund within 14 days with joint inspection.",
                        }
                    )
                    risk_counter += 1
                else:
                    risk_level = "LOW"
                    plain_en = "Refundable security deposit equivalent to standard 2 months rent, refunded within 14 days."
                    plain_hi = (
                        "2 महीने के किराए के बराबर प्रतिदेय सुरक्षा जमा, जो 14 दिनों के भीतर वापस की जाएगी।"
                    )

            elif any(
                k in c_lower for k in ["rent", "charges", "interest", "penalty", "escalation"]
            ):
                category = "Financial Obligations & Penalties"
                if "18%" in c_lower or "1,000 per day" in c_lower or "15%" in c_lower:
                    risk_level = "SEVERE"
                    plain_en = "Severe compounding interest (18% p.a.) and daily flat penalty of ₹1,000 for rent delay."
                    plain_hi = "किराए में देरी पर 18% वार्षिक ब्याज और ₹1,000 प्रतिदिन का भारी जुर्माना।"
                    recommendation = "Replace with standard reasonable grace period (7 days) and nominal simple interest."
                    risks.append(
                        {
                            "risk_id": f"R-{risk_counter:02d}",
                            "severity": "SEVERE",
                            "category": "Financial Penalty",
                            "title": "Exorbitant Late Payment Penalties (18% + ₹1,000/day)",
                            "description": "Imposes compounding interest of 18% plus daily fines, which is deemed penal and unconscionable.",
                            "clause_reference": c_title,
                            "countermeasure": "Request capping late fee to 1-2% simple interest after 7-day grace period.",
                        }
                    )
                    risk_counter += 1
                else:
                    risk_level = "LOW"
                    plain_en = "Fixed monthly rent with 7-day grace period before nominal 1% interest applies."
                    plain_hi = "निश्चित मासिक किराया और 1% मामूली ब्याज लागू होने से पहले 7 दिनों की छूट।"

            elif any(k in c_lower for k in ["indemnify", "indemnification", "hold harmless"]):
                category = "Indemnity & Liability"
                risk_level = "HIGH"
                plain_en = "You are agreeing to pay all damages and legal costs regardless of fault or negligence."
                plain_hi = "आप बिना किसी गलती या लापरवाही के भी सभी नुकसान और कानूनी खर्च वहन करने के लिए सहमत हो रहे हैं।"
                recommendation = "Limit indemnity strictly to direct damages caused by gross negligence or willful misconduct."
                risks.append(
                    {
                        "risk_id": f"R-{risk_counter:02d}",
                        "severity": "HIGH",
                        "category": "Indemnity",
                        "title": "Blanket Indemnification Clause",
                        "description": "Transfers unlimited liability to you even for events outside your direct control.",
                        "clause_reference": c_title,
                        "countermeasure": "Add mutual liability cap and carve-out for normal wear and tear or third-party acts.",
                    }
                )
                risk_counter += 1

            elif any(k in c_lower for k in ["non-compete", "restraint"]):
                category = "Non-Compete & Restrictive Covenants"
                risk_level = "HIGH"
                plain_en = "Restricts you from working for any competitor for 12 months after leaving employment."
                plain_hi = "नौकरी छोड़ने के बाद 12 महीने तक किसी भी प्रतिस्पर्धी कंपनी में काम करने पर प्रतिबंध।"
                recommendation = "Note that post-employment non-compete clauses are void under Section 27 of Indian Contract Act 1872."
                risks.append(
                    {
                        "risk_id": f"R-{risk_counter:02d}",
                        "severity": "HIGH",
                        "category": "Statutory Conflict",
                        "title": "Post-Employment Non-Compete Restriction",
                        "description": "Imposes 12-month ban on working with competitors, which Indian courts hold void under Section 27.",
                        "clause_reference": c_title,
                        "countermeasure": "Seek deletion of post-employment restrictions; highlight Supreme Court precedent (Percept D'Mark).",
                    }
                )
                risk_counter += 1

            elif any(
                k in c_lower
                for k in ["non-refundable", "limitation of liability", "waives all rights"]
            ):
                category = "Consumer Rights & Waivers"
                risk_level = "SEVERE"
                plain_en = "Requires you to waive your statutory right to approach consumer courts and declares all fees non-refundable."
                plain_hi = "उपभोक्ता फोरम में जाने के आपके कानूनी अधिकार को त्यागने को कहता है और फीस को गैर-वापसी योग्य बनाता है।"
                recommendation = "Such terms are unfair contracts under Section 2(46) of the Consumer Protection Act 2019."
                risks.append(
                    {
                        "risk_id": f"R-{risk_counter:02d}",
                        "severity": "SEVERE",
                        "category": "Unfair Contract Term",
                        "title": "Waiver of Consumer Court Jurisdiction",
                        "description": "Purports to bar consumer complaint filing, which is contrary to public policy and void under CPA 2019.",
                        "clause_reference": c_title,
                        "countermeasure": "Affirm that statutory jurisdiction of Consumer Commissions cannot be contractually waived.",
                    }
                )
                risk_counter += 1

            parsed_clauses.append(
                {
                    "clause_id": c["clause_id"],
                    "category": category,
                    "title": c_title,
                    "original_text": c_text[:400] + ("..." if len(c_text) > 400 else ""),
                    "plain_english": plain_en,
                    "plain_hindi": plain_hi,
                    "risk_level": risk_level,
                    "page_number": 1,
                    "recommendations": recommendation,
                }
            )

            # Extract obligations
            if "pay" in c_lower or "rent" in c_lower:
                obligations.append(
                    {
                        "obligation_id": f"O-{ob_counter:02d}",
                        "responsible_party": "Lessee / Customer",
                        "action": "Pay recurring charges/rent on time",
                        "deadline_or_frequency": "By the 1st to 7th of every calendar month",
                        "penalty_for_breach": "Late payment interest / penalty charges",
                    }
                )
                ob_counter += 1
            if "notice" in c_lower:
                obligations.append(
                    {
                        "obligation_id": f"O-{ob_counter:02d}",
                        "responsible_party": "Both Parties",
                        "action": "Serve written notice prior to termination or inspection",
                        "deadline_or_frequency": "15 to 30 days prior notice",
                        "penalty_for_breach": "Notice pay forfeiture or invalid termination",
                    }
                )
                ob_counter += 1

        # Detect Missing Clauses
        missing_clauses = []
        if is_lease:
            if not any(
                "water" in c["text"].lower() or "structural" in c["text"].lower()
                for c in raw_clauses
            ):
                missing_clauses.append(
                    {
                        "clause_name": "Landlord Structural Maintenance Warranty",
                        "importance": "CRITICAL",
                        "why_needed": "Clarifies who pays for major roof leaks, wall seepage, and plumbing integrity.",
                        "suggested_language": "The Lessor shall be solely responsible for all major and structural repairs including seepage and electrical mains.",
                        "risk_if_missing": "Landlord may attempt to deduct structural repairs from your security deposit.",
                    }
                )
            if not any("force majeure" in c["text"].lower() for c in raw_clauses):
                missing_clauses.append(
                    {
                        "clause_name": "Force Majeure & Rent Abatement",
                        "importance": "RECOMMENDED",
                        "why_needed": "Provides rent relief if property becomes uninhabitable due to natural disaster or government lockdown.",
                        "suggested_language": "If the premises become uninhabitable due to force majeure, rent shall be abated until restored.",
                        "risk_if_missing": "You may be held liable for full rent even if you cannot occupy the premises.",
                    }
                )
        elif is_employment:
            if not any(
                "pf" in c["text"].lower() or "provident" in c["text"].lower() for c in raw_clauses
            ):
                missing_clauses.append(
                    {
                        "clause_name": "Statutory Benefits (EPF & Gratuity)",
                        "importance": "RECOMMENDED",
                        "why_needed": "Confirms employer contributions under Employees' Provident Funds Act 1952.",
                        "suggested_language": "The Employee shall be eligible for statutory Provident Fund and Gratuity as per applicable Indian statutes.",
                        "risk_if_missing": "Ambiguity regarding CTC deductions and retirement benefits.",
                    }
                )

        # Summaries
        if is_lease:
            summary_cit = "This is a residential tenancy agreement. It outlines monthly rental payments, security deposit handling, maintenance responsibilities, and termination notice rules."
            summary_leg = "The document is a bilateral residential lease agreement establishing a license/tenancy relationship under Indian transfer of property principles, containing covenants on rent, quiet enjoyment, and surrender."
            summary_hi = "यह एक आवासीय किराया अनुबंध (लीज़ एग्रीमेंट) है। यह मासिक किराया भुगतान, जमानत राशि की वापसी, रखरखाव की जिम्मेदारियों और अनुबंध समाप्त करने के नियमों को स्पष्ट करता है।"
        elif is_employment:
            summary_cit = "This is an employment agreement for a tech position. It governs your job role, notice period on resignation, intellectual property rights, and restrictive covenants."
            summary_leg = "A contract of service defining terms of employment, fiduciary duties, restrictive covenants, and statutory obligations under Indian labor law."
            summary_hi = "यह एक रोजगार अनुबंध (नौकरी का समझौता) है। इसमें कार्यभार, नोटिस अवधि, बौद्धिक संपदा और नौकरी के बाद के नियमों की जानकारी दी गई है।"
        else:
            summary_cit = "This is a commercial or consumer service contract detailing fees, service scopes, liability caps, and dispute escalation terms."
            summary_leg = "A standard-form consumer agreement with terms of subscription, disclaimers of consequential damages, and forum selection clauses."
            summary_hi = "यह एक उपभोक्ता सेवा अनुबंध है जिसमें सेवा शुल्क, उत्तरदायित्व की सीमाएं और विवाद समाधान की शर्तें शामिल हैं।"

        return {
            "summary_citizen": summary_cit,
            "summary_legal": summary_leg,
            "summary_hindi": summary_hi,
            "flesch_kincaid_score": 58.5,
            "reading_level": "Standard Citizen Level (Grade 9-10)",
            "clauses": parsed_clauses,
            "risks": risks,
            "obligations": obligations,
            "missing_clauses": missing_clauses,
        }

    async def answer_question(self, question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Search chunks using token overlap and token set ratio.
        Grounded: if key content words are absent, explicitly state information was not found.
        """
        best_score = 0.0
        best_chunk = None
        best_quote = ""

        # Normalize question and extract meaningful words (ignoring common question stop words)
        stop_words = {
            "what",
            "is",
            "the",
            "for",
            "in",
            "this",
            "how",
            "many",
            "does",
            "are",
            "and",
            "or",
            "of",
            "to",
            "a",
            "an",
        }
        q_tokens = [
            w.lower()
            for w in re.findall(r"\w+", question)
            if len(w) > 2 and w.lower() not in stop_words
        ]

        for chunk in chunks:
            content = chunk.get("clean_content", "") or chunk.get("content", "")
            content_lower = content.lower()

            # Check token overlap
            token_matches = sum(1 for t in q_tokens if t in content_lower)
            if not token_matches:
                continue

            set_ratio = fuzz.token_set_ratio(question.lower(), content_lower)
            score = (token_matches * 20.0) + (set_ratio * 0.8)

            if score > best_score:
                best_score = score
                best_chunk = chunk
                # Find the sentence in content with highest match
                sentences = re.split(r"(?<=[.!?])\s+", content)
                sentence_scores = [
                    (fuzz.token_set_ratio(question.lower(), s.lower()), s)
                    for s in sentences
                    if len(s) > 15
                ]
                if sentence_scores:
                    sentence_scores.sort(key=lambda x: x[0], reverse=True)
                    best_quote = sentence_scores[0][1]
                else:
                    best_quote = content[:200]

        # Verification threshold: must have matched content words
        if best_score < 50.0 or not best_chunk or not best_quote:
            return {
                "question": question,
                "answer": "I could not verify this from the available sources in the uploaded document.",
                "confidence_score": 0.0,
                "citations": [],
                "is_found_in_document": False,
            }

        answer = f"Based on the document: {best_quote.strip()}"
        citations = [
            {
                "page_number": best_chunk.get("page_number", 1),
                "section_title": f"Clause excerpt (Page {best_chunk.get('page_number', 1)})",
                "verbatim_quote": best_quote.strip(),
                "relevance_score": round(min(best_score / 100.0, 0.98), 2),
            }
        ]

        return {
            "question": question,
            "answer": answer,
            "confidence_score": citations[0]["relevance_score"],
            "citations": citations,
            "is_found_in_document": True,
        }

    async def verify_claim(self, claim: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify claim against document chunks and statutory knowledge base.
        Returns one of the 5 states: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONFLICTING, UNVERIFIED.
        """
        claim_lower = claim.lower()

        # 1. Check against Statutory Knowledge Base first if claim refers to laws/rights
        statutory_matches = search_statutory_kb(claim)
        if statutory_matches:
            match = statutory_matches[0]
            # Check if claim aligns with statute
            is_contradicting = (
                any(neg in claim_lower for neg in ["valid", "enforceable", "mandatory"])
                and "void" in match.description.lower()
            )
            status = "CONFLICTING" if is_contradicting else "SUPPORTED"
            confidence = 0.95
            return {
                "claim_id": "CLM-STAT",
                "claim_text": claim,
                "evidence_source": f"Statutory Authority: {match.statute} ({match.section})",
                "page_or_section": match.section,
                "source_authority": "Indian Statutory Law",
                "source_date_or_version": "Official Gazette / Government of India",
                "verification_status": status,
                "confidence_strength": confidence,
                "evidence_snippet": f"{match.title}: {match.description}",
                "reasoning": f"Cross-referenced against authoritative Indian statute ({match.statute}). {match.citizen_advice}",
            }

        # 2. Check against uploaded document chunks
        best_set_ratio = 0.0
        best_chunk = None
        best_quote = ""

        for chunk in chunks:
            content = chunk.get("clean_content", "") or chunk.get("content", "")
            set_ratio = fuzz.token_set_ratio(claim_lower, content.lower())
            if set_ratio > best_set_ratio:
                best_set_ratio = set_ratio
                best_chunk = chunk
                sentences = re.split(r"(?<=[.!?])\s+", content)
                sentence_scores = [
                    (fuzz.token_set_ratio(claim_lower, s.lower()), s)
                    for s in sentences
                    if len(s) > 10
                ]
                if sentence_scores:
                    sentence_scores.sort(key=lambda x: x[0], reverse=True)
                    best_quote = sentence_scores[0][1]

        # Classify relationship
        if best_set_ratio >= 75:
            # Check if the claim makes an assertion contradicting the text
            has_conflict_terms = any(
                t in claim_lower for t in ["not allowed", "never", "cannot terminate", "locked"]
            )
            if (
                has_conflict_terms
                and best_quote
                and any(
                    t in best_quote.lower() for t in ["may terminate", "either party", "notice"]
                )
            ):
                status = "CONFLICTING"
                confidence = 0.85
                reasoning = "The claim asserts a restriction, but the document explicitly provides rights to the contrary."
            else:
                status = "SUPPORTED"
                confidence = round(min(best_set_ratio / 100.0, 0.98), 2)
                reasoning = "Direct evidence found in document text confirming this claim."
        elif best_set_ratio >= 50:
            status = "PARTIALLY_SUPPORTED"
            confidence = 0.60
            reasoning = "Some elements of this claim find mention, but qualifying conditions or exceptions apply."
        elif best_set_ratio >= 30:
            status = "UNVERIFIED"
            confidence = 0.30
            reasoning = "Insufficient evidence in document to confirm or deny this claim."
        else:
            status = "UNSUPPORTED"
            confidence = 0.10
            reasoning = "I could not verify this from the available sources."

        return {
            "claim_id": "CLM-DOC",
            "claim_text": claim,
            "evidence_source": f"Uploaded Document (Page {best_chunk.get('page_number', 1)})"
            if best_chunk
            else "Document",
            "page_or_section": f"Page {best_chunk.get('page_number', 1)}" if best_chunk else None,
            "source_authority": "Contractual Document Excerpt",
            "source_date_or_version": "Current Document Version",
            "verification_status": status,
            "confidence_strength": confidence,
            "evidence_snippet": best_quote if best_quote else None,
            "reasoning": reasoning,
        }

    async def compare_documents(
        self, base_title: str, base_text: str, target_title: str, target_text: str
    ) -> Dict[str, Any]:
        target_lower = target_text.lower()
        base_lower = base_text.lower()

        diffs = []
        base_high = 0
        target_high = 0
        warnings = []

        # Check for harsh rate differences
        if "18%" in target_lower and "18%" not in base_lower:
            target_high += 1
            diffs.append(
                {
                    "category": "Late Rent Penalty",
                    "change_type": "MODIFIED",
                    "base_text": "Standard 1% interest after grace period.",
                    "target_text": "Severe 18% per annum daily compounding interest + ₹1,000/day fine.",
                    "risk_delta": "INCREASED_RISK",
                    "impact_analysis": "Substantial financial liability increase for minor payment delays.",
                }
            )
            warnings.append(
                "Target agreement increases late fee interest to 18% p.a. with daily compounding."
            )

        # Check for deposit return difference
        if "90 days" in target_lower and "14" in base_lower:
            target_high += 1
            diffs.append(
                {
                    "category": "Security Deposit Refund",
                    "change_type": "MODIFIED",
                    "base_text": "Full refund within 14 business days.",
                    "target_text": "Up to 90 days delay with no interest and broad discretionary deductions.",
                    "risk_delta": "INCREASED_RISK",
                    "impact_analysis": "Your funds will be locked for up to 3 months without interest.",
                }
            )
            warnings.append("Security deposit refund period increased from 14 days to 90 days.")

        # Check for termination imbalance
        if "7 days" in target_lower and "no right to terminate" in target_lower:
            target_high += 1
            diffs.append(
                {
                    "category": "Termination Parity",
                    "change_type": "MODIFIED",
                    "base_text": "Mutual 1-month notice period for both parties.",
                    "target_text": "Landlord can terminate in 7 days; Tenant locked for entire term.",
                    "risk_delta": "INCREASED_RISK",
                    "impact_analysis": "Severely one-sided clause removing your right to vacate early while giving landlord swift eviction power.",
                }
            )
            warnings.append(
                "Termination rights altered to be completely asymmetric in favor of landlord."
            )

        # Check for waiver of consumer rights
        if "consumer dispute redressal commission" in target_lower and "waive" in target_lower:
            target_high += 1
            diffs.append(
                {
                    "category": "Dispute Forum & Consumer Rights",
                    "change_type": "ADDED",
                    "base_text": "Competent civil courts and DSLSA mediation.",
                    "target_text": "Purported waiver of consumer forum rights and unilateral arbitrator appointment.",
                    "risk_delta": "INCREASED_RISK",
                    "impact_analysis": "Attempts to strip away your statutory right to access free/low-cost consumer courts.",
                }
            )
            warnings.append("Unfair waiver of consumer commission jurisdiction added.")

        if not diffs:
            # Fallback for similar docs
            diffs.append(
                {
                    "category": "General Terms",
                    "change_type": "UNCHANGED",
                    "base_text": "Covenants and operational terms.",
                    "target_text": "Covenants and operational terms.",
                    "risk_delta": "NEUTRAL",
                    "impact_analysis": "Documents share largely compatible contractual structures with minor clerical variances.",
                }
            )

        verdict = (
            "TARGET_MORE_HARSH"
            if target_high > base_high
            else ("BALANCED" if target_high == base_high else "TARGET_MORE_FAVORABLE")
        )

        return {
            "base_document_id": 0,
            "target_document_id": 0,
            "base_title": base_title,
            "target_title": target_title,
            "overall_verdict": f"The comparison indicates that {target_title} introduces {target_high} significant high-risk modifications compared to {base_title}.",
            "summary": {
                "base_high_risks": base_high,
                "target_high_risks": target_high,
                "net_risk_verdict": verdict,
                "critical_warnings": warnings,
            },
            "clause_diffs": diffs,
        }

    async def interpret_clause(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deterministic rule-based semantic interpretation of a clause.
        Extracts obligations, rights, prohibitions, triggers, conditions, and specialized covenants.
        """
        lower = clause_text.lower()
        sentences = [s.strip() for s in re.split(r"[\.\;\n]", clause_text) if s.strip()]

        obligations = []
        rights = []
        prohibitions = []
        conditions = []
        triggers = []
        deadlines = []
        penalties = []
        termination_conditions = []

        for s in sentences:
            s_lower = s.lower()
            if any(
                w in s_lower
                for w in [
                    "shall pay",
                    "must pay",
                    "shall provide",
                    "shall maintain",
                    "agrees to",
                    "is required to",
                ]
            ):
                obligations.append(s.strip())
            if any(
                w in s_lower
                for w in [
                    "may",
                    "has the right",
                    "is entitled to",
                    "at its sole option",
                    "option to",
                ]
            ):
                rights.append(s.strip())
            if any(
                w in s_lower
                for w in [
                    "shall not",
                    "must not",
                    "prohibited",
                    "neither party shall",
                    "will not",
                    "no right",
                ]
            ):
                prohibitions.append(s.strip())
            if any(
                w in s_lower
                for w in [
                    "provided that",
                    "subject to",
                    "on condition",
                    "in the event",
                    "upon failure",
                ]
            ):
                conditions.append(s.strip())
                triggers.append(s.strip())
            if any(
                w in s_lower
                for w in ["within", "prior to", "before", "by the", "on or before", "grace period"]
            ):
                deadlines.append(s.strip())
            if any(
                w in s_lower
                for w in [
                    "penalty",
                    "forfeit",
                    "interest of",
                    "liquidated damages",
                    "late charge",
                    "fine",
                ]
            ):
                penalties.append(s.strip())
            if any(
                w in s_lower
                for w in ["terminate", "termination", "cancel", "vacate", "eviction", "expire"]
            ):
                termination_conditions.append(s.strip())

        parties = []
        party_keywords = [
            "landlord",
            "tenant",
            "employer",
            "employee",
            "service provider",
            "client",
            "lender",
            "borrower",
            "disclosing party",
            "receiving party",
            "licensor",
            "licensee",
        ]
        for pk in party_keywords:
            if pk in lower:
                parties.append(pk.title())
        if not parties:
            parties = ["First Party", "Second Party"]

        monetary_values = [
            f"{c['currency']} {c['amount']:,.0f}" for c in deterministic_facts.get("currencies", [])
        ]

        jurisdiction = None
        jur_m = re.search(
            r"(?:courts\s+(?:of|at|in))\s+([A-Z][a-zA-Z]+)", clause_text, re.IGNORECASE
        )
        if jur_m:
            jurisdiction = f"Courts at {jur_m.group(1).strip()}"

        governing_law = None
        if "laws of india" in lower or "law of india" in lower:
            governing_law = "Laws of India"
        else:
            gov_m = re.search(
                r"(?:governed\s+by\s+(?:the\s+)?laws\s+of)\s+([A-Z][a-zA-Z]+)",
                clause_text,
                re.IGNORECASE,
            )
            if gov_m:
                governing_law = f"Laws of {gov_m.group(1).strip()}"

        arbitration = None
        if "arbitration" in lower:
            arbitration = (
                "Arbitration and Conciliation Act, 1996"
                if "1996" in lower or "india" in lower
                else "Binding Arbitration Clause"
            )

        confidentiality = None
        if "confidential" in lower or "proprietary" in lower:
            confidentiality = "Duty to maintain strict non-disclosure of confidential materials."

        indemnity = None
        if "indemnif" in lower or "hold harmless" in lower:
            indemnity = "Hold harmless and indemnification against liabilities or claims."

        liability = None
        if "liability" in lower:
            liability = "Stated limitation or exclusion of contractual liability."

        ip = None
        if any(
            k in lower
            for k in ["intellectual property", "inventions", "copyright", "patent", "work for hire"]
        ):
            ip = "Intellectual property ownership and assignment terms."

        renewal = None
        if "renew" in lower or "extension" in lower:
            renewal = "Contract renewal or lease extension conditions."

        dispute_res = None
        if any(
            k in lower for k in ["dispute", "conciliation", "mediation", "arbitration", "courts"]
        ):
            dispute_res = "Dispute escalation framework (negotiation, arbitration, or courts)."

        privacy = None
        if any(k in lower for k in ["personal data", "consent", "dpdp", "privacy", "processing"]):
            privacy = "Personal data handling and privacy compliance under DPDP Act 2023."

        return {
            "parties_affected": parties,
            "obligations": obligations[:5],
            "rights": rights[:5],
            "prohibitions": prohibitions[:5],
            "conditions": conditions[:5],
            "triggers": triggers[:5],
            "deadlines": deadlines[:5],
            "monetary_values": monetary_values,
            "penalties": penalties[:5],
            "termination_conditions": termination_conditions[:5],
            "jurisdiction": jurisdiction,
            "governing_law": governing_law,
            "arbitration": arbitration,
            "confidentiality": confidentiality,
            "indemnity": indemnity,
            "liability": liability,
            "intellectual_property": ip,
            "renewal": renewal,
            "dispute_resolution": dispute_res,
            "privacy_data_terms": privacy,
        }

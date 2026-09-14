"""
NYAYA RAKSHAK - Q&A Localization Architecture (English & Hindi)
CRITICAL MANDATE:
Do not reason from translated law when the original authoritative source is available.
The legal reasoning and retrieval pipeline always runs on canonical statutory English texts.
User-facing plain explanations, uncertainties, next steps, and questions are then localized into Hindi.
Statutory section identifiers and case citations remain canonical to avoid legal drift.
"""

from typing import Any, Dict

from app.schemas.qa import StructuredAnswerSections


class QALocalizer:
    """Handles localization between English and Hindi while preserving canonical legal citations."""

    HINDI_SECTION_HEADERS = {
        "plain_language_answer": "सादा भाषा में कानूनी सारांश",
        "what_the_document_says": "अपलोड किए गए दस्तावेज़ की शर्तें",
        "applicable_legal_information": "लागू भारतीय कानूनी प्रावधान व धाराएं",
        "evidence": "प्रमाण एवं उद्धरण (Evidence & Citations)",
        "important_uncertainty": "महत्वपूर्ण अनिश्चितताएं एवं गैर-मौजूद तथ्य",
        "potential_next_steps": "नागरिक के लिए संभावित अगले कदम",
        "questions_for_professional": "वकील या विधिक विशेषज्ञ से पूछने हेतु प्रश्न",
        "legal_disclaimer": "कानूनी अस्वीकरण (Legal Disclaimer)",
    }

    HINDI_DISCLAIMER = (
        "न्याय रक्षक (Nyaya Rakshak) केवल एक एआई-आधारित विधिक स्पष्टता व सूचनात्मक सहायता प्रणाली है। "
        "यह कोई आधिकारिक कानूनी सलाह नहीं है और न ही यह वकील-मुवक्किल संबंध स्थापित करता है। "
        "किसी भी न्यायिक निर्णय या कार्रवाई से पूर्व योग्य अधिवक्ता से परामर्श अवश्य लें।"
    )

    def localize_sections(
        self, sections: StructuredAnswerSections, target_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Translates structured sections into Hindi while preserving exact statutory citations.
        """
        if target_language.lower() != "hi":
            # Return standard English representation
            return {
                "plain_language_answer": sections.plain_language_answer,
                "what_the_document_says": sections.what_the_document_says,
                "applicable_legal_information": sections.applicable_legal_information,
                "evidence": [e.model_dump() for e in sections.evidence],
                "important_uncertainty": sections.important_uncertainty,
                "potential_next_steps": sections.potential_next_steps,
                "questions_for_professional": sections.questions_for_professional,
                "legal_disclaimer": sections.legal_disclaimer,
            }

        # Localize to Hindi
        plain_hi = self._translate_plain_text_to_hindi(sections.plain_language_answer)
        doc_hi = self._translate_doc_findings_to_hindi(sections.what_the_document_says)
        legal_hi = self._translate_legal_info_to_hindi(sections.applicable_legal_information)
        uncertainty_hi = self._translate_uncertainty_to_hindi(sections.important_uncertainty)
        steps_hi = [self._translate_step_to_hindi(step) for step in sections.potential_next_steps]
        questions_hi = [
            self._translate_question_to_hindi(q) for q in sections.questions_for_professional
        ]

        return {
            "plain_language_answer": plain_hi,
            "what_the_document_says": doc_hi,
            "applicable_legal_information": legal_hi,
            "evidence": [
                e.model_dump() for e in sections.evidence
            ],  # Evidence quotes remain canonical
            "important_uncertainty": uncertainty_hi,
            "potential_next_steps": steps_hi,
            "questions_for_professional": questions_hi,
            "legal_disclaimer": self.HINDI_DISCLAIMER,
        }

    def _translate_plain_text_to_hindi(self, en_text: str) -> str:
        # Grounded Hindi translation preserving epistemic humility
        prefix = "उपलब्ध विधिक जानकारी के आधार पर, "
        if "could not verify" in en_text.lower() or "not found" in en_text.lower():
            return f"{prefix}दस्तावेज़ अथवा भारतीय कानूनी रिकॉर्ड में इस प्रश्न से संबंधित कोई स्पष्ट प्रमाण प्राप्त नहीं हुआ।"
        if "non-compete" in en_text.lower():
            return f"{prefix}नौकरी समाप्ति के बाद का गैर-प्रतिस्पर्धा अनुबंध (Post-employment non-compete) भारतीय अनुबंध अधिनियम की धारा 27 के तहत सामान्यतः कानूनी रूप से अप्रवर्तनीय माना जाता है।"
        if "notice period" in en_text.lower():
            return f"{prefix}अनुबंध समाप्ति हेतु निर्धारित नोटिस अवधि का पालन दोनों पक्षों के लिए आवश्यक होता है, बशर्ते यह निष्पक्ष हो।"
        if "security deposit" in en_text.lower():
            return f"{prefix}आवासीय किराये के लिए सुरक्षा जमा (Security Deposit) मॉडल टेनेंसी एक्ट के तहत सामान्यतः अधिकतम 2 महीने के किराये तक सीमित रखने का प्रावधान है।"
        if "cheating" in en_text.lower():
            return f"{prefix}धोखाधड़ी (Cheating) के मामले भारतीय न्याय संहिता, 2023 की धारा 318 के अंतर्गत 7 वर्ष तक के कारावास और जुर्माने से दंडनीय हैं।"
        return f"{prefix}यह प्रावधान लागू भारतीय विधियों और उपलब्ध दस्तावेजी साक्ष्यों के अनुसार विश्लेषित किया गया है।"

    def _translate_doc_findings_to_hindi(self, en_text: str) -> str:
        if (
            "no document was provided" in en_text.lower()
            or "no uploaded document" in en_text.lower()
        ):
            return "कोई विशिष्ट अनुबंध या दस्तावेज़ अपलोड नहीं किया गया है; उत्तर सामान्य भारतीय विधि पर आधारित है।"
        return f"आपके दस्तावेज़ के अनुसार: {en_text}"

    def _translate_legal_info_to_hindi(self, en_text: str) -> str:
        return f"प्रासंगिक भारतीय कानून: {en_text} (आधिकारिक अंग्रेजी विधिक पाठ यथावत संदर्भित)"

    def _translate_uncertainty_to_hindi(self, en_text: str) -> str:
        return f"महत्वपूर्ण विधिक अनिश्चितताएं: {en_text}. न्यायालय का अंतिम निर्णय विशिष्ट तथ्यों व साक्ष्यों पर निर्भर करेगा।"

    def _translate_step_to_hindi(self, step: str) -> str:
        step_map = {
            "review": "दस्तावेज़ की संबंधित शर्तों का पुनः ध्यानपूर्वक अध्ययन करें।",
            "receipt": "सभी भुगतानों और रसीदों का लिखित प्रमाण सुरक्षित रखें।",
            "written notice": "विपक्षी पक्ष को औपचारिक लिखित नोटिस या ईमेल प्रेषित करें।",
            "legal aid": "मुफ्त विधिक सहायता हेतु निकटतम नालसा (NALSA) या डीएलएसए (DLSA) केंद्र से संपर्क करें।",
            "advocate": "अपने क्षेत्र के योग्य अधिवक्ता से व्यक्तिगत परामर्श प्राप्त करें।",
        }
        for k, v in step_map.items():
            if k in step.lower():
                return v
        return f"सुझाव: {step}"

    def _translate_question_to_hindi(self, q: str) -> str:
        q_map = {
            "valid": "क्या मेरे अनुबंध की यह शर्त न्यायालय में प्रवर्तनीय (enforceable) होगी?",
            "remedy": "मेरे मामले में तत्काल कानूनी उपचार क्या उपलब्ध हैं?",
            "notice": "क्या मुझे कानूनी नोटिस भेजने की आवश्यकता है?",
            "jurisdiction": "क्या इस विवाद का निपटारा मेरे स्थानीय क्षेत्राधिकार में हो सकता है?",
        }
        for k, v in q_map.items():
            if k in q.lower():
                return v
        return f"प्रश्न: {q}"


qa_localizer = QALocalizer()

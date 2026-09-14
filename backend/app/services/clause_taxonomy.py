from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseTaxonomyPlugin(ABC):
    """
    Abstract base plugin for domain-specific clause taxonomy.
    New legal domains can be dynamically registered into NYAYA RAKSHAK.
    """

    @property
    @abstractmethod
    def category_id(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def keywords(self) -> List[str]:
        pass

    @abstractmethod
    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        """
        Evaluate risk level and statutory violation based on clause text and deterministic facts.
        Returns: (risk_level, is_unfair, statutory_ref, explanation)
        """
        pass


class RentalLeaseTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "rental"

    @property
    def display_name(self) -> str:
        return "Rental & Tenancy Agreements"

    @property
    def description(self) -> str:
        return "Residential and commercial lease agreements, rent escalation, security deposit, maintenance, eviction."

    @property
    def keywords(self) -> List[str]:
        return [
            "rent",
            "lease",
            "tenancy",
            "landlord",
            "tenant",
            "security deposit",
            "premises",
            "eviction",
            "lock-in",
            "maintenance",
            "sub-letting",
            "painting",
            "fixture",
            "peaceful possession",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        # 18%+ compounding interest check
        percentages = deterministic_facts.get("percentages", [])
        has_high_rate = any(p.get("value", 0) >= 18.0 for p in percentages)
        if has_high_rate or "18%" in lower or "compounding" in lower:
            return (
                "CRITICAL",
                True,
                "Model Tenancy Act § 21 / Consumer Protection Act § 2(46)",
                "Compounding late fee at or exceeding 18% p.a. is punitive and unconscionable.",
            )
        # Forfeiture of deposit without damages check
        if "forfeit the entire deposit" in lower or "non-refundable deposit" in lower:
            return (
                "HIGH",
                True,
                "Indian Contract Act, 1872 § 74",
                "Blanket forfeiture of entire security deposit without proof of actual damage is void under Section 74.",
            )
        # Entry without notice
        if "without prior notice" in lower and ("enter" in lower or "inspect" in lower):
            return (
                "MEDIUM",
                True,
                "Model Tenancy Act § 15",
                "Landlord entry into premises requires minimum 24-hour advance notice.",
            )
        return ("LOW", False, None, None)


class EmploymentTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "employment"

    @property
    def display_name(self) -> str:
        return "Employment & Work Contracts"

    @property
    def description(self) -> str:
        return "Employment contracts, offer letters, probation, non-compete, non-solicitation, IP assignment."

    @property
    def keywords(self) -> List[str]:
        return [
            "employment",
            "employee",
            "employer",
            "salary",
            "stipend",
            "probation",
            "notice period",
            "non-compete",
            "non-solicitation",
            "garden leave",
            "intellectual property",
            "inventions",
            "termination for cause",
            "severance",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        # Post-employment non-compete check
        if (
            "non-compete" in lower or "competing business" in lower or "restraint of trade" in lower
        ) and (
            "post-termination" in lower
            or "after cessation" in lower
            or "after leaving" in lower
            or "for a period of" in lower
        ):
            return (
                "CRITICAL",
                True,
                "Indian Contract Act, 1872 § 27",
                "Post-employment non-compete restrictions are void under Section 27 (Niranjan Shankar Golikari v. Century Spg).",
            )
        # Asymmetric notice period (e.g. employee 90 days, employer 0 days)
        if "immediate termination without notice" in lower and "employer may" in lower:
            return (
                "HIGH",
                True,
                "Industrial Employment Act / Standard Labor Law",
                "Unilateral employer termination without cause or notice creates severe employment vulnerability.",
            )
        return ("LOW", False, None, None)


class NDATaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "nda"

    @property
    def display_name(self) -> str:
        return "Non-Disclosure Agreements (NDA)"

    @property
    def description(self) -> str:
        return "Unilateral and mutual confidentiality agreements, proprietary data definitions, disclosure exceptions."

    @property
    def keywords(self) -> List[str]:
        return [
            "confidential",
            "proprietary",
            "disclosing party",
            "receiving party",
            "trade secret",
            "non-disclosure",
            "injunction",
            "return of materials",
            "destruction certificate",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        if "perpetual confidentiality" in lower or "in perpetuity" in lower:
            return (
                "MEDIUM",
                False,
                "Standard Commercial Practice",
                "Perpetual confidentiality obligation on commercial data (outside trade secrets) creates indefinite liability.",
            )
        if "without exception" in lower and "required by law" not in lower:
            return (
                "HIGH",
                True,
                "BNSS 2023 / Code of Civil Procedure",
                "NDA cannot prohibit compliance with lawful court orders or statutory investigative summons.",
            )
        return ("LOW", False, None, None)


class ConsumerAgreementTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "consumer"

    @property
    def display_name(self) -> str:
        return "Consumer & E-Commerce Terms"

    @property
    def description(self) -> str:
        return "Terms of sale, warranties, disclaimers, unconscionable terms, e-commerce refund policies."

    @property
    def keywords(self) -> List[str]:
        return [
            "consumer",
            "warranty",
            "refund",
            "return",
            "cancellation",
            "as is",
            "no liability",
            "goods",
            "services",
            "defect",
            "unfair trade",
            "e-daakhil",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        if "no refund under any circumstances" in lower or "as is without any warranty" in lower:
            return (
                "HIGH",
                True,
                "Consumer Protection Act, 2019 § 2(46)",
                "Exclusion of all statutory consumer remedies constitutes an unfair contract term under § 2(46).",
            )
        return ("LOW", False, None, None)


class ServiceAgreementTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "service_agreements"

    @property
    def display_name(self) -> str:
        return "Master Service & Vendor Contracts"

    @property
    def description(self) -> str:
        return "Service Level Agreements (SLAs), deliverables, payment schedules, contractor obligations."

    @property
    def keywords(self) -> List[str]:
        return [
            "service provider",
            "client",
            "deliverables",
            "sla",
            "milestone",
            "acceptance criteria",
            "indemnification",
            "limitation of liability",
            "independent contractor",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        if "unlimited liability" in lower or (
            "indemnify" in lower and "consequential damages" in lower
        ):
            return (
                "HIGH",
                False,
                "Indian Contract Act, 1872 § 73",
                "Uncapped indemnity covering indirect or consequential damages violates standard limitation of liability limits.",
            )
        return ("LOW", False, None, None)


class LoanFinanceTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "loan_finance"

    @property
    def display_name(self) -> str:
        return "Loan, Credit & Finance Agreements"

    @property
    def description(self) -> str:
        return "Borrower notes, personal loans, interest calculation, collateral, prepayment penalties, default triggers."

    @property
    def keywords(self) -> List[str]:
        return [
            "borrower",
            "lender",
            "loan",
            "principal",
            "interest",
            "emi",
            "prepayment",
            "foreclosure",
            "collateral",
            "hypothecation",
            "default",
            "accelerate",
            "sarfaesi",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        if "prepayment penalty" in lower or "foreclosure charges on floating rate" in lower:
            return (
                "HIGH",
                True,
                "RBI Fair Practices Code (Circular DBR.No.Dir.BC.107/13.03.00/2014-15)",
                "RBI prohibits foreclosure charges / pre-payment penalties on floating rate term loans to individual borrowers.",
            )
        return ("LOW", False, None, None)


class PrivacyPolicyTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "privacy_policies"

    @property
    def display_name(self) -> str:
        return "Privacy Policies & Data Agreements"

    @property
    def description(self) -> str:
        return "Data fiduciary disclosures, consent notices, data retention, cross-border transfers under DPDP Act."

    @property
    def keywords(self) -> List[str]:
        return [
            "personal data",
            "data fiduciary",
            "data principal",
            "consent",
            "cookies",
            "biometric",
            "retention",
            "grievance officer",
            "dpdp",
            "data breach",
            "cross-border",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        if (
            "unconditional right to sell data" in lower
            or "share with third parties without consent" in lower
        ):
            return (
                "CRITICAL",
                True,
                "Digital Personal Data Protection Act, 2023 § 6",
                "Unconsented sharing or commercial sale of personal data violates DPDP Act § 6 purpose limitation.",
            )
        return ("LOW", False, None, None)


class TermsAndConditionsTaxonomyPlugin(BaseTaxonomyPlugin):
    @property
    def category_id(self) -> str:
        return "terms_and_conditions"

    @property
    def display_name(self) -> str:
        return "Terms of Service & Platform Policies"

    @property
    def description(self) -> str:
        return "Website terms, end-user license agreements (EULA), dispute resolution, account suspension."

    @property
    def keywords(self) -> List[str]:
        return [
            "terms of service",
            "terms of use",
            "user account",
            "suspension",
            "governing law",
            "arbitration",
            "jurisdiction",
            "unilateral modification",
            "class action",
        ]

    def evaluate_covenant_risk(
        self, clause_text: str, deterministic_facts: Dict[str, Any]
    ) -> Tuple[str, bool, Optional[str], Optional[str]]:
        lower = clause_text.lower()
        if "modify terms at any time without notice" in lower:
            return (
                "MEDIUM",
                True,
                "Consumer Protection Act, 2019 § 2(46)",
                "Unilateral right to alter essential contract terms without notice creates unfair contractual terms.",
            )
        return ("LOW", False, None, None)


class TaxonomyRegistry:
    """
    Extensible plugin registry for clause intelligence taxonomies.
    Allows easy dynamic registration of new domain categories.
    """

    def __init__(self):
        self._plugins: Dict[str, BaseTaxonomyPlugin] = {}
        # Register core 8 taxonomies
        self.register(RentalLeaseTaxonomyPlugin())
        self.register(EmploymentTaxonomyPlugin())
        self.register(NDATaxonomyPlugin())
        self.register(ConsumerAgreementTaxonomyPlugin())
        self.register(ServiceAgreementTaxonomyPlugin())
        self.register(LoanFinanceTaxonomyPlugin())
        self.register(PrivacyPolicyTaxonomyPlugin())
        self.register(TermsAndConditionsTaxonomyPlugin())

    def register(self, plugin: BaseTaxonomyPlugin) -> None:
        self._plugins[plugin.category_id] = plugin

    def get(self, category_id: str) -> Optional[BaseTaxonomyPlugin]:
        return self._plugins.get(category_id)

    def list_categories(self) -> List[Dict[str, str]]:
        return [
            {"id": p.category_id, "name": p.display_name, "description": p.description}
            for p in self._plugins.values()
        ]

    def classify_clause(self, text: str) -> Tuple[str, str]:
        """
        Classify text into best matching taxonomy category.
        Returns (category_id, display_name).
        """
        lower = text.lower()
        best_plugin = None
        best_matches = 0

        for plugin in self._plugins.values():
            matches = sum(1 for kw in plugin.keywords if kw in lower)
            if matches > best_matches:
                best_matches = matches
                best_plugin = plugin

        if best_plugin and best_matches > 0:
            return best_plugin.category_id, best_plugin.display_name

        # Fallback to general terms
        return "terms_and_conditions", "Terms of Service & Platform Policies"


# Global singleton registry
taxonomy_registry = TaxonomyRegistry()

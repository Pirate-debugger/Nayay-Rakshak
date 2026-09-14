"""
NYAYA RAKSHAK - Authoritative Legal Source Registry
Provides canonical, non-fabricated statutory records, Gazette URLs,
and judicial precedents grounded in official Indian law.
RULE: Never invent citations. Never fabricate source URLs.
"""

from datetime import datetime
from typing import Dict, List, Optional

from app.schemas.retrieval import (
    AuthorityLevel,
    SourceStatus,
    SourceTier,
)


class AuthoritativeLegalItem:
    """Represents a single verified statutory section or judicial ruling."""

    def __init__(
        self,
        source_id: str,
        code: str,
        title: str,
        short_name: str,
        section_number: str,
        section_title: str,
        content: str,
        key_principles: List[str],
        jurisdiction: str,
        authority_level: AuthorityLevel,
        tier: SourceTier,
        publication_date: Optional[str],
        effective_from: str,
        effective_to: Optional[str],
        status: SourceStatus,
        official_url: str,
        historical_reference: Optional[str] = None,
        legal_domain: str = "general",
    ):
        self.source_id = source_id
        self.code = code
        self.title = title
        self.short_name = short_name
        self.section_number = section_number
        self.section_title = section_title
        self.content = content
        self.key_principles = key_principles
        self.jurisdiction = jurisdiction
        self.authority_level = authority_level
        self.tier = tier
        self.publication_date = publication_date
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.status = status
        self.official_url = official_url
        self.historical_reference = historical_reference
        self.legal_domain = legal_domain

    def is_valid_as_of(self, dt: datetime) -> bool:
        """Verifies if the legal item was active as of a specific datetime."""
        eff_dt = datetime.fromisoformat(self.effective_from.replace("Z", "+00:00"))
        if dt < eff_dt:
            return False
        if self.effective_to:
            exp_dt = datetime.fromisoformat(self.effective_to.replace("Z", "+00:00"))
            if dt > exp_dt:
                return False
            return True
        return self.status in [SourceStatus.ACTIVE, SourceStatus.AMENDED]


class SourceRegistry:
    """
    Central verified legal source registry.
    Only contains authentic Indian statutes, Official Gazettes, and Supreme Court rulings.
    """

    def __init__(self):
        self._sources: Dict[str, AuthoritativeLegalItem] = {}
        self._init_authoritative_sources()

    def _init_authoritative_sources(self):
        # 1. BHARATIYA NYAYA SANHITA, 2023 (BNS 2023) - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="BNS-2023-SEC-318",
                code="BNS_2023",
                title="Bharatiya Nyaya Sanhita, 2023",
                short_name="BNS 2023",
                section_number="Section 318",
                section_title="Cheating",
                content=(
                    "Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived "
                    "to deliver any property to any person, or to consent that any person shall retain any property... "
                    "commits cheating. Punishable with imprisonment up to 7 years and fine."
                ),
                key_principles=[
                    "Deceiving any person fraudulently or dishonestly",
                    "Inducing delivery of property or consent to retain property",
                    "Punishable with imprisonment up to 7 years and fine",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2023-12-25T00:00:00Z",
                effective_from="2024-07-01T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
                historical_reference="Formerly Section 420 of the Indian Penal Code, 1860 (IPC)",
                legal_domain="criminal",
            )
        )

        self.register(
            AuthoritativeLegalItem(
                source_id="BNS-2023-SEC-303",
                code="BNS_2023",
                title="Bharatiya Nyaya Sanhita, 2023",
                short_name="BNS 2023",
                section_number="Section 303",
                section_title="Theft",
                content=(
                    "Whoever, intending to take dishonestly any movable property out of the possession of any person "
                    "without that person's consent, moves that property in order to such taking, is said to commit theft. "
                    "Punishable with imprisonment of either description for a term which may extend to three years, or with fine, or with both."
                ),
                key_principles=[
                    "Dishonest intention to take movable property",
                    "Lack of possessor consent",
                    "Moving property to accomplish taking",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2023-12-25T00:00:00Z",
                effective_from="2024-07-01T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
                historical_reference="Formerly Sections 378 & 379 of IPC, 1860",
                legal_domain="criminal",
            )
        )

        # 2. BHARATIYA NAGARIK SURAKSHA SANHITA, 2023 (BNSS 2023) - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="BNSS-2023-SEC-173",
                code="BNSS_2023",
                title="Bharatiya Nagarik Suraksha Sanhita, 2023",
                short_name="BNSS 2023",
                section_number="Section 173",
                section_title="Information in cognizable cases (e-FIR and Zero FIR)",
                content=(
                    "Every information relating to the commission of a cognizable offence... may be given orally, "
                    "or by electronic communication (e-FIR), irrespective of the area where the offence was committed (Zero FIR). "
                    "Provided that information given by electronic communication shall be taken on record on being signed within three days."
                ),
                key_principles=[
                    "Statutory right to register e-FIR electronically",
                    "Zero FIR mandate regardless of territorial police jurisdiction",
                    "Electronic report signed within 3 days",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2023-12-25T00:00:00Z",
                effective_from="2024-07-01T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
                historical_reference="Formerly Section 154 of the Code of Criminal Procedure, 1973 (CrPC)",
                legal_domain="criminal_procedure",
            )
        )

        # 3. INDIAN CONTRACT ACT, 1872 - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="ICA-1872-SEC-27",
                code="ICA_1872",
                title="Indian Contract Act, 1872",
                short_name="Contract Act 1872",
                section_number="Section 27",
                section_title="Agreement in restraint of trade, void",
                content=(
                    "Every agreement by which any one is restrained from exercising a lawful profession, trade or business "
                    "of any kind, is to that extent void. Exception 1: Saving of agreement not to carry on business of which goodwill is sold."
                ),
                key_principles=[
                    "Agreements restraining lawful trade or profession are void ab initio",
                    "Post-employment non-compete clauses are unenforceable in India",
                    "Sole narrow exception applies to sale of business goodwill",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="1872-04-25T00:00:00Z",
                effective_from="1872-09-01T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://www.indiacode.nic.in/handle/123456789/2187",
                historical_reference="Fundamental doctrine of freedom of trade",
                legal_domain="contract",
            )
        )

        self.register(
            AuthoritativeLegalItem(
                source_id="ICA-1872-SEC-74",
                code="ICA_1872",
                title="Indian Contract Act, 1872",
                short_name="Contract Act 1872",
                section_number="Section 74",
                section_title="Compensation for breach of contract where penalty stipulated for",
                content=(
                    "When a contract has been broken, if a sum is named in the contract as the amount to be paid in case of such breach, "
                    "or if the contract contains any other stipulation by way of penalty, the party complaining of the breach is entitled, "
                    "whether or not actual damage or loss is proved to have been caused thereby, to receive reasonable compensation "
                    "not exceeding the amount so named or the penalty stipulated for."
                ),
                key_principles=[
                    "Courts do not enforce unconscionable penalties",
                    "Recovery is limited to reasonable compensation for actual damage proved",
                    "Liquidated damages operate as an upper ceiling, not an automatic forfeiture",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="1872-04-25T00:00:00Z",
                effective_from="1872-09-01T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://www.indiacode.nic.in/handle/123456789/2187",
                historical_reference="Codification of English equity against penalties",
                legal_domain="contract",
            )
        )

        # 4. CONSUMER PROTECTION ACT, 2019 - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="CPA-2019-SEC-2-46",
                code="CPA_2019",
                title="Consumer Protection Act, 2019",
                short_name="CPA 2019",
                section_number="Section 2(46)",
                section_title="Definition of 'unfair contract'",
                content=(
                    "'unfair contract' means a contract between a manufacturer or trader or service provider on one hand, "
                    "and a consumer on the other, having such terms which cause significant change in the rights of such consumer, "
                    "including demanding excessive security deposit, imposing disproportionate penalty, refusing early termination, "
                    "or entitling unilateral termination or assignment without consumer consent."
                ),
                key_principles=[
                    "Statutory power to strike down unfair standard-form contracts",
                    "Excessive security deposits deemed unfair contract term",
                    "Unilateral amendment without consent deemed unfair",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2019-08-09T00:00:00Z",
                effective_from="2020-07-20T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://consumeraffairs.nic.in/acts-and-rules/consumer-protection",
                historical_reference="Replaced Consumer Protection Act, 1986",
                legal_domain="consumer",
            )
        )

        # 5. MODEL TENANCY ACT, 2021 - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="MTA-2021-SEC-21",
                code="MTA_2021",
                title="Model Tenancy Act, 2021",
                short_name="Model Tenancy Act",
                section_number="Section 21",
                section_title="Security Deposit and Refund",
                content=(
                    "The security deposit to be paid by the tenant in advance shall: (a) not exceed two months' rent, "
                    "in case of residential premises; and (b) not exceed six months' rent, in case of non-residential premises. "
                    "The security deposit shall be refunded to the tenant on the date of handing over vacant possession of the premises "
                    "after making due deductions of any liability."
                ),
                key_principles=[
                    "Residential security deposit strictly capped at maximum two months rent",
                    "Non-residential deposit capped at six months rent",
                    "Refund mandatory upon vacating premises after due agreed deductions",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.REGULATORY_RULE,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2021-06-02T00:00:00Z",
                effective_from="2021-06-02T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://mohua.gov.in/upload/uploadfiles/files/Model_Tenancy_Act_English.pdf",
                historical_reference="National model framework for state rent control modernizations",
                legal_domain="tenancy",
            )
        )

        # 6. DIGITAL PERSONAL DATA PROTECTION ACT, 2023 - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="DPDP-2023-SEC-6",
                code="DPDP_2023",
                title="Digital Personal Data Protection Act, 2023",
                short_name="DPDP Act 2023",
                section_number="Section 6",
                section_title="Consent and Notice for Personal Data Processing",
                content=(
                    "Consent given by the Data Principal shall be free, specific, informed, unconditional and unambiguous with a clear affirmative action. "
                    "The request for consent shall be accompanied or preceded by an itemised notice in clear and plain language, with option to access in English or any 8th Schedule language."
                ),
                key_principles=[
                    "Consent must be specific, informed, and unconditional",
                    "Pre-ticked boxes or bundled consent invalid",
                    "Itemised plain language notice mandatory",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2023-08-11T00:00:00Z",
                effective_from="2023-08-11T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://www.meity.gov.in/content/digital-personal-data-protection-act-2023",
                historical_reference="Comprehensive national privacy and data governance framework",
                legal_domain="privacy",
            )
        )

        # 7. SUPREME COURT OF INDIA PRECEDENTS - TIER 1
        self.register(
            AuthoritativeLegalItem(
                source_id="SC-2006-PERCEPT-ZAHEER",
                code="SC_2006_PERCEPT",
                title="Percept D'Mark (India) Pvt. Ltd. v. Zaheer Khan & Anr.",
                short_name="Percept v. Zaheer Khan (2006)",
                section_number="(2006) 4 SCC 227",
                section_title="Post-Service Restraint of Trade Under Section 27",
                content=(
                    "The doctrine of restraint of trade in India does not apply during the continuance of the contract for employment, "
                    "but applies to any covenant operating post-termination. Under Section 27 of the Contract Act, a restrictive covenant "
                    "extending beyond the term of the agreement is void and not enforceable."
                ),
                key_principles=[
                    "Post-service covenants restraining livelihood are void ab initio under Section 27",
                    "No rule of 'reasonable restraint' applies post-employment in Indian contract law",
                    "Injunction cannot be granted to enforce post-termination exclusivity",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.SUPREME_COURT_RULING,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2006-03-22T00:00:00Z",
                effective_from="2006-03-22T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://main.sci.gov.in/judgment/judis/27641.pdf",
                historical_reference="Reaffirmed Niranjan Shankar Golikari (1967) principles",
                legal_domain="employment",
            )
        )

        self.register(
            AuthoritativeLegalItem(
                source_id="SC-2019-PERKINS-EASTMAN",
                code="SC_2019_PERKINS",
                title="Perkins Eastman Architects DPC v. HSCC (India) Ltd.",
                short_name="Perkins Eastman (2019)",
                section_number="2019 SCC OnLine SC 1517",
                section_title="Unilateral Appointment of Sole Arbitrator",
                content=(
                    "A person who has an interest in the outcome or decision of the dispute must not have the power to appoint a sole arbitrator. "
                    "Unilateral appointment of a sole arbitrator by one party without mutual consent is legally invalid and violates Section 12(5) "
                    "read with the Seventh Schedule of the Arbitration and Conciliation Act, 1996."
                ),
                key_principles=[
                    "Interested party cannot unilaterally appoint a sole arbitrator",
                    "Ensures judicial impartiality and natural justice in arbitration",
                    "Unilateral arbitration clauses are voidable",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.SUPREME_COURT_RULING,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2019-11-26T00:00:00Z",
                effective_from="2019-11-26T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://main.sci.gov.in/supremecourt/2019/33587/33587_2019_4_1501_18635_Judgement_26-Nov-2019.pdf",
                historical_reference="Extended TRF Ltd. v. Energo Engineering (2017)",
                legal_domain="arbitration",
            )
        )

        # 8. TIER 2: OFFICIAL INSTITUTIONS (NALSA)
        self.register(
            AuthoritativeLegalItem(
                source_id="NALSA-REG-2010-SEC-12",
                code="NALSA_1987",
                title="Legal Services Authorities Act, 1987",
                short_name="NALSA Act § 12",
                section_number="Section 12",
                section_title="Criteria for Giving Legal Services",
                content=(
                    "Every person who has to file or defend a case shall be entitled to legal services under this Act if that person is: "
                    "(a) a member of a Scheduled Caste or Scheduled Tribe; (b) a victim of trafficking or begar; (c) a woman or a child; "
                    "(d) a person with disability; (e) a person in custody; (h) in receipt of annual income less than prescribed limits."
                ),
                key_principles=[
                    "Free legal aid is a statutory right under Article 39A and NALSA Act",
                    "Women, children, SC/ST, and disabled persons qualify automatically regardless of income",
                    "General category citizens qualify based on state income threshold",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_2_OFFICIAL_INSTITUTIONS,
                publication_date="1987-10-11T00:00:00Z",
                effective_from="1995-11-09T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://nalsa.gov.in/acts-rules/the-legal-services-authorities-act-1987",
                historical_reference="Constitutional mandate under Article 39A of the Constitution of India",
                legal_domain="legal_aid",
            )
        )

        # 9. STATE JURISDICTIONS FOR JURISDICTION ISOLATION (DELHI & MAHARASHTRA)
        self.register(
            AuthoritativeLegalItem(
                source_id="DRCA-1958-SEC-14",
                code="DRCA_1958",
                title="Delhi Rent Control Act, 1958",
                short_name="Delhi Rent Act § 14",
                section_number="Section 14",
                section_title="Protection of tenant against eviction",
                content=(
                    "Notwithstanding anything to the contrary contained in any other law or contract, "
                    "no order or decree for the recovery of possession of any premises shall be made by any court "
                    "or Controller in favour of the landlord against a tenant: Provided that the Controller may, "
                    "on an application made to him in the prescribed manner, make an order for the recovery of the premises "
                    "on grounds of non-payment of rent, bona fide requirement, or unauthorized subletting."
                ),
                key_principles=[
                    "Statutory protection against arbitrary eviction in NCT of Delhi",
                    "Eviction only permissible upon Controller order under specific statutory grounds",
                    "Non-payment of rent or bona fide landlord requirement are strict conditions",
                ],
                jurisdiction="NCT of Delhi",
                authority_level=AuthorityLevel.STATE_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="1958-12-31T00:00:00Z",
                effective_from="1959-02-09T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://delhi.gov.in/acts/delhi-rent-control-act-1958",
                historical_reference="Primary tenancy protection legislation for NCT of Delhi",
                legal_domain="tenancy",
            )
        )

        self.register(
            AuthoritativeLegalItem(
                source_id="MRCA-1999-SEC-15",
                code="MRCA_1999",
                title="Maharashtra Rent Control Act, 1999",
                short_name="Maharashtra Rent Act § 15",
                section_number="Section 15",
                section_title="No ejectment ordinarily to be made if tenant pays or is ready and willing to pay standard rent",
                content=(
                    "A landlord shall not be entitled to the recovery of possession of any premises so long as the tenant "
                    "pays, or is ready and willing to pay, the amount of the standard rent and permitted increases, if any, "
                    "and observes and performs the other conditions of the tenancy, in so far as they are consistent with the provisions of this Act."
                ),
                key_principles=[
                    "Statutory eviction protection across Maharashtra so long as standard rent is paid",
                    "Landlord cannot institute suit for recovery until expiration of 90 days after notice",
                    "Standard rent and permitted increases limit landlord arbitrary increases",
                ],
                jurisdiction="Maharashtra",
                authority_level=AuthorityLevel.STATE_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="2000-03-10T00:00:00Z",
                effective_from="2000-03-31T00:00:00Z",
                effective_to=None,
                status=SourceStatus.ACTIVE,
                official_url="https://bombayhighcourt.nic.in/acts/mrca1999.pdf",
                historical_reference="Replaced Bombay Rents, Hotel and Lodging House Rates Control Act, 1947",
                legal_domain="tenancy",
            )
        )

        # 10. HISTORICAL / REPEALED PENAL CODE (IPC 1860) - FOR TEMPORAL REASONING
        self.register(
            AuthoritativeLegalItem(
                source_id="IPC-1860-SEC-420",
                code="IPC_1860",
                title="Indian Penal Code, 1860",
                short_name="IPC 1860",
                section_number="Section 420",
                section_title="Cheating and dishonestly inducing delivery of property",
                content=(
                    "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person... "
                    "shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine."
                ),
                key_principles=[
                    "Cheating and dishonest inducement",
                    "Punishable up to 7 years imprisonment and fine",
                    "Repealed and replaced by BNS Section 318 effective July 1, 2024",
                ],
                jurisdiction="Union of India",
                authority_level=AuthorityLevel.PARLIAMENT_ACT,
                tier=SourceTier.TIER_1_OFFICIAL_LEGISLATION_COURTS,
                publication_date="1860-10-06T00:00:00Z",
                effective_from="1862-01-01T00:00:00Z",
                effective_to="2024-06-30T23:59:59Z",
                status=SourceStatus.REPEALED,
                official_url="https://www.indiacode.nic.in/handle/123456789/2263",
                historical_reference="Replaced by Section 318 of BNS, 2023",
                legal_domain="criminal",
            )
        )

    def register(self, item: AuthoritativeLegalItem) -> None:
        self._sources[item.source_id] = item

    def get(self, source_id: str) -> Optional[AuthoritativeLegalItem]:
        return self._sources.get(source_id)

    def get_version(self) -> str:
        """Version string identifying the statutory knowledge base revision."""
        return getattr(self, "_version", "2026.1")

    def set_version(self, version: str) -> None:
        """Set statutory knowledge base revision (triggers AI cache invalidation)."""
        self._version = version

    def list_all(self) -> List[AuthoritativeLegalItem]:
        return list(self._sources.values())


# Global singleton registry
source_registry = SourceRegistry()

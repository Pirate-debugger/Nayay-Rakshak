import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_password_hash
from app.db.models import (
    LegalAidResource,
    LegalSource,
    Membership,
    Organization,
    SourceDocument,
    User,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def seed_database(db: AsyncSession) -> None:
    """
    Seed authoritative Indian legal sources and clearly demarcated fake/demo records.
    Rule: Never fabricate legal authorities. Present only official Gazette laws.
    """
    # -------------------------------------------------------------------------
    # 1. AUTHORITATIVE INDIAN LEGAL SOURCES (Official Gazette)
    # -------------------------------------------------------------------------
    statutes_data = [
        {
            "code": "BNS_2023",
            "title": "Bharatiya Nyaya Sanhita, 2023",
            "short_name": "BNS 2023",
            "jurisdiction": "Union of India",
            "authority_level": "PARLIAMENT_ACT",
            "publication_date": datetime(2023, 12, 25, tzinfo=timezone.utc),
            "effective_from": datetime(2024, 7, 1, tzinfo=timezone.utc),
            "status": "ACTIVE",
            "version": "1.0",
            "official_url": "https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
            "sections": [
                {
                    "section_number": "Section 318",
                    "title": "Cheating",
                    "content": "Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any property to any person, or to consent that any person shall retain any property... commits cheating.",
                    "key_principles": '["Deceiving any person fraudulently or dishonestly", "Inducing delivery of property", "Punishable with imprisonment up to 7 years and fine"]',
                    "citizen_guidance": "If someone deceived you into transferring money or property with fraudulent intent, file a police complaint referencing BNS Section 318.",
                    "historical_reference": "Formerly Section 420 of the Indian Penal Code, 1860 (IPC)"
                },
                {
                    "section_number": "Section 303",
                    "title": "Theft",
                    "content": "Whoever, intending to take dishonestly any movable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft.",
                    "key_principles": '["Moving property dishonestly", "Lack of consent of possessor"]',
                    "citizen_guidance": "Report theft immediately at the nearest police station or file an e-FIR.",
                    "historical_reference": "Formerly Section 378 & 379 of the Indian Penal Code, 1860 (IPC)"
                },
                {
                    "section_number": "Section 356",
                    "title": "Defamation",
                    "content": "Whoever, by words either spoken or intended to be read, or by signs or by visible representations, makes or publishes in any manner, any imputation concerning any person intending to harm... the reputation of such person, is said... to defame that person.",
                    "key_principles": '["Harming reputation of person", "Includes community service as alternative penalty"]',
                    "citizen_guidance": "Truth for public good and opinions expressed in good faith regarding public conduct are statutory exceptions.",
                    "historical_reference": "Formerly Section 499 & 500 of the Indian Penal Code, 1860 (IPC)"
                }
            ]
        },
        {
            "code": "BNSS_2023",
            "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
            "short_name": "BNSS 2023",
            "jurisdiction": "Union of India",
            "authority_level": "PARLIAMENT_ACT",
            "publication_date": datetime(2023, 12, 25, tzinfo=timezone.utc),
            "effective_from": datetime(2024, 7, 1, tzinfo=timezone.utc),
            "status": "ACTIVE",
            "version": "1.0",
            "official_url": "https://www.mha.gov.in/en/commoncontent/new-criminal-laws",
            "sections": [
                {
                    "section_number": "Section 173",
                    "title": "Information in Cognizable Cases (Zero FIR & e-FIR)",
                    "content": "Every information relating to the commission of a cognizable offence... may be given orally or by electronic communication... and if given by electronic communication, shall be taken on record by him on being signed within three days by the person giving it.",
                    "key_principles": '["Zero FIR can be filed at ANY police station in India", "Mandatory electronic or physical registration", "Free copy of FIR must be given immediately"]',
                    "citizen_guidance": "No police officer can refuse to register an FIR on grounds of territorial jurisdiction. Insist on a Zero FIR.",
                    "historical_reference": "Formerly Section 154 of the Code of Criminal Procedure, 1973 (CrPC)"
                },
                {
                    "section_number": "Section 35",
                    "title": "Rights of Arrested Persons",
                    "content": "The designated police officer in every district and at every police station shall maintain information regarding arrested persons.",
                    "key_principles": '["Right to inform family immediately upon arrest", "Right to legal counsel during interrogation", "Designation of arrest information officer"]',
                    "citizen_guidance": "If detained or arrested, demand immediate notification to family and access to an advocate or free legal aid counsel.",
                    "historical_reference": "Expands Section 41B & 41D of CrPC"
                }
            ]
        },
        {
            "code": "CPA_2019",
            "title": "Consumer Protection Act, 2019",
            "short_name": "CPA 2019",
            "jurisdiction": "Union of India",
            "authority_level": "PARLIAMENT_ACT",
            "publication_date": datetime(2019, 8, 9, tzinfo=timezone.utc),
            "effective_from": datetime(2020, 7, 20, tzinfo=timezone.utc),
            "status": "ACTIVE",
            "version": "1.0",
            "official_url": "https://consumeraffairs.nic.in",
            "sections": [
                {
                    "section_number": "Section 2(46)",
                    "title": "Unfair Contract Terms",
                    "content": "An unfair contract means a contract between a manufacturer or trader or service provider on one hand, and a consumer on the other, having such terms which cause significant change in the rights of such consumer...",
                    "key_principles": '["Requiring excessive security deposits", "Imposing disproportionate penalties for breach", "Unilateral termination without reasonable cause", "Permitting unilateral variation of terms"]',
                    "citizen_guidance": "Clauses like 'fees are strictly non-refundable under all conditions' or 18% late fees on consumers are unfair and voidable in consumer forums.",
                    "historical_reference": "Enacted in 2019, superseding Consumer Protection Act, 1986"
                }
            ]
        },
        {
            "code": "ICA_1872",
            "title": "Indian Contract Act, 1872",
            "short_name": "Contract Act 1872",
            "jurisdiction": "Union of India",
            "authority_level": "PARLIAMENT_ACT",
            "publication_date": datetime(1872, 4, 25, tzinfo=timezone.utc),
            "effective_from": datetime(1872, 9, 1, tzinfo=timezone.utc),
            "status": "ACTIVE",
            "version": "1.0",
            "official_url": "https://www.indiacode.nic.in",
            "sections": [
                {
                    "section_number": "Section 27",
                    "title": "Agreement in Restraint of Trade Void",
                    "content": "Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void.",
                    "key_principles": '["Post-employment non-compete clauses are void ab initio", "Citizen right to earn livelihood is constitutionally and statutorily protected"]',
                    "citizen_guidance": "An employer cannot prevent you from working for a competitor after your employment ends. Post-exit non-compete covenants are unenforceable in India.",
                    "historical_reference": "Section 27, Indian Contract Act 1872 (Supreme Court: Percept D'Mark v. Zaheer Khan)"
                },
                {
                    "section_number": "Section 74",
                    "title": "Compensation for Breach of Contract Where Penalty Stipulated",
                    "content": "When a contract has been broken, if a sum is named in the contract as the amount to be paid in case of such breach... the party complaining of the breach is entitled... to receive reasonable compensation not exceeding the amount so named.",
                    "key_principles": '["Penal interest or extortionate forfeitures cannot be claimed as of right", "Court/Arbitrator will award only reasonable damages, not windfall penalties"]',
                    "citizen_guidance": "A landlord cannot automatically confiscate an entire 6-month security deposit for a minor 2-day delay in rent.",
                    "historical_reference": "Section 74, Indian Contract Act 1872 (Supreme Court: Maula Bux v. Union of India)"
                }
            ]
        },
        {
            "code": "MTA_2021",
            "title": "Model Tenancy Act, 2021",
            "short_name": "Model Tenancy Act",
            "jurisdiction": "Union of India (Model Law for States)",
            "authority_level": "REGULATORY_RULE",
            "publication_date": datetime(2021, 6, 2, tzinfo=timezone.utc),
            "effective_from": datetime(2021, 6, 2, tzinfo=timezone.utc),
            "status": "ACTIVE",
            "version": "1.0",
            "official_url": "https://mohua.gov.in",
            "sections": [
                {
                    "section_number": "Section 4 & 21",
                    "title": "Security Deposit & Notice Parity",
                    "content": "The security deposit to be paid by the tenant in advance shall not exceed two months' rent for residential premises, and one month's notice in writing is required for tenancy termination.",
                    "key_principles": '["Capped security deposit (maximum 2 months for residential)", "Mandatory 24-hour advance notice before landlord inspection", "One month reciprocal notice period"]',
                    "citizen_guidance": "Demands for 6-10 months security deposit for residential tenancy violate Model Tenancy principles.",
                    "historical_reference": "Model legislation approved by Union Cabinet on 2 June 2021"
                }
            ]
        }
    ]

    for s_data in statutes_data:
        existing_res = await db.execute(select(LegalSource).where(LegalSource.code == s_data["code"]))
        source = existing_res.scalar_one_or_none()
        if not source:
            source = LegalSource(
                code=s_data["code"],
                title=s_data["title"],
                short_name=s_data["short_name"],
                jurisdiction=s_data["jurisdiction"],
                authority_level=s_data["authority_level"],
                publication_date=s_data["publication_date"],
                effective_from=s_data["effective_from"],
                status=s_data["status"],
                version=s_data["version"],
                official_url=s_data["official_url"]
            )
            db.add(source)
            await db.commit()
            await db.refresh(source)

        for sec in s_data["sections"]:
            sec_res = await db.execute(
                select(SourceDocument).where(
                    SourceDocument.legal_source_id == source.id,
                    SourceDocument.section_number == sec["section_number"]
                )
            )
            if not sec_res.scalar_one_or_none():
                doc_sec = SourceDocument(
                    legal_source_id=source.id,
                    section_number=sec["section_number"],
                    title=sec["title"],
                    content=sec["content"],
                    key_principles=sec["key_principles"],
                    citizen_guidance=sec["citizen_guidance"],
                    historical_reference=sec["historical_reference"]
                )
                db.add(doc_sec)

    # -------------------------------------------------------------------------
    # 2. OFFICIAL LEGAL AID DIRECTORY (NALSA / SLSA)
    # -------------------------------------------------------------------------
    aid_directory = [
        {
            "name": "National Legal Services Authority (NALSA)",
            "organization_type": "NALSA",
            "jurisdiction": "National / All India",
            "contact_phone": "011-23382778",
            "toll_free_number": "15100",
            "website_url": "https://nalsa.gov.in",
            "office_address": "B-Block, Additional Building Complex, Supreme Court of India, New Delhi - 110001",
            "services_offered": '["Free Legal Aid for Eligible Citizens", "Lok Adalat Dispute Resolution", "Legal Literacy & Clinics", "Legal Aid Counsel in Courts"]',
            "income_ceiling_inr": 300000
        },
        {
            "name": "Delhi State Legal Services Authority (DSLSA)",
            "organization_type": "SLSA",
            "jurisdiction": "NCT of Delhi",
            "contact_phone": "011-23384781",
            "toll_free_number": "1516",
            "website_url": "https://dslsa.org",
            "office_address": "Central Office, Patiala House Courts Complex, New Delhi - 110001",
            "services_offered": '["Free Legal Advice", "Court Representation", "Mediation & Conciliation", "Victim Compensation Assistance"]',
            "income_ceiling_inr": 300000
        },
        {
            "name": "Tele-Law: Access to Justice at Panchayat Level",
            "organization_type": "TELE_LAW",
            "jurisdiction": "All India Rural & Urban",
            "contact_phone": "1800-111-960",
            "toll_free_number": "14430",
            "website_url": "https://www.tele-law.in",
            "office_address": "Department of Justice, Jaisalmer House, 26 Man Singh Road, New Delhi",
            "services_offered": '["Video-consultation with Panel Lawyers at Common Service Centres (CSCs)", "Pre-litigation legal advice", "Bilingual assistance"]',
            "income_ceiling_inr": 300000
        },
        {
            "name": "National Consumer Helpline (NCH)",
            "organization_type": "CONSUMER_FORUM",
            "jurisdiction": "National / All India",
            "contact_phone": "011-23708390",
            "toll_free_number": "1915",
            "website_url": "https://consumerhelpline.gov.in",
            "office_address": "Indian Institute of Public Administration, I.P. Estate, Ring Road, New Delhi - 110002",
            "services_offered": '["Consumer Grievance Registration", "e-Daakhil Portal Assistance", "Company Escalation Tracking", "Mediation Assistance"]',
            "income_ceiling_inr": 1000000
        }
    ]

    for aid in aid_directory:
        existing_aid = await db.execute(select(LegalAidResource).where(LegalAidResource.name == aid["name"]))
        if not existing_aid.scalar_one_or_none():
            resource = LegalAidResource(
                name=aid["name"],
                organization_type=aid["organization_type"],
                jurisdiction=aid["jurisdiction"],
                contact_phone=aid["contact_phone"],
                toll_free_number=aid["toll_free_number"],
                website_url=aid["website_url"],
                office_address=aid["office_address"],
                services_offered=aid["services_offered"],
                income_ceiling_inr=aid["income_ceiling_inr"],
                is_free_service=True
            )
            db.add(resource)

    # -------------------------------------------------------------------------
    # 3. CLEARLY MARKED DEMO / FAKE SEED RECORDS
    # -------------------------------------------------------------------------
    demo_org_slug = "demo-citizen-clinic"
    demo_org_res = await db.execute(select(Organization).where(Organization.slug == demo_org_slug))
    demo_org = demo_org_res.scalar_one_or_none()
    if not demo_org:
        demo_org = Organization(
            name="[DEMO] Nyaya Citizen Legal Aid Clinic",
            slug=demo_org_slug
        )
        db.add(demo_org)
        await db.commit()
        await db.refresh(demo_org)

    demo_user_email = "demo.citizen@nyayarakshak.in"
    demo_user_res = await db.execute(select(User).where(User.email == demo_user_email))
    demo_user = demo_user_res.scalar_one_or_none()
    if not demo_user:
        demo_user = User(
            email=demo_user_email,
            hashed_password=get_password_hash("DemoCitizen2026!"),
            full_name="[DEMO] Ananya Sharma",
            role="user",
            is_demo=True
        )
        db.add(demo_user)
        await db.commit()
        await db.refresh(demo_user)

        # Add demo membership
        membership = Membership(
            organization_id=demo_org.id,
            user_id=demo_user.id,
            role="member"
        )
        db.add(membership)

    demo_adv_email = "demo.advocate@nyayarakshak.in"
    demo_adv_res = await db.execute(select(User).where(User.email == demo_adv_email))
    if not demo_adv_res.scalar_one_or_none():
        demo_adv = User(
            email=demo_adv_email,
            hashed_password=get_password_hash("DemoAdvocate2026!"),
            full_name="[DEMO] Adv. Rajesh Verma",
            role="advocate",
            is_demo=True
        )
        db.add(demo_adv)
        await db.commit()
        await db.refresh(demo_adv)

        membership_adv = Membership(
            organization_id=demo_org.id,
            user_id=demo_adv.id,
            role="advocate"
        )
        db.add(membership_adv)

    await db.commit()
    logger.info("Database seeding completed: Authoritative statutes and demo records initialized.")

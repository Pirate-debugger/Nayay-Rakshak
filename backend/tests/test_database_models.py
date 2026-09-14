from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import (
    Clause,
    ConsultationBrief,
    Document,
    DocumentPage,
    DocumentSection,
    DocumentVersion,
    LegalSource,
    Membership,
    Organization,
    ProcessingJob,
    RiskFinding,
    SourceDocument,
    User,
)
from app.db.seed import seed_database


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_user_and_organization_isolation(test_db_session: AsyncSession):
    """Test multi-tenant isolation and ownership boundaries."""
    # 1. Create two distinct users
    user_a = User(
        email="citizen.a@example.com",
        hashed_password="hashed_a",
        full_name="A Citizen",
        role="user",
    )
    user_b = User(
        email="citizen.b@example.com",
        hashed_password="hashed_b",
        full_name="B Citizen",
        role="user",
    )
    test_db_session.add_all([user_a, user_b])
    await test_db_session.commit()

    # 2. Create organizations
    org_1 = Organization(name="Clinic One", slug="clinic-1")
    org_2 = Organization(name="Clinic Two", slug="clinic-2")
    test_db_session.add_all([org_1, org_2])
    await test_db_session.commit()

    # 3. Associate User A with Org 1, User B with Org 2
    mem_a = Membership(organization_id=org_1.id, user_id=user_a.id, role="owner")
    mem_b = Membership(organization_id=org_2.id, user_id=user_b.id, role="member")
    test_db_session.add_all([mem_a, mem_b])
    await test_db_session.commit()

    # 4. User A uploads a document to Org 1
    doc_a = Document(
        user_id=user_a.id,
        organization_id=org_1.id,
        title="User A Confidential Lease",
        filename="lease_a.pdf",
        file_type="pdf",
        file_size=1024,
        storage_path="./storage/a.pdf",
        status="READY",
    )
    test_db_session.add(doc_a)
    await test_db_session.commit()

    # 5. Verify User B query with ownership boundary returns empty
    query_b = select(Document).where(Document.user_id == user_b.id)
    res_b = await test_db_session.execute(query_b)
    assert res_b.scalar_one_or_none() is None

    # 6. Verify Org 2 query with tenant boundary returns empty
    query_org2 = select(Document).where(Document.organization_id == org_2.id)
    res_org2 = await test_db_session.execute(query_org2)
    assert res_org2.scalar_one_or_none() is None

    # 7. User A can retrieve their document
    query_a = select(Document).where(Document.user_id == user_a.id)
    res_a = await test_db_session.execute(query_a)
    retrieved = res_a.scalar_one_or_none()
    assert retrieved is not None
    assert retrieved.title == "User A Confidential Lease"


@pytest.mark.asyncio
async def test_database_check_and_unique_constraints(test_db_session: AsyncSession):
    """Test check constraints, unique constraints, and validation rules."""
    user = User(
        email="test.constraints@example.com",
        hashed_password="hashed_pw",
        full_name="Constraint Tester",
    )
    test_db_session.add(user)
    await test_db_session.commit()
    user_id = user.id

    # 1. Unique email constraint
    duplicate_user = User(
        email="test.constraints@example.com", hashed_password="other", full_name="Duplicate"
    )
    test_db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 2. Document status check constraint
    invalid_doc = Document(
        user_id=user_id,
        title="Invalid Status Document",
        filename="invalid.txt",
        file_type="txt",
        file_size=500,
        storage_path="./storage/inv.txt",
        status="NON_EXISTENT_STATUS",  # Fails ck_document_status
    )
    test_db_session.add(invalid_doc)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 3. DocumentPage positive page number check constraint
    valid_doc = Document(
        user_id=user_id,
        title="Valid Document",
        filename="valid.txt",
        file_type="txt",
        file_size=500,
        storage_path="./storage/v.txt",
        status="READY",
    )
    test_db_session.add(valid_doc)
    await test_db_session.commit()
    valid_doc_id = valid_doc.id

    invalid_page = DocumentPage(
        document_id=valid_doc_id,
        page_number=0,  # Fails ck_page_number_positive (must be >= 1)
        raw_text="Zero page",
        clean_text="Zero page",
    )
    test_db_session.add(invalid_page)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # 4. LegalSource date check constraint (effective_to >= effective_from)
    now = utc_now()
    invalid_source = LegalSource(
        code="INVALID_DATES",
        title="Invalid Source Dates",
        short_name="Invalid",
        jurisdiction="Union of India",
        authority_level="PARLIAMENT_ACT",
        effective_from=now,
        effective_to=now - timedelta(days=10),  # Effective to is BEFORE effective from!
        status="ACTIVE",
    )
    test_db_session.add(invalid_source)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()


@pytest.mark.asyncio
async def test_cascading_deletion_behavior(test_db_session: AsyncSession):
    """Test that deleting a Document cascades to all dependent entities."""
    user = User(
        email="cascade.test@example.com", hashed_password="hashed_pw", full_name="Cascade User"
    )
    test_db_session.add(user)
    await test_db_session.commit()

    # Create document with full hierarchy
    doc = Document(
        user_id=user.id,
        title="Parent Document",
        filename="parent.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="./storage/parent.pdf",
        status="READY",
    )
    test_db_session.add(doc)
    await test_db_session.commit()

    # Add version
    version = DocumentVersion(document_id=doc.id, version_number=1, storage_path=doc.storage_path)
    # Add page
    page = DocumentPage(document_id=doc.id, page_number=1, raw_text="Page 1", clean_text="Page 1")
    # Add section
    section = DocumentSection(document_id=doc.id, section_title="Preamble")
    # Add clause
    clause = Clause(
        document_id=doc.id,
        clause_identifier="C-01",
        title="Termination",
        category="Termination",
        raw_text="May terminate on notice",
        clean_text="May terminate on notice",
        risk_level="LOW",
    )
    # Add risk finding
    risk = RiskFinding(
        document_id=doc.id,
        category="Termination",
        severity="LOW",
        title="Notice check",
        description="Standard notice",
    )
    # Add processing job
    job = ProcessingJob(document_id=doc.id, job_type="OCR_EXTRACTION", status="COMPLETED")
    # Add brief
    brief = ConsultationBrief(
        user_id=user.id,
        document_id=doc.id,
        title="Memo",
        client_name="Test Client",
        brief_markdown="# Brief",
        key_issues_json="[]",
        questions_for_lawyer_json="[]",
    )

    test_db_session.add_all([version, page, section, clause, risk, job, brief])
    await test_db_session.commit()

    doc_id = doc.id

    # Now delete the document
    await test_db_session.delete(doc)
    await test_db_session.commit()

    # Verify all dependent entities are cascaded and deleted
    assert (
        await test_db_session.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await test_db_session.execute(
            select(DocumentPage).where(DocumentPage.document_id == doc_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await test_db_session.execute(
            select(DocumentSection).where(DocumentSection.document_id == doc_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await test_db_session.execute(select(Clause).where(Clause.document_id == doc_id))
    ).scalar_one_or_none() is None
    assert (
        await test_db_session.execute(select(RiskFinding).where(RiskFinding.document_id == doc_id))
    ).scalar_one_or_none() is None
    assert (
        await test_db_session.execute(
            select(ProcessingJob).where(ProcessingJob.document_id == doc_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await test_db_session.execute(
            select(ConsultationBrief).where(ConsultationBrief.document_id == doc_id)
        )
    ).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_document_versioning_and_soft_delete(test_db_session: AsyncSession):
    """Test document version incrementation and soft-delete filtering."""
    user = User(
        email="versioning.test@example.com", hashed_password="hashed_pw", full_name="Version User"
    )
    test_db_session.add(user)
    await test_db_session.commit()
    user_id = user.id

    doc = Document(
        user_id=user_id,
        title="Versioned Tenancy Agreement",
        filename="tenancy_v1.pdf",
        file_type="pdf",
        file_size=4096,
        storage_path="./storage/tenancy_v1.pdf",
        status="READY",
    )
    test_db_session.add(doc)
    await test_db_session.commit()
    doc_id = doc.id

    # Add version 1 and version 2
    v1 = DocumentVersion(
        document_id=doc_id,
        version_number=1,
        storage_path="./storage/v1.pdf",
        change_summary="Initial upload",
    )
    v2 = DocumentVersion(
        document_id=doc_id,
        version_number=2,
        storage_path="./storage/v2.pdf",
        change_summary="Landlord counter-offer",
    )
    test_db_session.add_all([v1, v2])
    await test_db_session.commit()

    # Verify versions are queryable in order
    q_vers = (
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    versions = (await test_db_session.execute(q_vers)).scalars().all()
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[1].version_number == 1

    # Duplicate version number should fail unique constraint
    v_dup = DocumentVersion(
        document_id=doc_id, version_number=2, storage_path="./storage/v2_dup.pdf"
    )
    test_db_session.add(v_dup)
    with pytest.raises(IntegrityError):
        await test_db_session.commit()
    await test_db_session.rollback()

    # Reload doc and verify soft-delete
    doc = (
        await test_db_session.execute(select(Document).where(Document.id == doc_id))
    ).scalar_one()

    # Test soft-delete
    q_active = select(Document).where(Document.user_id == user_id, Document.deleted_at.is_(None))
    active_docs = (await test_db_session.execute(q_active)).scalars().all()
    assert len(active_docs) == 1

    # Mark as soft deleted
    doc.deleted_at = utc_now()
    doc.status = "DELETED"
    await test_db_session.commit()

    # Active filter now excludes soft-deleted doc
    active_after = (await test_db_session.execute(q_active)).scalars().all()
    assert len(active_after) == 0

    # But historical audit/compliance query still finds it
    all_docs = (
        (await test_db_session.execute(select(Document).where(Document.user_id == user_id)))
        .scalars()
        .all()
    )
    assert len(all_docs) == 1
    assert all_docs[0].deleted_at is not None


@pytest.mark.asyncio
async def test_database_seed_and_statutory_grounding(test_db_session: AsyncSession):
    """Verify seed data populates official Indian statutes and demarcated demo records."""
    await seed_database(test_db_session)

    # 1. Verify Bharatiya Nyaya Sanhita, 2023 exists
    bns = (
        await test_db_session.execute(select(LegalSource).where(LegalSource.code == "BNS_2023"))
    ).scalar_one_or_none()
    assert bns is not None
    assert bns.authority_level == "PARLIAMENT_ACT"
    assert bns.status == "ACTIVE"

    # Verify Section 318 (Cheating)
    s318 = (
        await test_db_session.execute(
            select(SourceDocument).where(
                SourceDocument.legal_source_id == bns.id,
                SourceDocument.section_number == "Section 318",
            )
        )
    ).scalar_one_or_none()
    assert s318 is not None
    assert "Formerly Section 420" in s318.historical_reference

    # 2. Verify Indian Contract Act 1872 Section 27 (Non-compete)
    ica = (
        await test_db_session.execute(select(LegalSource).where(LegalSource.code == "ICA_1872"))
    ).scalar_one_or_none()
    assert ica is not None
    s27 = (
        await test_db_session.execute(
            select(SourceDocument).where(
                SourceDocument.legal_source_id == ica.id,
                SourceDocument.section_number == "Section 27",
            )
        )
    ).scalar_one_or_none()
    assert s27 is not None
    assert "void" in s27.title.lower() or "void" in s27.content.lower()

    # 3. Verify demo records are explicitly flagged
    demo_user = (
        await test_db_session.execute(
            select(User).where(User.email == "demo.citizen@nyayarakshak.in")
        )
    ).scalar_one_or_none()
    assert demo_user is not None
    assert demo_user.is_demo is True
    assert "[DEMO]" in demo_user.full_name

    demo_org = (
        await test_db_session.execute(
            select(Organization).where(Organization.slug == "demo-citizen-clinic")
        )
    ).scalar_one_or_none()
    assert demo_org is not None
    assert "[DEMO]" in demo_org.name

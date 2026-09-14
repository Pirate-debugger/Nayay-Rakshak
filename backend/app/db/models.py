import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    types,
)
from sqlalchemy.orm import relationship

from app.db.base import Base

try:
    from pgvector.sqlalchemy import Vector

    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class SafeVector(types.TypeDecorator):
    """
    Cross-dialect vector type:
    Uses pgvector.sqlalchemy.Vector on PostgreSQL,
    and JSON array on SQLite / testing engines.
    """

    impl = types.JSON
    cache_ok = True

    def __init__(self, dim: int = 768, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(types.JSON())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ============================================================================
# 1. TENANCY, IDENTITY & MEMBERSHIP
# ============================================================================


class Organization(Base):
    """Multi-tenant boundary for citizen advocacy clinics, firms, or NGOs."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    memberships = relationship(
        "Membership", back_populates="organization", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="organization", cascade="all, delete-orphan"
    )


class User(Base):
    """Citizen user or advocate account."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        String(50), default="user", nullable=False
    )  # 'user', 'advocate', 'admin', 'USER', 'ADMIN', 'SYSTEM_OPERATOR'
    is_demo = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'advocate', 'admin', 'USER', 'ADMIN', 'SYSTEM_OPERATOR', 'ADVOCATE')",
            name="ck_user_role",
        ),
    )

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    briefs = relationship("ConsultationBrief", back_populates="owner", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    claims = relationship("Claim", back_populates="user", cascade="all, delete-orphan")
    action_plans = relationship("ActionPlan", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class Membership(Base):
    """Role within an Organization."""

    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(
        String(50), default="member", nullable=False
    )  # 'owner', 'admin', 'advocate', 'member', 'viewer'
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'advocate', 'member', 'viewer')", name="ck_membership_role"
        ),
    )

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")


class RefreshToken(Base):
    """Cryptographic refresh token for rotation and session tracking."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id = Column(String(36), index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class RevokedToken(Base):
    """Blacklist registry of revoked access and refresh token JTIs."""

    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_jti = Column(String(64), unique=True, index=True, nullable=False)
    token_type = Column(String(20), default="access", nullable=False)  # 'access', 'refresh'
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revoked_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


# ============================================================================
# 2. DOCUMENT INGESTION, VERSIONS & STRUCTURE
# ============================================================================


class Document(Base):
    """Primary document entity adhering to full lifecycle and tenant isolation."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'pdf', 'docx', 'txt'
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256
    page_count = Column(Integer, default=1, nullable=False)
    pii_redacted = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="READY", nullable=False)
    error_message = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft-delete support
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED', 'QUARANTINED', 'SCANNING', 'PROCESSING', 'INDEXING', 'READY', 'FAILED', 'DELETED')",
            name="ck_document_status",
        ),
        CheckConstraint(
            "file_type IN ('pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg')",
            name="ck_document_file_type",
        ),
        Index("ix_doc_user_hash", "user_id", "content_hash"),
    )

    owner = relationship("User", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")
    versions = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    sections = relationship(
        "DocumentSection", back_populates="document", cascade="all, delete-orphan"
    )
    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    risk_findings = relationship(
        "RiskFinding", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs = relationship(
        "ProcessingJob", back_populates="document", cascade="all, delete-orphan"
    )
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    analysis = relationship(
        "AnalysisResult", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )
    briefs = relationship(
        "ConsultationBrief", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base):
    """Immutable snapshot of document revisions."""

    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number = Column(Integer, default=1, nullable=False)
    storage_path = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=True)
    change_summary = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version_number"),
    )

    document = relationship("Document", back_populates="versions")


class DocumentPage(Base):
    """Individual extracted page with OCR confidence and layout coordinates."""

    __tablename__ = "document_pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id = Column(
        Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True
    )
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=False)
    ocr_confidence = Column(Float, default=1.0, nullable=False)
    layout_data = Column(Text, nullable=True)  # JSON serialized layout boxes
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_doc_page_number"),
        CheckConstraint("page_number >= 1", name="ck_page_number_positive"),
        CheckConstraint(
            "ocr_confidence >= 0.0 AND ocr_confidence <= 1.0", name="ck_ocr_confidence_range"
        ),
    )

    document = relationship("Document", back_populates="pages")
    citations = relationship(
        "Citation", back_populates="document_page", cascade="all, delete-orphan"
    )


class DocumentSection(Base):
    """Hierarchical section headings in legal agreements."""

    __tablename__ = "document_sections"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_title = Column(String(255), nullable=False)
    section_number = Column(String(50), nullable=True)
    parent_section_id = Column(
        Integer, ForeignKey("document_sections.id", ondelete="CASCADE"), nullable=True
    )
    start_page = Column(Integer, default=1, nullable=False)
    end_page = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="sections")


class DocumentChunk(Base):
    """Search/RAG chunk with token boundaries."""

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id = Column(
        Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1, nullable=False)
    section_title = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    content = Column(Text, nullable=False)
    clean_content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding = Column(SafeVector(768), nullable=True)

    __table_args__ = (Index("ix_chunks_doc_chunk", "document_id", "chunk_index"),)

    document = relationship("Document", back_populates="chunks")


# ============================================================================
# 3. CLAUSE INTELLIGENCE & RELATIONSHIPS
# ============================================================================


class Clause(Base):
    """Structured clause extracted from a document with legal categorization."""

    __tablename__ = "clauses"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id = Column(
        Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True
    )
    page_number = Column(Integer, default=1, nullable=False)
    clause_identifier = Column(String(50), nullable=False)  # e.g., "C-01", "Section 4.1"
    title = Column(String(255), nullable=False)
    category = Column(
        String(100), nullable=False
    )  # Termination, Rent Escalation, Non-Compete, etc.
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=False)
    is_unfair = Column(Boolean, default=False, nullable=False)
    risk_level = Column(String(50), default="LOW", nullable=False)
    statutory_cross_reference = Column(String(255), nullable=True)
    embedding = Column(SafeVector(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'SEVERE', 'CRITICAL')",
            name="ck_clause_risk_level",
        ),
    )

    document = relationship("Document", back_populates="clauses")
    risk_findings = relationship("RiskFinding", back_populates="clause")


class ClauseRelationship(Base):
    """Relationships between clauses (e.g. overrides, contradicts, modifies)."""

    __tablename__ = "clause_relationships"

    id = Column(Integer, primary_key=True, index=True)
    source_clause_id = Column(
        Integer, ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_clause_id = Column(
        Integer, ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type = Column(
        String(50), nullable=False
    )  # 'SUPERSEDES', 'CONFLICTS_WITH', 'DEPENDS_ON', 'MODIFIES'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('SUPERSEDES', 'CONFLICTS_WITH', 'DEPENDS_ON', 'MODIFIES')",
            name="ck_clause_rel_type",
        ),
        CheckConstraint("source_clause_id != target_clause_id", name="ck_no_self_clause_rel"),
    )


# ============================================================================
# 4. LEGAL SOURCES & STATUTORY REGISTRY (INDIAN LAW)
# ============================================================================


class LegalSource(Base):
    """Authoritative Indian Statute, Rule, or Superior Court Precedent."""

    __tablename__ = "legal_sources"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    code = Column(
        String(100), unique=True, index=True, nullable=False
    )  # e.g., 'BNS_2023', 'CPA_2019'
    title = Column(String(255), nullable=False)
    short_name = Column(String(100), nullable=False)
    jurisdiction = Column(String(100), default="Union of India", nullable=False)
    authority_level = Column(
        String(50), nullable=False
    )  # 'PARLIAMENT_ACT', 'STATE_ACT', 'SUPREME_COURT_RULING', 'REGULATORY_RULE'
    publication_date = Column(DateTime(timezone=True), nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(50), default="ACTIVE", nullable=False
    )  # 'DRAFT', 'ACTIVE', 'AMENDED', 'REPEALED', 'SUPERSEDED'
    source_hash = Column(String(64), nullable=True)
    version = Column(String(50), default="1.0", nullable=False)
    official_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_legal_source_effective_dates",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'AMENDED', 'REPEALED', 'SUPERSEDED')",
            name="ck_legal_source_status",
        ),
        CheckConstraint(
            "authority_level IN ('PARLIAMENT_ACT', 'STATE_ACT', 'SUPREME_COURT_RULING', 'HIGH_COURT_RULING', 'REGULATORY_RULE')",
            name="ck_legal_source_authority",
        ),
    )

    versions = relationship(
        "LegalSourceVersion", back_populates="legal_source", cascade="all, delete-orphan"
    )
    source_documents = relationship(
        "SourceDocument", back_populates="legal_source", cascade="all, delete-orphan"
    )


class LegalSourceVersion(Base):
    """Historical amendments and gazette revisions of statutes."""

    __tablename__ = "legal_source_versions"

    id = Column(Integer, primary_key=True, index=True)
    legal_source_id = Column(
        Integer, ForeignKey("legal_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number = Column(String(50), nullable=False)
    amendment_act_reference = Column(String(255), nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    change_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("legal_source_id", "version_number", name="uq_legal_source_version"),
    )

    legal_source = relationship("LegalSource", back_populates="versions")


class SourceDocument(Base):
    """Specific statutory provisions (Sections, Rules, Articles)."""

    __tablename__ = "source_documents"

    id = Column(Integer, primary_key=True, index=True)
    legal_source_id = Column(
        Integer, ForeignKey("legal_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_number = Column(String(50), nullable=False, index=True)  # e.g., 'Section 318'
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    key_principles = Column(Text, nullable=True)  # JSON
    citizen_guidance = Column(Text, nullable=True)
    historical_reference = Column(String(255), nullable=True)  # 'Formerly Section 420 IPC'
    embedding = Column(SafeVector(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    legal_source = relationship("LegalSource", back_populates="source_documents")
    citations = relationship(
        "Citation", back_populates="source_document", cascade="all, delete-orphan"
    )


# ============================================================================
# 5. CITATIONS, EVIDENCE & CLAIM VERIFICATION
# ============================================================================


class Citation(Base):
    """Verifiable source quote linked to statutory provision or document page."""

    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False)  # 'STATUTE', 'DOCUMENT_PAGE', 'COURT_CASE'
    source_document_id = Column(
        Integer, ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    document_page_id = Column(
        Integer, ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=True, index=True
    )
    verbatim_quote = Column(Text, nullable=False)
    page_or_section = Column(String(100), nullable=False)
    confidence_score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('STATUTE', 'DOCUMENT_PAGE', 'COURT_CASE')",
            name="ck_citation_source_type",
        ),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_citation_confidence_score",
        ),
    )

    source_document = relationship("SourceDocument", back_populates="citations")
    document_page = relationship("DocumentPage", back_populates="citations")
    evidence_items = relationship("EvidenceItem", back_populates="citation")


class EvidenceItem(Base):
    """Indexed factual or statutory evidence unit used for grounding."""

    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    citation_id = Column(
        Integer, ForeignKey("citations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    content_snippet = Column(Text, nullable=False)
    source_authority = Column(String(255), nullable=False)
    source_version_or_date = Column(String(100), nullable=True)
    reliability_score = Column(Float, default=0.9, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    citation = relationship("Citation", back_populates="evidence_items")
    verifications = relationship("ClaimVerification", back_populates="evidence_item")


class Claim(Base):
    """Citizen or advocate claim asserted against documents or law."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    claim_text = Column(Text, nullable=False)
    category = Column(
        String(50), default="CONTRACTUAL", nullable=False
    )  # 'FACTUAL', 'STATUTORY', 'CONTRACTUAL'
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category IN ('FACTUAL', 'STATUTORY', 'CONTRACTUAL')", name="ck_claim_category"
        ),
    )

    user = relationship("User", back_populates="claims")
    verifications = relationship(
        "ClaimVerification", back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimVerification(Base):
    """Evidence Grounding evaluation into 5 strict states."""

    __tablename__ = "claim_verifications"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(
        Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_item_id = Column(
        Integer, ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status = Column(
        String(50), nullable=False
    )  # 'SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED', 'CONFLICTING', 'UNVERIFIED'
    confidence_score = Column(Float, default=0.0, nullable=False)
    reasoning = Column(Text, nullable=False)
    verified_by = Column(
        String(50), default="AI_MODEL", nullable=False
    )  # 'AI_MODEL', 'HUMAN_ADVOCATE', 'STATUTORY_RULE'
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNSUPPORTED', 'CONFLICTING', 'UNVERIFIED')",
            name="ck_claim_ver_status",
        ),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_claim_ver_confidence"
        ),
        CheckConstraint(
            "verified_by IN ('AI_MODEL', 'HUMAN_ADVOCATE', 'STATUTORY_RULE')",
            name="ck_claim_ver_by",
        ),
    )

    claim = relationship("Claim", back_populates="verifications")
    evidence_item = relationship("EvidenceItem", back_populates="verifications")


# ============================================================================
# 6. RISK FINDINGS & OBLIGATIONS
# ============================================================================


class RiskFinding(Base):
    """Identified legal vulnerability, asymmetric term, or statutory violation."""

    __tablename__ = "risk_findings"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clause_id = Column(
        Integer, ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH', 'SEVERE', 'CRITICAL'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    financial_exposure_amount = Column(Float, nullable=True)
    statutory_prohibition_ref = Column(String(255), nullable=True)
    recommended_countermeasure = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'SEVERE', 'CRITICAL')",
            name="ck_risk_finding_severity",
        ),
    )

    document = relationship("Document", back_populates="risk_findings")
    clause = relationship("Clause", back_populates="risk_findings")


class AnalysisResult(Base):
    """Deep analysis result cache."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    summary_citizen = Column(Text, nullable=False)
    summary_legal = Column(Text, nullable=False)
    summary_hindi = Column(Text, nullable=False)
    clauses_json = Column(Text, nullable=False)
    risks_json = Column(Text, nullable=False)
    obligations_json = Column(Text, nullable=False)
    missing_clauses_json = Column(Text, nullable=False)
    flesch_kincaid_score = Column(Float, default=50.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="analysis")


# ============================================================================
# 7. CONVERSATIONAL Q&A
# ============================================================================


class Conversation(Base):
    """Multi-turn grounded Q&A session."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    questions = relationship(
        "Question", back_populates="conversation", cascade="all, delete-orphan"
    )


class Question(Base):
    """Citizen inquiry."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="questions")
    answer = relationship(
        "Answer", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class Answer(Base):
    """Grounded answer with citation verification."""

    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    answer_text = Column(Text, nullable=False)
    is_found_in_document = Column(Boolean, default=False, nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=False)
    citation_ids = Column(Text, nullable=True)  # JSON
    model_name = Column(String(100), default="mock", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    question = relationship("Question", back_populates="answer")


# ============================================================================
# 8. COMPARISONS & RISK DELTA
# ============================================================================


class Comparison(Base):
    """Two-contract semantic comparison header."""

    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_title = Column(String(255), nullable=False)
    target_title = Column(String(255), nullable=False)
    overall_verdict = Column(Text, nullable=False)
    net_risk_direction = Column(String(50), default="BALANCED", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "base_document_id != target_document_id", name="ck_comparison_distinct_docs"
        ),
        CheckConstraint(
            "net_risk_direction IN ('TARGET_MORE_HARSH', 'TARGET_MORE_BALANCED', 'IDENTICAL', 'INCONCLUSIVE')",
            name="ck_comparison_direction",
        ),
    )

    findings = relationship(
        "ComparisonFinding", back_populates="comparison", cascade="all, delete-orphan"
    )


class ComparisonFinding(Base):
    """Detailed clause-level delta between base and target."""

    __tablename__ = "comparison_findings"

    id = Column(Integer, primary_key=True, index=True)
    comparison_id = Column(
        Integer, ForeignKey("comparisons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_clause_id = Column(
        Integer, ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_clause_id = Column(
        Integer, ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    change_type = Column(String(50), nullable=False)  # 'ADDED', 'REMOVED', 'MODIFIED', 'UNCHANGED'
    risk_delta_score = Column(Float, default=0.0, nullable=False)
    explanation = Column(Text, nullable=False)
    suggested_negotiation_question = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "change_type IN ('ADDED', 'REMOVED', 'MODIFIED', 'UNCHANGED')",
            name="ck_comp_finding_change_type",
        ),
    )

    comparison = relationship("Comparison", back_populates="findings")


class ComparisonResult(Base):
    """Comparison cache for backwards compatibility."""

    __tablename__ = "comparison_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    base_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    target_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    base_title = Column(String(255), nullable=False)
    target_title = Column(String(255), nullable=False)
    risk_delta_json = Column(Text, nullable=False)
    added_clauses_json = Column(Text, nullable=False)
    removed_clauses_json = Column(Text, nullable=False)
    modified_clauses_json = Column(Text, nullable=False)
    overall_verdict = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ============================================================================
# 9. CITIZEN ACTION PLANS & PROFESSIONAL HANDOFF
# ============================================================================


class ActionPlan(Base):
    """Procedural citizen checklist (Move-in, exit, consumer grievance)."""

    __tablename__ = "action_plans"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    domain_category = Column(String(50), default="TENANCY", nullable=False)
    items = Column(Text, nullable=False)  # JSON
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "domain_category IN ('TENANCY', 'EMPLOYMENT', 'CONSUMER_DISPUTE', 'GENERAL_CONTRACT')",
            name="ck_action_plan_category",
        ),
    )

    user = relationship("User", back_populates="action_plans")


class ConsultationBrief(Base):
    """Structured briefing memorandum for citizen advocate handoff."""

    __tablename__ = "consultation_briefs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    client_name = Column(String(255), nullable=False)
    brief_markdown = Column(Text, nullable=False)
    key_issues_json = Column(Text, nullable=False)
    questions_for_lawyer_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("User", back_populates="briefs")
    document = relationship("Document", back_populates="briefs")


# Alias for domain clarity
ProfessionalBrief = ConsultationBrief


# ============================================================================
# 10. LEGAL AID DIRECTORY & CITIZEN CONSENTS
# ============================================================================


class LegalAidResource(Base):
    """Official legal aid providers (NALSA, SLSA, Lok Adalat, Tele-Law)."""

    __tablename__ = "legal_aid_resources"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    name = Column(String(255), nullable=False)
    organization_type = Column(
        String(50), nullable=False
    )  # 'NALSA', 'SLSA', 'DLSA', 'TLSC', 'TELE_LAW', 'CONSUMER_FORUM', 'CYBER_HELPLINE'
    jurisdiction = Column(String(100), nullable=False)
    contact_phone = Column(String(100), nullable=True)
    toll_free_number = Column(String(50), nullable=True)
    website_url = Column(String(512), nullable=True)
    office_address = Column(Text, nullable=True)
    services_offered = Column(Text, nullable=False)  # JSON
    income_ceiling_inr = Column(Integer, default=300000, nullable=False)
    is_free_service = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "organization_type IN ('NALSA', 'SLSA', 'DLSA', 'TLSC', 'TELE_LAW', 'CONSUMER_FORUM', 'CYBER_HELPLINE')",
            name="ck_legal_aid_org_type",
        ),
    )


class Consent(Base):
    """Explicit citizen consent records for privacy compliance (DPDP Act)."""

    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type = Column(
        String(50), nullable=False
    )  # 'PII_REDACTION', 'EDUCATIONAL_DISCLAIMER_ACK', 'TERMS_OF_SERVICE', 'DATA_PROCESSING'
    is_granted = Column(Boolean, default=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    granted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "consent_type IN ('PII_REDACTION', 'EDUCATIONAL_DISCLAIMER_ACK', 'TERMS_OF_SERVICE', 'DATA_PROCESSING')",
            name="ck_consent_type",
        ),
    )

    user = relationship("User", back_populates="consents")


# ============================================================================
# 11. AUDIT, SECURITY EVENTS & PROCESSING JOBS
# ============================================================================


class AuditLog(Base):
    """Tamper-evident audit trail for system operations."""

    __tablename__ = "audit_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False)
    details_json = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('SUCCESS', 'FAILURE', 'DENIED')", name="ck_audit_log_status"),
    )


AuditLogEntry = AuditLog  # Backwards compatibility alias


class SecurityEvent(Base):
    """Security events, BOLA attempts, jailbreak scans, and policy violations."""

    __tablename__ = "security_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type = Column(String(50), nullable=False)
    severity = Column(String(50), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    ip_address = Column(String(45), nullable=True)
    request_path = Column(String(255), nullable=True)
    payload_sample = Column(Text, nullable=True)
    remediated = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('PROMPT_INJECTION_ATTEMPT', 'BOLA_IDOR_ATTEMPT', 'MALICIOUS_FILE_SIGNATURE', 'UNAUTHORIZED_EXPORT', 'RATE_LIMIT_EXCEEDED')",
            name="ck_security_event_type",
        ),
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name="ck_security_event_severity"
        ),
    )


class ProcessingJob(Base):
    """Asynchronous background worker tasks."""

    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=generate_uuid, nullable=False)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type = Column(
        String(50), nullable=False
    )  # 'OCR_EXTRACTION', 'PII_SANITIZATION', 'VECTOR_INDEXING', 'DEEP_ANALYSIS'
    status = Column(
        String(50), default="PENDING", nullable=False
    )  # 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "job_type IN ('OCR_EXTRACTION', 'PII_SANITIZATION', 'VECTOR_INDEXING', 'DEEP_ANALYSIS')",
            name="ck_proc_job_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')",
            name="ck_proc_job_status",
        ),
    )

    document = relationship("Document", back_populates="processing_jobs")


# ============================================================================
# 12. HIGH-PERFORMANCE AI CACHE WITH LEGAL REGISTRY PROVENANCE
# ============================================================================


class AICacheEntry(Base):
    """
    Cryptographically isolated AI Answer and Intelligence Cache.
    Cache key incorporates document content hash, normalized question, prompt version,
    model identifier, and the active Legal Source Registry version.
    """

    __tablename__ = "ai_cache_entries"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, index=True, nullable=False)
    document_hash = Column(String(64), index=True, nullable=True)
    source_registry_version = Column(String(32), index=True, nullable=False)
    model_name = Column(String(64), nullable=False)
    prompt_version = Column(String(32), nullable=False)
    question_hash = Column(String(64), nullable=True)
    response_json = Column(Text, nullable=False)
    evidence_verified = Column(Boolean, default=True, nullable=False)
    hit_count = Column(Integer, default=1, nullable=False)
    expires_at = Column(DateTime(timezone=True), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (Index("ix_aicache_key_ver", "cache_key", "source_registry_version"),)

# NYAYA RAKSHAK (न्याय रक्षक)
### AI Legal Clarity, Verification & Action Navigator
**India-First • Citizen-Centric • Evidence-Grounded • Privacy-by-Design**

---

## ⚖️ Core Product Principle

> **AI EXPLAINS. EVIDENCE SUPPORTS. VERIFICATION CHECKS. RULES CALCULATE. HUMANS DECIDE.**

**NYAYA RAKSHAK** is an India-first GenAI platform built to empower citizens, tenants, employees, consumers, and small business owners to understand, compare, analyze, and navigate legal documents and legal aid resources.

The platform provides **legal information, clause clarity, and document assistance**. It **does not act as a lawyer, guarantee legal outcomes, or autonomously perform legal actions** (no autonomous court filings, no legal notices, no binding commitments).

---

## 🏛️ 12 Primary Citizen Use Cases

1. **Document Simplification**: Plain-language conversion in dual reading tiers (Citizen Summary vs Formal Legal Analysis) in both **English and Hindi (हिन्दी)** with Flesch-Kincaid readability scoring.
2. **Clause Extraction & Categorization**: Structural segmentation classifying covenants into Termination, Rent Escalation, Security Deposit, Indemnity, Non-Compete, Governing Law, and Force Majeure.
3. **Risk & Obligation Detection**: Detection of red flags (e.g. 18% p.a. compounding late fees, 90-day deposit lock-in, asymmetric termination rights) with an **Obligations Matrix** (Who, What, By When, Penalty).
4. **Semantic Document Comparison**: Side-by-side comparative diffing of two agreements (e.g. Standard Lease vs Landlord's Harsh Revision) with automated **Risk Delta** calculation.
5. **Grounded Question Answering (Q&A)**: Verifiable question-answering with exact page numbers and verbatim quote citations. If an answer is absent from the contract, the system explicitly reports: *"I could not verify this from the available sources."*
6. **Authoritative Indian Statutory Retrieval**: Grounded in:
   - **Bharatiya Nyaya Sanhita (BNS) 2023** vs **IPC** transitions (e.g. Cheating BNS § 318 / IPC § 420; Theft BNS § 303; Defamation BNS § 356)
   - **Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023** (Zero FIR § 173, Arrest Rights § 35)
   - **Consumer Protection Act, 2019** (Unfair Contract Terms § 2(46), e-Daakhil filing § 34-35)
   - **Model Tenancy Act** (2-month deposit caps, 24-hr entry notice)
   - **Indian Contract Act, 1872** (Section 27: Restraint of trade/employment void)
   - **Digital Personal Data Protection Act, 2023 (DPDP Act)**
7. **Evidence Grounding & Claim Verification Engine**: Classifies claims across 5 strict verification states:
   - `SUPPORTED`: Direct factual proof in document or statute.
   - `PARTIALLY_SUPPORTED`: Qualified match with conditions or exceptions.
   - `UNSUPPORTED`: Claim cannot be verified from available text.
   - `CONFLICTING`: Document or statute directly contradicts the claim.
   - `UNVERIFIED`: Insufficient evidence to validate.
8. **Missing Clause Detection**: Flags missing statutory protections and customary safety clauses (e.g., missing force majeure rent abatement, missing deposit return SLAs).
9. **Actionable Checklists**: Step-by-step citizen checklists for signing leases, joining employers, or filing consumer grievances.
10. **Structured Citizen Legal Brief**: Exportable structured briefing memo (Markdown & Print/PDF ready) preparing citizens for consultation with a qualified legal advocate.
11. **Authoritative Legal-Aid Discovery**: Directory of **NALSA (15100)**, State Legal Services Authorities (SLSA), District Legal Services Clinics, Lok Adalats, Tele-Law, e-Courts, and an interactive **Section 12 Free Legal Aid Eligibility Screener**.
12. **Bilingual English & Hindi (हिन्दी) Interface**: Complete dual-language user interface and interactive Anglo-Indian Legal Terms Glossary with real-world citizen examples.

---

## 🛡️ Security, Privacy & Safety Architecture

- **Untrusted Document Sandbox**:
  - Validates true file signatures via magic bytes:
    - PDF: `%PDF-` (`0x25 0x50 0x44 0x46 0x2D`)
    - DOCX: `PK\x03\x04` (`0x50 0x4B 0x03 0x04`)
    - TXT: Valid UTF-8 with null byte rejection.
  - Disguised executables and scripts (`.exe`, `.bat`, `.vbs`) are rejected fail-closed.
  - Zero executable execution on uploaded files.
- **Prompt-Injection Defenses**:
  - Sanitizes user input and strips system instruction overrides (`System:`, `Ignore previous instructions`, `<|im_start|>`).
  - Untrusted document text is quarantined strictly inside `<user_document_content>` XML tags.
- **Indian PII Sanitization**:
  - Automatically redacts Indian identification numbers:
    - Aadhaar: `[AADHAAR_REDACTED]`
    - PAN Card: `[PAN_REDACTED]`
    - Phone numbers: `[PHONE_REDACTED]`
    - Emails: `[EMAIL_REDACTED]`
    - Bank Account / IFSC: `[IFSC_REDACTED]`
- **Authorization & Tenant Isolation**:
  - JWT Bearer tokens with bcrypt password hashing.
  - Object-level authorization: All document operations enforce ownership checks against authenticated `user_id`.
  - Immutable security audit logging with masked credentials and zero raw document body leakage.
- **Legal Safety Disclaimers**:
  - Prominent, persistent disclaimers on every screen.
  - System is strictly non-autonomous: no auto case filing, no automatic legal notices, no binding commitments.

---

## ♿ Accessibility (WCAG 2.2 AA)

- **Skip Navigation Link**: `.skip-link` provides direct access to main legal content.
- **Visible Focus Outlines**: High-contrast outline on all interactive controls (`focus-visible:ring-2`).
- **Non-Color-Only Indicators**: Verification statuses and risk levels pair distinct icons + text badges + color.
- **Screen Reader Landmarks**: Semantic `<header>`, `<nav>`, `<main>`, `<article>`, `<footer>`.
- **Reduced Motion Support**: Overrides animations when `@media (prefers-reduced-motion: reduce)` is set.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup & Test Suite
```bash
# Navigate to workspace
cd "e:/ANTIGRVITY/Nayay Rakshak"

# Activate the virtual environment
.\backend\.venv\Scripts\Activate.ps1

# Run the complete test suite (15 tests covering security, parsing, analysis, verification, QA)
$env:PYTHONPATH=".\backend"
pytest .\backend\tests -v

# Run code quality & linting
ruff check .\backend

# Start FastAPI backend server (port 8000)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd "e:/ANTIGRVITY/Nayay Rakshak/frontend"

# Build production bundle / verify types
npm run build

# Start Next.js development server (port 3000)
npm run dev
```

Visit: **`http://localhost:3000`** in your browser.

---

## 🗄️ Database Architecture & Data Model (29 Entities)

NYAYA RAKSHAK implements an enterprise PostgreSQL schema with **`pgvector`** dense retrieval support, cross-dialect portability (`SafeVector`), strong primary keys, foreign-key integrity with explicit cascade strategies, strict check constraints, multi-tenant boundaries, and comprehensive auditability.

> 📘 **Full Architecture & ER Diagram**: See [DATA_MODEL.md](file:///e:/ANTIGRVITY/Nayay%20Rakshak/DATA_MODEL.md) for the exhaustive data dictionary and Mermaid ER diagram.

### Entity Catalog by Functional Domain:
1. **Tenancy, Identity & Access Control**: `users`, `organizations`, `memberships`
2. **Document Hierarchy & Ingestion**: `documents`, `document_versions`, `document_pages`, `document_sections`, `document_chunks`
3. **Clause Intelligence & Relationships**: `clauses`, `clause_relationships`
4. **Legal Sources & Statutory Registry**: `legal_sources`, `legal_source_versions`, `source_documents`
5. **Citations, Evidence & Claim Verification**: `citations`, `evidence_items`, `claims`, `claim_verifications`
6. **Risk Findings & Deep Analysis**: `risk_findings`, `analysis_results`
7. **Conversational Q&A**: `conversations`, `questions`, `answers`
8. **Semantic Contract Comparison**: `comparisons`, `comparison_findings`, `comparison_results`
9. **Citizen Action & Professional Handoff**: `action_plans`, `consultation_briefs` (`professional_briefs`)
10. **Legal Aid Discovery & Privacy Consents**: `legal_aid_resources`, `consents`
11. **Audit Trails, Security & Background Jobs**: `audit_logs`, `security_events`, `processing_jobs`

### Key Model Capabilities:
- **8-State Document Ingestion Lifecycle**:
  `UPLOADED` $\rightarrow$ `QUARANTINED` $\rightarrow$ `SCANNING` $\rightarrow$ `PROCESSING` $\rightarrow$ `INDEXING` $\rightarrow$ `READY` (or `FAILED`) $\rightarrow$ `DELETED` (soft delete with `deleted_at`).
- **Official Indian Law Registry**:
  Strict statutory grounding (BNS 2023, BNSS 2023, CPA 2019, ICA 1872, MTA 2021). Zero fabricated authorities. Demo records explicitly tagged (`is_demo = True`, `[DEMO]` prefix).
- **Anti-IDOR / Anti-BOLA Boundaries**:
  External UUID exposure (`uuid`), dual composite checks (`WHERE id = :id AND user_id = :current_user_id`).
- **Database Migrations & Test Suite**:
  ```bash
  # Run Alembic migrations
  cd backend
  alembic upgrade head

  # Run database test suite (5 suites covering isolation, constraints, cascades, versioning, seeds)
  pytest tests/test_database_models.py -v
  ```

---

## 🧪 Automated Test Verification

The test suite validates:
- `test_database_models.py`: Multi-tenant isolation (User B cannot see User A's data), check constraints (email uniqueness, positive page numbers, status enums, effective date ranges), cascading deletions, document versioning and soft-delete filtering, and official Indian statutory seed data grounding.
- `test_security.py`: Magic byte signature validation, rejection of fake PDFs, prompt-injection stripping, Indian PII redaction, object-level authorization (User B cannot access User A's data).
- `test_document_parser.py`: Text extraction, boundary preservation, and semantic chunking.
- `test_analysis.py`: Clause categorization, plain English & Hindi summaries, 18% late fee & 90-day deposit risk detection.
- `test_comparison.py`: Comparative diff between standard and harsh lease with Risk Delta verdict.
- `test_verification.py`: Claim verification engine covering `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONFLICTING`, and `UNVERIFIED` states.
- `test_qa.py`: Grounded citations with exact page numbers and quotes; anti-hallucination fallback for absent queries.
- `test_brief.py`: Citizen legal consultation brief generation and markdown export.
- `test_legal_aid.py`: Section 12 free legal aid statutory eligibility screener and Anglo-Indian legal glossary search.

---

## ⚖️ Legal Safety Statement
*Nyaya Rakshak is built for informational clarity, evidence-grounded document understanding, and citizen legal literacy in India. It does not provide legal advice, establish an attorney-client relationship, or substitute for consultation with a qualified advocate enrolled with the Bar Council.*

import io
import os

import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.file_security import (
    detect_malicious_content,
    generate_secure_storage_name,
    sanitize_filename,
    secure_delete_file,
    validate_file_magic_and_mime,
)
from app.services.document_parser import (
    chunk_document_with_provenance,
)
from app.services.ocr_service import extract_image_ocr_layout, is_scanned_page


def test_sanitize_filename():
    assert sanitize_filename("../../malicious/path.pdf") == "path.pdf"
    assert sanitize_filename("..\\..\\windows\\system32\\evil.docx") in [
        "evil.docx",
        "windowssystem32evil.docx",
    ]
    assert sanitize_filename("safe document 123.pdf") == "safe_document_123.pdf"


def test_generate_secure_storage_name():
    name1 = generate_secure_storage_name("doc", ".pdf")
    name2 = generate_secure_storage_name("doc", ".pdf")
    assert name1 != name2
    assert name1.endswith(".pdf")
    assert len(name1) > 20


def test_detect_malicious_executables():
    # PE Header (MZ)
    pe_content = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100
    is_threat, reason = detect_malicious_content(pe_content, ".pdf")
    assert is_threat is True
    assert "executable" in reason.lower()

    # ELF Header
    elf_content = b"\x7fELF" + b"\x00" * 100
    is_threat, reason = detect_malicious_content(elf_content, ".pdf")
    assert is_threat is True
    assert "linux" in reason.lower()

    # Mach-O Header
    macho_content = b"\xcf\xfa\xed\xfe" + b"\x00" * 100
    is_threat, reason = detect_malicious_content(macho_content, ".pdf")
    assert is_threat is True

    # Safe PDF
    safe_pdf = b"%PDF-1.7 safe text content" + b"\x00" * 50
    is_threat, _ = detect_malicious_content(safe_pdf, ".pdf")
    assert is_threat is False


def test_validate_file_magic_and_mime():
    # PDF
    assert validate_file_magic_and_mime(b"%PDF-1.4...", "doc.pdf") == "pdf"

    # TXT
    assert validate_file_magic_and_mime(b"Simple plain text", "doc.txt") == "txt"

    # Valid PNG created via Pillow
    png_img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    png_buf = io.BytesIO()
    png_img.save(png_buf, format="PNG")
    assert validate_file_magic_and_mime(png_buf.getvalue(), "scan.png") == "png"

    # Valid JPG created via Pillow
    jpg_img = Image.new("RGB", (10, 10), color=(255, 255, 255))
    jpg_buf = io.BytesIO()
    jpg_img.save(jpg_buf, format="JPEG")
    assert validate_file_magic_and_mime(jpg_buf.getvalue(), "scan.jpg") == "jpg"

    # Disallowed extension
    with pytest.raises(Exception):
        validate_file_magic_and_mime(b"echo 'evil'", "script.sh")

    # Mismatched signature (fake PDF containing plain text)
    with pytest.raises(Exception):
        validate_file_magic_and_mime(b"Not a real pdf at all", "fake.pdf")


def test_ocr_and_scanned_page_heuristic():
    # Create synthetic test image
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    result = extract_image_ocr_layout(img_bytes, page_number=1)
    assert "boxes" in result
    assert result["confidence"] > 0.0

    # Scanned page check
    assert is_scanned_page(text="") is True
    assert is_scanned_page(text="Short") is True
    assert is_scanned_page(text="A" * 100) is False


def test_chunk_provenance():
    pages = [
        {
            "page_number": 1,
            "clean_text": "Section 1. Agreement terms.\n\nSection 2. Financial payment obligations.",
        }
    ]
    chunks = chunk_document_with_provenance(
        pages=pages, sections=[], content_hash="abc123hash", document_id=1, version_id=1
    )
    assert len(chunks) >= 1
    c = chunks[0]
    assert c["document_id"] == 1
    assert c["version_id"] == 1
    assert c["content_hash"] == "abc123hash"
    assert c["page_number"] == 1


def test_secure_delete_file(tmp_path):
    test_file = tmp_path / "temp_to_delete.txt"
    test_file.write_text("Confidential legal content to be securely erased.")
    assert os.path.exists(test_file)

    deleted = secure_delete_file(str(test_file))
    assert deleted is True
    assert not os.path.exists(test_file)


# =====================================================================
# API Integration Ingestion Security Tests
# =====================================================================


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_extension(client: AsyncClient, auth_headers: dict):
    files = {"file": ("malicious.exe", b"MZ\x90\x00...", "application/x-msdownload")}
    resp = await client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
    assert resp.status_code in [400, 422]


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client: AsyncClient, auth_headers: dict):
    # 16 MB dummy content
    oversized = b"%PDF-1.4 " + b"0" * (16 * 1024 * 1024)
    files = {"file": ("big.pdf", oversized, "application/pdf")}
    resp = await client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
    assert resp.status_code == 400
    assert "exceeds maximum limit" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_valid_pdf_and_check_status(client: AsyncClient, auth_headers: dict):
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer << /Size 4 /Root 1 0 R >>\nstartxref\n150\n%%EOF\n"
    )
    files = {"file": ("contract.pdf", pdf_content, "application/pdf")}
    resp = await client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    doc_id = data["id"]
    assert data["status"] in ["PROCESSING", "READY", "INDEXING"]

    # Poll status endpoint
    status_resp = await client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "status" in status_data
    assert status_data["id"] == doc_id

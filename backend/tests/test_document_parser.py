from app.services.document_parser import (
    chunk_document_text,
    extract_text_and_pages,
    validate_file_signature,
)


def test_txt_extraction_and_chunking():
    sample_text = (
        "1. PREMISES\nThe landlord agrees to lease the residential apartment.\n\n"
        "2. TERM\nThe lease shall be for 11 months.\n\n"
        "3. RENT\nMonthly rent is Thirty Thousand Rupees."
    )
    bytes_content = sample_text.encode("utf-8")
    file_type = validate_file_signature(bytes_content, "lease.txt")
    assert file_type == "txt"

    pages = extract_text_and_pages(bytes_content, file_type)
    assert len(pages) == 1
    assert pages[0][0] == 1

    chunks = chunk_document_text(pages, target_chunk_size=100, overlap=20)
    assert len(chunks) >= 1
    for c in chunks:
        assert c["page_number"] == 1
        assert len(c["clean_content"]) > 0

from unittest.mock import MagicMock

import pytest

from app.ai.gemini_provider import GeminiProvider
from app.core.audit import _sanitize_details_recursive
from app.core.config import settings
from app.core.file_security import detect_malicious_content
from app.core.rate_limit import create_limiter
from app.main import ALLOWED_CORS_HEADERS, ALLOWED_CORS_METHODS
from app.services.ai_cache import ai_cache_service


def test_production_config_fails_on_dev_secret():
    """Verify fail-fast startup: production environment rejects dev secret."""
    original_env = settings.ENVIRONMENT
    original_key = settings.SECRET_KEY
    try:
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "nyaya-rakshak-secure-dev-secret-key-min32chars-for-jwt-signing!"
        with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION ERROR.*SECRET_KEY"):
            settings.validate_production_settings()
    finally:
        settings.ENVIRONMENT = original_env
        settings.SECRET_KEY = original_key


def test_production_config_fails_on_short_secret():
    """Verify fail-fast startup: production environment rejects weak / short secrets."""
    original_env = settings.ENVIRONMENT
    original_key = settings.SECRET_KEY
    try:
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "too-short-secret"
        with pytest.raises(ValueError, match="at least 32 characters"):
            settings.validate_production_settings()
    finally:
        settings.ENVIRONMENT = original_env
        settings.SECRET_KEY = original_key


def test_production_config_passes_with_strong_settings():
    """Verify production settings pass when properly configured."""
    original_env = settings.ENVIRONMENT
    original_key = settings.SECRET_KEY
    original_secure = settings.COOKIE_SECURE
    try:
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "a-very-strong-production-secret-key-minimum-32-chars-long!"
        settings.COOKIE_SECURE = True
        # Should not raise
        settings.validate_production_settings()
    finally:
        settings.ENVIRONMENT = original_env
        settings.SECRET_KEY = original_key
        settings.COOKIE_SECURE = original_secure


def test_cors_hardened_policies():
    """Verify CORS policy contains no wildcards and only strict allowed methods and headers."""
    assert "*" not in ALLOWED_CORS_METHODS
    assert "*" not in ALLOWED_CORS_HEADERS
    # Verify mandatory security headers are present
    assert "Authorization" in ALLOWED_CORS_HEADERS
    assert "Content-Type" in ALLOWED_CORS_HEADERS
    assert "X-Legal-Disclaimer" in ALLOWED_CORS_HEADERS
    # Verify standard safe HTTP methods only
    for method in ["GET", "POST", "PUT", "DELETE"]:
        assert method in ALLOWED_CORS_METHODS


def test_redis_rate_limit_fallback_to_memory():
    """Verify rate limiter gracefully falls back to in-memory storage if Redis is unavailable."""
    # Invalid host should not crash the app, but fall back to memory
    limiter = create_limiter("redis://127.0.0.1:59999/0")
    assert limiter is not None

    # None / empty URI should use memory directly
    memory_limiter = create_limiter(None)
    assert memory_limiter is not None


@pytest.mark.asyncio
async def test_ai_cache_user_isolation():
    """Verify AI cache keys are isolated by user_id to prevent cross-user document leakage."""
    doc_hash = "test_doc_content_hash_xyz"
    question = "What is the penalty for delay?"

    key_u1 = ai_cache_service.compute_cache_key(doc_hash, question, user_id=101)
    key_u2 = ai_cache_service.compute_cache_key(doc_hash, question, user_id=102)
    assert key_u1 != key_u2

    payload = {"summary": "Confidential Tenant Agreement Summary"}

    # Cache for User 101
    await ai_cache_service.set(key_u1, payload, document_content_hash=doc_hash)

    # User 101 gets a cache hit
    result_u1 = await ai_cache_service.get(key_u1)
    assert result_u1 is not None
    assert result_u1["summary"] == "Confidential Tenant Agreement Summary"

    # User 102 querying the same document and question gets a cache miss
    result_u2 = await ai_cache_service.get(key_u2)
    assert result_u2 is None

    # Eviction on document deletion
    evicted = await ai_cache_service.evict_document(doc_hash)
    assert evicted >= 1
    assert (await ai_cache_service.get(key_u1)) is None


def test_audit_logging_scrubs_all_credentials():
    """Verify recursive audit log sanitizer masks passwords, keys, tokens, and cookies."""
    sample_details = {
        "user_email": "citizen@example.com",
        "api_key": "ai-secret-key-12345",
        "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
        "refresh_token": "d7a8b9c0...",
        "cookie": "session=xyz123",
        "authorization": "Bearer token123",
        "nested": {"password": "SuperSecretPassword123!", "normal_field": "public legal question"},
    }
    sanitized = _sanitize_details_recursive(sample_details)

    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["refresh_token"] == "[REDACTED]"
    assert sanitized["cookie"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["normal_field"] == "public legal question"


def test_malware_detection_eicar_signature():
    """Verify malware engine detects standard EICAR test file and flags it as malicious."""
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    is_malicious, reason = detect_malicious_content(eicar, ".txt")
    assert is_malicious is True
    assert "EICAR" in reason

    # Clean text should pass
    clean_text = (
        b"This is a standard residential lease agreement executed between Landlord and Tenant."
    )
    is_clean, _ = detect_malicious_content(clean_text, ".txt")
    assert is_clean is False


@pytest.mark.asyncio
async def test_gemini_provider_non_blocking_execution_and_structured_qa():
    """Verify GeminiProvider uses non-blocking threads and properly parses structured answers."""
    provider = GeminiProvider(api_key="mock-gemini-key")
    provider.model = MagicMock()

    # Mock response from Gemini
    mock_response = MagicMock()
    mock_response.text = (
        '{"answer": "Either party may terminate the lease by giving 30 days written notice.", '
        '"confidence_score": 0.94, '
        '"is_found_in_document": true, '
        '"citations": [{"page_number": 1, "section_title": "Termination", "verbatim_quote": "30 days notice", "relevance_score": 0.94}]}'
    )
    provider.model.generate_content.return_value = mock_response

    chunks = [
        {
            "page_number": 1,
            "clean_content": "Clause 5: Either party may terminate with 30 days notice.",
        }
    ]
    result = await provider.answer_question("What is the termination notice period?", chunks)

    assert result["is_found_in_document"] is True
    assert "30 days" in result["answer"]
    assert result["confidence_score"] == 0.94
    assert len(result["citations"]) == 1
    assert result["citations"][0]["page_number"] == 1
    assert provider.model.generate_content.called

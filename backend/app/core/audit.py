import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.pii_sanitizer import sanitize_pii

# Structured logger for security audit events
audit_logger = logging.getLogger("nyaya_rakshak.audit")
audit_logger.setLevel(logging.INFO)

# Handler if none exists
if not audit_logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    ch.setFormatter(formatter)
    audit_logger.addHandler(ch)


def _sanitize_details_recursive(obj: Any) -> Any:
    """Recursively scrub secrets and Indian PII from log detail dictionaries."""
    if isinstance(obj, dict):
        cleaned = {}
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "auth",
            "credential",
            "raw_text",
            "content",
            "api_key",
            "key",
            "authorization",
            "cookie",
            "access_token",
            "refresh_token",
            "bearer",
            "private_key",
        ]
        for k, v in obj.items():
            if any(s in k.lower() for s in sensitive_patterns):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = _sanitize_details_recursive(v)
        return cleaned
    elif isinstance(obj, list):
        return [_sanitize_details_recursive(item) for item in obj]
    elif isinstance(obj, str):
        sanitized_str, _ = sanitize_pii(obj)
        return sanitized_str
    return obj


def log_audit_event(
    action: str,
    user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[Any] = None,
    ip_address: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None,
):
    """
    Log security-sensitive audit event.
    CRITICAL: Never include raw document contents, secrets, or unmasked PII.
    Outputs strict, valid JSON.
    """
    safe_details = _sanitize_details_recursive(details or {})

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user_id": user_id,
        "target_type": target_type,
        "target_id": str(target_id) if target_id is not None else None,
        "ip_address": ip_address,
        "status": status,
        "details": safe_details,
    }
    audit_logger.info(json.dumps(event, default=str))

import re
from typing import Dict, Tuple

# Indian PII regex patterns
AADHAAR_PATTERN = re.compile(r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
PHONE_PATTERN = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
BANK_ACC_PATTERN = re.compile(r"(?:Account|A/C)\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d{9,18})", re.IGNORECASE)

def sanitize_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Sanitize sensitive Indian Personally Identifiable Information (PII).
    Returns (sanitized_text, counts_of_redactions).
    """
    stats = {
        "aadhaar": 0,
        "pan": 0,
        "phone": 0,
        "email": 0,
        "ifsc": 0,
        "bank_account": 0
    }

    # Count and redact Aadhaar
    aadhaar_matches = AADHAAR_PATTERN.findall(text)
    stats["aadhaar"] = len(aadhaar_matches)
    text = AADHAAR_PATTERN.sub("[AADHAAR_REDACTED]", text)

    # Count and redact PAN
    pan_matches = PAN_PATTERN.findall(text)
    stats["pan"] = len(pan_matches)
    text = PAN_PATTERN.sub("[PAN_REDACTED]", text)

    # Count and redact Phone
    phone_matches = PHONE_PATTERN.findall(text)
    stats["phone"] = len(phone_matches)
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)

    # Count and redact Email
    email_matches = EMAIL_PATTERN.findall(text)
    stats["email"] = len(email_matches)
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)

    # Count and redact IFSC
    ifsc_matches = IFSC_PATTERN.findall(text)
    stats["ifsc"] = len(ifsc_matches)
    text = IFSC_PATTERN.sub("[IFSC_REDACTED]", text)

    # Count and redact Bank Account Numbers
    def redact_acc(match):
        stats["bank_account"] += 1
        return "Account No: [ACCOUNT_REDACTED]"
    text = BANK_ACC_PATTERN.sub(redact_acc, text)

    return text, stats

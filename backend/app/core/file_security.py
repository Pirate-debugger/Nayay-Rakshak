import io
import os
import re
import uuid
import zipfile
from typing import Tuple

from PIL import Image

from app.core.config import settings
from app.core.exceptions import FileIntegrityError, SecurityValidationError

# Magic bytes signatures
PDF_MAGIC = b"%PDF-"
DOCX_MAGIC = b"PK\x03\x04"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

# Executable / binary headers that must NEVER appear in uploaded documents
EXECUTABLE_SIGNATURES = [
    (b"MZ", "Windows PE executable (EXE/DLL)"),
    (b"\x7fELF", "Linux ELF binary"),
    (b"\xca\xfe\xba\xbe", "Mach-O / Java bytecode binary"),
    (b"\xce\xfa\xed\xfe", "Mach-O 32-bit binary"),
    (b"\xcf\xfa\xed\xfe", "Mach-O 64-bit binary"),
]

# Decompression bomb threshold (25 megapixels)
Image.MAX_IMAGE_PIXELS = 25_000_000


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename against path traversal, null bytes, and control characters.
    Extracts only the safe base name without directory components.
    """
    if not filename:
        return f"document_{uuid.uuid4().hex[:8]}.txt"

    # Strip directory paths
    base = os.path.basename(filename)
    # Remove null bytes and control chars
    base = base.replace("\x00", "").strip()
    # Strip any remaining path traversal sequences
    base = re.sub(r"\.\.+[/\\ ]*", "", base)
    # Remove characters outside alphanumerics, underscores, hyphens, and single periods
    base = re.sub(r"[^a-zA-Z0-9_\.-]", "_", base)
    # Eliminate multiple consecutive dots
    base = re.sub(r"\.{2,}", ".", base)

    if not base or base.startswith("."):
        base = f"document_{uuid.uuid4().hex[:8]}" + (base if base.startswith(".") else ".txt")

    return base


def generate_secure_storage_name(prefix: str, extension: str) -> str:
    """Generate a collision-resistant, randomized storage identifier."""
    clean_ext = extension if extension.startswith(".") else f".{extension}"
    return f"{prefix}_{uuid.uuid4().hex}{clean_ext}"


EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def scan_with_clamav_socket(
    file_bytes: bytes, host: str, port: int, timeout: float = 2.0
) -> Tuple[bool, str]:
    """
    Query ClamAV daemon using standard INSTREAM protocol over TCP socket.
    Returns (is_infected, message).
    """
    try:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            s.sendall(b"zINSTREAM\x00")

            chunk_size = 2048
            for i in range(0, len(file_bytes), chunk_size):
                chunk = file_bytes[i : i + chunk_size]
                chunk_len = len(chunk).to_bytes(4, byteorder="big")
                s.sendall(chunk_len + chunk)
            s.sendall(b"\x00\x00\x00\x00")

            response = s.recv(1024)
            if b"FOUND" in response:
                result_str = response.decode("utf-8", errors="replace").strip()
                return True, f"ClamAV Antivirus signature detected: {result_str}"
            elif b"OK" in response:
                return False, ""
            return False, ""
    except Exception as e:
        return False, f"CLAMAV_UNAVAILABLE: {str(e)}"


def scan_with_malware_engine(file_bytes: bytes, filename: str) -> Tuple[bool, str]:
    """
    Multi-engine malware inspection for untrusted legal documents.
    1. Built-in EICAR standard anti-virus signature detection.
    2. Configurable ClamAV daemon scan with fail-closed production mode.
    """
    import logging

    _logger = logging.getLogger("nyaya_rakshak.malware_scan")

    # 1. Built-in EICAR signature verification
    if EICAR_SIGNATURE in file_bytes:
        return True, "EICAR standard anti-virus test signature detected in document stream."

    # 2. Configurable ClamAV daemon
    if settings.ENABLE_CLAMAV_SCAN:
        is_infected, msg = scan_with_clamav_socket(
            file_bytes, settings.CLAMAV_HOST, settings.CLAMAV_PORT
        )
        if is_infected:
            return True, msg
        if "CLAMAV_UNAVAILABLE" in msg:
            if settings.CLAMAV_REQUIRED:
                raise SecurityValidationError(
                    f"Production security violation: Antivirus scanner is unreachable ({msg})."
                )
            _logger.warning(
                f"ClamAV scanner unavailable ({msg}); proceeding with built-in heuristic signature detection."
            )

    return False, ""


def detect_malicious_content(file_bytes: bytes, ext: str) -> Tuple[bool, str]:
    """
    Inspect raw binary stream for embedded executables, Office macros, zip-slips, decompression bombs, or malware.
    Returns (is_malicious, description).
    """
    if not file_bytes:
        return True, "File is completely empty (0 bytes)."

    # 0. Anti-virus & EICAR test signature detection
    is_infected, msg = scan_with_malware_engine(file_bytes, ext)
    if is_infected:
        return True, msg

    # 1. Check for raw executable headers
    for sig, desc in EXECUTABLE_SIGNATURES:
        if file_bytes.startswith(sig):
            return True, f"Disguised binary executable detected: {desc}"

    # 2. Inspect DOCX zip archive for macros or zip-slip
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zf:
                for entry in zf.namelist():
                    # Check for path traversal inside zip archive (Zip Slip)
                    if ".." in entry or entry.startswith("/") or entry.startswith("\\"):
                        return True, "Malicious zip-slip path traversal entry detected inside DOCX."
                    # Check for Word VBA macros
                    lower_entry = entry.lower()
                    if lower_entry.endswith(".bin") and "vba" in lower_entry:
                        return True, "Malicious embedded VBA macros detected in Word document."
        except zipfile.BadZipFile:
            return True, "Corrupted or non-standard DOCX archive."

    # 3. Inspect images for pixel bombs or payload tampering
    if ext in (".png", ".jpg", ".jpeg"):
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()
        except Image.DecompressionBombError:
            return (
                True,
                "Image exceeds safe decompression thresholds (potential decompression bomb).",
            )
        except Exception as e:
            return True, f"Corrupted or invalid image format: {str(e)}"

    return False, ""


def validate_file_magic_and_mime(file_bytes: bytes, filename: str) -> str:
    """
    Validate file size, extension, magic bytes, and absence of malicious content.
    Returns the normalized canonical file_type ('pdf', 'docx', 'txt', 'png', 'jpg').
    Fail-closed: raises SecurityValidationError or FileIntegrityError on any mismatch.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise SecurityValidationError("File is empty (0 bytes). Upload a valid legal document.")

    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise SecurityValidationError(
            f"File size ({len(file_bytes)} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes (15 MB)."
        )

    safe_name = sanitize_filename(filename)
    ext = os.path.splitext(safe_name.lower())[1]

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise SecurityValidationError(
            f"File extension '{ext}' is not permitted. Supported formats: {settings.ALLOWED_EXTENSIONS}"
        )

    # Perform deep malicious payload scan (executables, macros, zip-slip, image bombs)
    is_malicious, reason = detect_malicious_content(file_bytes, ext)
    if is_malicious:
        raise SecurityValidationError(f"Security validation failed: {reason}")

    # Antivirus / Malware signature scan (EICAR & ClamAV)
    is_malware, malware_reason = scan_with_malware_engine(file_bytes, safe_name)
    if is_malware:
        raise SecurityValidationError(f"Security validation failed: {malware_reason}")

    # Validate exact magic bytes per extension
    if ext == ".pdf":
        if not file_bytes.startswith(PDF_MAGIC):
            raise FileIntegrityError(
                "File claims to be a PDF but magic byte signature (%PDF-) is missing or forged."
            )
        return "pdf"

    elif ext == ".docx":
        if not file_bytes.startswith(DOCX_MAGIC):
            raise FileIntegrityError(
                "File claims to be a DOCX document but ZIP magic signature is invalid or forged."
            )
        return "docx"

    elif ext == ".txt":
        if b"\x00" in file_bytes[:2048]:
            raise FileIntegrityError("File claims to be plain text but contains binary/null bytes.")
        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                file_bytes.decode("latin-1")
            except Exception:
                raise FileIntegrityError("File encoding could not be verified as valid text.")
        return "txt"

    elif ext == ".png":
        if not file_bytes.startswith(PNG_MAGIC):
            raise FileIntegrityError(
                "File claims to be a PNG image but magic byte signature is invalid or forged."
            )
        return "png"

    elif ext in (".jpg", ".jpeg"):
        if not file_bytes.startswith(JPEG_MAGIC):
            raise FileIntegrityError(
                "File claims to be a JPEG image but magic byte signature is invalid or forged."
            )
        return "jpg"

    raise SecurityValidationError(f"Unsupported file type: {ext}")


def secure_delete_file(file_path: str) -> bool:
    """
    Securely delete a file from physical disk by overwriting with zeros before unlinking.
    Prevents forensic recovery of sensitive legal documents from unallocated disk clusters.
    """
    if not file_path:
        return False
    try:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 0:
                with open(file_path, "wb") as f:
                    f.write(b"\x00" * file_size)
                    f.flush()
                    os.fsync(f.fileno())
            os.remove(file_path)
            return True
    except Exception:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
    return False

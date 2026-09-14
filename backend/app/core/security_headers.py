from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production-grade HTTP Security Headers Middleware.
    Enforces strict browser sandboxing, anti-framing, HSTS, and CSP without weakening protections.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # 1. Content Security Policy (CSP)
        # Prevents XSS, packet injection, and unauthorized scripts
        csp_directives = [
            "default-src 'self'",
            "img-src 'self' data:",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "frame-ancestors 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # 2. Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 3. Prevent clickjacking / framing
        response.headers["X-Frame-Options"] = "DENY"

        # 4. Strict Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Disable unused browser device APIs
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"

        # 6. Modern XSS filter setting (0 to prevent XS-Search side channels)
        response.headers["X-XSS-Protection"] = "0"

        # 7. HTTP Strict Transport Security (HSTS) in production or HTTPS
        if settings.ENVIRONMENT == "production" or request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # 8. Mandatory Legal Educational Disclaimer Header
        response.headers["X-Legal-Disclaimer"] = "Nyaya-Rakshak-Educational-Only-Not-Legal-Advice"

        return response

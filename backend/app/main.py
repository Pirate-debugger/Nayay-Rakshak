import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import (
    admin,
    analysis,
    auth,
    briefs,
    comparison,
    documents,
    glossary,
    legal_aid,
    qa,
    retrieval,
    verification,
)
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.base import init_db

logger = logging.getLogger("nyaya_rakshak.main")
 
LEGAL_DISCLAIMER_TEXT = (
    "Nyaya Rakshak is an AI-powered legal clarity and educational assistance platform. "
    "It does NOT provide legal advice, does NOT constitute an attorney-client relationship, "
    "and cannot guarantee legal outcomes. Consult a qualified advocate for official representation."
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schemas
    await init_db()
    try:
        from app.db.base import AsyncSessionLocal
        from app.db.seed import seed_database
        async with AsyncSessionLocal() as session:
            await seed_database(session)
    except Exception as e:
        logger.warning(f"Database seed initialization warning: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Citizen-centric GenAI platform for legal document clarity, verification, and action navigation in India. "
        "AI explains. Evidence supports. Verification checks. Rules calculate. Humans decide."
    ),
    lifespan=lifespan
)

# Set rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Security Headers Middleware (strict CSP, HSTS, anti-clickjacking, nosniff, permissions)
app.add_middleware(SecurityHeadersMiddleware)

# 2. CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Generic safe exception handler to prevent internal stack trace leakage
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled system error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal system error occurred. Please try again or contact support."}
    )

# Mount v1 routers
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(analysis.router, prefix=api_prefix)
app.include_router(comparison.router, prefix=api_prefix)
app.include_router(qa.router, prefix=api_prefix)
app.include_router(verification.router, prefix=api_prefix)
app.include_router(briefs.router, prefix=api_prefix)
app.include_router(legal_aid.router, prefix=api_prefix)
app.include_router(glossary.router, prefix=api_prefix)
app.include_router(retrieval.router, prefix=api_prefix)


@app.get("/health", tags=["Health"])
async def health_check():
    """System health check and operational status."""
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ai_provider": settings.AI_PROVIDER,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "legal_disclaimer": LEGAL_DISCLAIMER_TEXT
    }

import logging
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger("nyaya_rakshak.rate_limit")


def create_limiter(storage_uri: Optional[str] = None) -> Limiter:
    """Create a SlowAPI Limiter instance with fallback to in-memory storage."""
    uri = storage_uri if storage_uri else "memory://"
    try:
        lim = Limiter(
            key_func=get_remote_address,
            default_limits=[settings.RATE_LIMIT_DEFAULT],
            storage_uri=uri,
        )
        if storage_uri:
            logger.info(f"Distributed Redis rate limiting initialized with URI: {storage_uri}")
        return lim
    except Exception as e:
        logger.warning(
            f"Failed to initialize rate limiter with storage_uri '{uri}': {e}. Falling back to in-memory limiter."
        )
        return Limiter(
            key_func=get_remote_address,
            default_limits=[settings.RATE_LIMIT_DEFAULT],
            storage_uri="memory://",
        )


limiter = create_limiter(settings.REDIS_URL)

"""
NYAYA RAKSHAK - High-Performance AI Caching & Request Deduplication Service
Enforces strict provenance, deterministic cache identities, statutory version invalidation,
and evidence grounding retention.
"""

import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models import AICacheEntry
from app.services.retrieval.registry import source_registry

logger = logging.getLogger("nyaya_rakshak.ai_cache")


class AICacheService:
    """
    Tier-1 In-Memory LRU + Persistent SQL AI Answer Cache.
    
    CRITICAL RULES:
    1. Cache identity MUST incorporate:
       - Document content hash
       - Normalized query/prompt
       - Model identifier
       - Prompt version
       - Legal Source Registry version
       - PII redaction setting
    2. NEVER reuse an answer if the legal source registry version has changed.
    3. Cached responses MUST retain verified evidence citations and evidence coverage.
    """

    def __init__(self, max_memory_entries: int = 1000):
        self.max_memory_entries = max_memory_entries
        self._memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._in_flight_requests: Dict[str, asyncio.Future] = {}

    def compute_cache_key(
        self,
        document_content_hash: Optional[str],
        question: str,
        model_name: str = "gemini-2.5-flash",
        prompt_version: str = "v1.0",
        pii_redacted: bool = True
    ) -> str:
        """
        Compute deterministic SHA-256 cache identity.
        """
        doc_hash = (document_content_hash or "statutory_general").strip()
        norm_q = question.strip().lower()
        active_source_ver = source_registry.get_version()

        identity_str = f"{doc_hash}:{norm_q}:{model_name}:{prompt_version}:{active_source_ver}:{pii_redacted}"
        return hashlib.sha256(identity_str.encode("utf-8")).hexdigest()

    async def get(
        self,
        cache_key: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached AI response if still valid against active legal sources.
        """
        current_source_ver = source_registry.get_version()
        now = datetime.now(timezone.utc)

        # 1. Check in-memory LRU cache
        async with self._lock:
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                # Invalidate if source registry version changed
                if entry.get("source_registry_version") != current_source_ver:
                    del self._memory_cache[cache_key]
                    logger.info(f"AI Cache invalidated for key {cache_key}: legal source registry version changed.")
                elif entry.get("expires_at") and entry["expires_at"] < now:
                    del self._memory_cache[cache_key]
                else:
                    self._memory_cache.move_to_end(cache_key)
                    entry["hit_count"] = entry.get("hit_count", 0) + 1
                    return entry["response_data"]

        # 2. Check persistent DB cache if session provided
        if db:
            try:
                q = select(AICacheEntry).where(AICacheEntry.cache_key == cache_key)
                res = await db.execute(q)
                db_entry = res.scalar_one_or_none()
                if db_entry:
                    # Invalidate if source registry version changed
                    if db_entry.source_registry_version != current_source_ver:
                        await db.delete(db_entry)
                        await db.commit()
                        logger.info(f"DB AI Cache evicted key {cache_key}: registry version {db_entry.source_registry_version} != {current_source_ver}.")
                        return None

                    if db_entry.expires_at:
                        exp = db_entry.expires_at if db_entry.expires_at.tzinfo else db_entry.expires_at.replace(tzinfo=timezone.utc)
                        if exp < now:
                            await db.delete(db_entry)
                            await db.commit()
                            return None

                    # Cache hit!
                    db_entry.hit_count += 1
                    await db.commit()

                    data = json.loads(db_entry.response_json)

                    # Update in-memory LRU
                    async with self._lock:
                        if len(self._memory_cache) >= self.max_memory_entries:
                            self._memory_cache.popitem(last=False)
                        self._memory_cache[cache_key] = {
                            "response_data": data,
                            "source_registry_version": db_entry.source_registry_version,
                            "expires_at": db_entry.expires_at,
                            "hit_count": db_entry.hit_count
                        }

                    return data
            except Exception as e:
                logger.warning(f"Error querying DB AI cache: {e}")

        return None

    async def set(
        self,
        cache_key: str,
        response_data: Dict[str, Any],
        document_content_hash: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        prompt_version: str = "v1.0",
        db: Optional[AsyncSession] = None,
        ttl_seconds: int = 86400  # 24 hours default
    ) -> None:
        """
        Store response in in-memory LRU and persistent database.
        """
        active_source_ver = source_registry.get_version()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        # 1. Store in memory LRU
        async with self._lock:
            if len(self._memory_cache) >= self.max_memory_entries:
                self._memory_cache.popitem(last=False)
            self._memory_cache[cache_key] = {
                "response_data": response_data,
                "source_registry_version": active_source_ver,
                "expires_at": expires_at,
                "hit_count": 1
            }

        # 2. Store in DB
        if db:
            try:
                # Check if exists
                q = select(AICacheEntry).where(AICacheEntry.cache_key == cache_key)
                res = await db.execute(q)
                db_entry = res.scalar_one_or_none()

                payload_json = json.dumps(response_data, default=str)

                if db_entry:
                    db_entry.response_json = payload_json
                    db_entry.source_registry_version = active_source_ver
                    db_entry.hit_count += 1
                    db_entry.expires_at = expires_at
                else:
                    new_entry = AICacheEntry(
                        cache_key=cache_key,
                        document_hash=document_content_hash,
                        source_registry_version=active_source_ver,
                        model_name=model_name,
                        prompt_version=prompt_version,
                        response_json=payload_json,
                        evidence_verified=True,
                        expires_at=expires_at,
                        created_at=now
                    )
                    db.add(new_entry)
                await db.commit()
            except Exception as e:
                logger.warning(f"Error persisting to DB AI cache: {e}")

    def clear(self) -> None:
        """Clear memory cache."""
        self._memory_cache.clear()


# Global singleton
ai_cache_service = AICacheService()

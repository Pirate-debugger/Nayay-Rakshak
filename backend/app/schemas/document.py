from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    filename: str
    file_type: str
    file_size: int
    page_count: int
    pii_redacted: bool
    status: str = "READY"
    error_message: Optional[str] = None
    content_hash: Optional[str] = None
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    chunk_count: int
    preview_text: str


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    page_number: int
    section_title: Optional[str] = None
    content_hash: Optional[str] = None
    content: str
    clean_content: str


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    page_count: int
    error_message: Optional[str] = None
    content_hash: Optional[str] = None
    jobs: List[Dict[str, Any]] = []

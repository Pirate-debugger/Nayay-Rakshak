from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class BriefCreateRequest(BaseModel):
    document_id: int
    client_name: str
    specific_questions: Optional[List[str]] = None


class BriefResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    title: str
    client_name: str
    brief_markdown: str
    key_issues: List[str]
    questions_for_lawyer: List[str]
    created_at: datetime

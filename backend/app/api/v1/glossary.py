from typing import List, Optional

from fastapi import APIRouter, Query

from app.services.glossary_data import GlossaryEntry, search_glossary

router = APIRouter(prefix="/glossary", tags=["Legal Glossary"])


@router.get("/", response_model=List[GlossaryEntry])
async def get_legal_glossary(
    query: Optional[str] = Query(None, description="Search term in English or Hindi"),
):
    """
    Search Anglo-Indian legal dictionary with plain English & Hindi translations.
    """
    return search_glossary(query)

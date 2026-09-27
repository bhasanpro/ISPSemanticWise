"""
Glossary Routes - Business Glossary Management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

from isp_semantic_wise.config import get_settings, Settings

router = APIRouter()


# Request/Response Models
class BusinessTermBase(BaseModel):
    term: str = Field(..., min_length=1, max_length=255)
    synonyms: List[str] = []
    definition: str = ""
    category: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class BusinessTermCreate(BusinessTermBase):
    pass


class BusinessTermUpdate(BaseModel):
    synonyms: Optional[List[str]] = None
    definition: Optional[str] = None
    category: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class BusinessTermResponse(BusinessTermBase):
    id: UUID
    validated_by: Optional[str] = None
    validated_at: Optional[str] = None
    technical_mappings: List[dict] = []

    class Config:
        from_attributes = True


class TechnicalMappingCreate(BaseModel):
    technical_artifact_id: UUID
    mapping_type: str = "defines"
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    transformation_logic: str = ""
    business_rule: str = ""


class GlossarySearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class GlossaryGenerateRequest(BaseModel):
    source_system: str = Field(..., description="Source system to generate from")
    source_path: Optional[str] = None
    batch_size: int = Field(default=20, ge=1, le=100)


@router.get("/terms", response_model=List[BusinessTermResponse])
async def list_terms(
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
):
    """List business terms with optional filtering"""
    # TODO: Implement database query
    return []


@router.get("/terms/{term_id}", response_model=BusinessTermResponse)
async def get_term(
    term_id: UUID,
    settings: Settings = Depends(get_settings),
):
    """Get a specific business term with mappings"""
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Term not found")


@router.post("/terms", response_model=BusinessTermResponse, status_code=201)
async def create_term(
    term: BusinessTermCreate,
    settings: Settings = Depends(get_settings),
):
    """Create a new business term"""
    # TODO: Implement database insert
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/terms/{term_id}", response_model=BusinessTermResponse)
async def update_term(
    term_id: UUID,
    term: BusinessTermUpdate,
    settings: Settings = Depends(get_settings),
):
    """Update a business term"""
    # TODO: Implement database update
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/terms/{term_id}", status_code=204)
async def delete_term(
    term_id: UUID,
    settings: Settings = Depends(get_settings),
):
    """Delete a business term"""
    # TODO: Implement database delete
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/terms/{term_id}/mappings", status_code=201)
async def add_mapping(
    term_id: UUID,
    mapping: TechnicalMappingCreate,
    settings: Settings = Depends(get_settings),
):
    """Add technical mapping to a business term"""
    # TODO: Implement mapping creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/generate", status_code=202)
async def generate_glossary(
    request: GlossaryGenerateRequest,
    settings: Settings = Depends(get_settings),
):
    """Generate glossary from source code (async job)"""
    # TODO: Trigger async glossary generation job
    return {"job_id": "generated", "status": "started"}


@router.post("/search", response_model=List[BusinessTermResponse])
async def search_terms(
    request: GlossarySearchRequest,
    settings: Settings = Depends(get_settings),
):
    """Semantic search for business terms"""
    # TODO: Implement semantic search
    return []


@router.get("/categories", response_model=List[str])
async def list_categories(settings: Settings = Depends(get_settings)):
    """List all categories"""
    return [
        "trade",
        "settlement",
        "counterparty",
        "risk",
        "reconciliation",
        "matching",
        "corporate_actions",
        "fees",
    ]


@router.get("/export")
async def export_glossary(
    format: str = Query(default="yaml", regex="^(yaml|json|csv)$"),
    settings: Settings = Depends(get_settings),
):
    """Export glossary in specified format"""
    # TODO: Implement export
    return {"message": f"Export in {format} format not implemented yet"}
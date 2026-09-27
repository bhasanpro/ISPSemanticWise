"""
Trade Match Debugger Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID

from isp_semantic_wise.config import get_settings, Settings

router = APIRouter()


class DebugTradeRequest(BaseModel):
    trade_id: str = Field(..., min_length=1)
    break_code: Optional[str] = None
    include_transformation_logic: bool = True
    max_depth: int = Field(default=10, ge=1, le=20)


class DebugTradeResponse(BaseModel):
    trade_id: str
    break_reason: Optional[str]
    lineage_trace: List[Dict]
    mismatch_points: List[Dict]
    root_cause: str
    business_action: str
    confidence: float


class BreakCodeRequest(BaseModel):
    break_code: str
    counterparty: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)


class BreakCodeAnalysisResponse(BaseModel):
    break_code: str
    total_occurrences: int
    top_root_causes: List[Dict]
    affected_counterparties: List[str]
    trend: str


@router.post("/debug", response_model=DebugTradeResponse)
async def debug_trade(
    request: DebugTradeRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Debug a specific trade break
    
    Traces the full lineage from source through Ab Initio/Oracle/Unix
    to identify the exact mismatch point.
    """
    # TODO: Implement trade debugger
    # 1. Get trade from NetworkX graph
    # 2. Trace full lineage path
    # 3. Compare expected vs actual at each transformation
    # 4. Identify divergence point
    # 5. Generate business-language explanation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/break-codes/analyze", response_model=BreakCodeAnalysisResponse)
async def analyze_break_code(
    request: BreakCodeRequest,
    settings: Settings = Depends(get_settings),
):
    """Analyze a specific break code across trades"""
    # TODO: Implement break code analysis
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/break-codes", response_model=List[Dict])
async def list_break_codes(
    settings: Settings = Depends(get_settings),
):
    """List known break codes with descriptions"""
    # TODO: Load from glossary/database
    return [
        {"code": "SAMT", "description": "Settlement Amount Mismatch", "category": "amount"},
        {"code": "SDAT", "description": "Settlement Date Mismatch", "category": "date"},
        {"code": "CPID", "description": "Counterparty ID Mismatch", "category": "counterparty"},
        {"code": "TRDT", "description": "Trade Date Mismatch", "category": "date"},
        {"code": "QTYM", "description": "Quantity Mismatch", "category": "quantity"},
        {"code": "PRCM", "description": "Price Mismatch", "category": "amount"},
        {"code": "CURM", "description": "Currency Mismatch", "category": "currency"},
    ]


@router.get("/trades/{trade_id}/lineage", response_model=List[Dict])
async def get_trade_lineage(
    trade_id: str,
    settings: Settings = Depends(get_settings),
):
    """Get full lineage trace for a trade"""
    # TODO: Query NetworkX graph
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/compare", response_model=Dict)
async def compare_sources(
    trade_id: str,
    source_systems: List[str] = ["ab_initio", "oracle", "confirmation"],
    settings: Settings = Depends(get_settings),
):
    """Compare trade data across source systems"""
    # TODO: Implement multi-source comparison
    raise HTTPException(status_code=501, detail="Not implemented")
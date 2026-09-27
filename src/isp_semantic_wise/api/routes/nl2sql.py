"""
NL2SQL Routes - Natural Language to SQL Translation
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from isp_semantic_wise.config import get_settings, Settings

router = APIRouter()


class NL2SQLRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    include_lineage: bool = Field(default=True, description="Include lineage trace")
    validate_sql: bool = Field(default=True, description="Validate generated SQL")


class NL2SQLResponse(BaseModel):
    sql: str
    explanation: str
    lineage_trace: Optional[List[Dict]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    tables_used: List[str] = []
    columns_used: List[str] = []


class NL2SQLValidateRequest(BaseModel):
    sql: str


class NL2SQLValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class SchemaInfoRequest(BaseModel):
    tables: Optional[List[str]] = None


class SchemaInfoResponse(BaseModel):
    tables: Dict[str, List[Dict]]
    relationships: List[Dict]


@router.post("/generate", response_model=NL2SQLResponse)
async def generate_sql(
    request: NL2SQLRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Generate SQL from natural language question
    
    Example questions:
    - "Show all trades where settlement amount differs from confirmed amount for Goldman Sachs in January 2024"
    - "What's the total settlement amount by counterparty for last month?"
    - "Find trades with break code SAMT for the past week"
    """
    # TODO: Implement NL2SQL using Tier 1 model with tool calling
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/validate", response_model=NL2SQLValidateResponse)
async def validate_sql(
    request: NL2SQLValidateRequest,
    settings: Settings = Depends(get_settings),
):
    """Validate SQL syntax and semantics"""
    # TODO: Implement SQL validation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/schema", response_model=SchemaInfoResponse)
async def get_schema_info(
    request: SchemaInfoRequest,
    settings: Settings = Depends(get_settings),
):
    """Get database schema information for context"""
    # TODO: Return relevant schema information
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/examples", response_model=List[Dict[str, str]])
async def get_examples(
    category: Optional[str] = None,
    settings: Settings = Depends(get_settings),
):
    """Get example NL→SQL pairs for few-shot prompting"""
    examples = [
        {
            "question": "Show all trades where settlement amount differs from confirmed amount for Goldman Sachs in January 2024",
            "category": "reconciliation",
            "sql": "SELECT t.TRADE_ID, t.TRD_DT, r.SETT_AMT, c.CONF_AMT, (r.SETT_AMT - c.CONF_AMT) as DIFF FROM RECON_RESULTS r JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID JOIN CONFIRMATIONS c ON r.TRADE_ID = c.TRADE_ID WHERE t.CP_CD = 'GS' AND t.TRD_DT BETWEEN '2024-01-01' AND '2024-01-31' AND ABS(r.SETT_AMT - c.CONF_AMT) > 0.01"
        },
        {
            "question": "What's the total settlement amount by counterparty for last month?",
            "category": "aggregation",
            "sql": "SELECT t.CP_CD, SUM(r.SETT_AMT) as TOTAL_SETTLEMENT FROM RECON_RESULTS r JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID WHERE t.TRD_DT >= CURRENT_DATE - INTERVAL '1 month' GROUP BY t.CP_CD"
        },
        {
            "question": "Find trades with break code SAMT for the past week",
            "category": "break_analysis",
            "sql": "SELECT t.TRADE_ID, t.TRD_DT, t.CP_CD, r.BREAK_CODE FROM RECON_RESULTS r JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID WHERE r.BREAK_CODE = 'SAMT' AND t.TRD_DT >= CURRENT_DATE - INTERVAL '7 days'"
        },
    ]
    if category:
        return [e for e in examples if e["category"] == category]
    return examples
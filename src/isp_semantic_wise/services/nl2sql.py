"""
NL2SQL Translator - Natural Language to SQL with Lineage
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

from ..config import get_settings
from ..storage.vector import VectorStore
from ..storage.graph import GraphStore
from ..storage.relational import RelationalStore


@dataclass
class NL2SQLResult:
    sql: str
    explanation: str
    lineage_trace: List[Dict]
    confidence: float
    tables_used: List[str]
    columns_used: List[str]
    validation_errors: List[str]


class NL2SQLTranslator:
    """Translates natural language to SQL with lineage trace"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self.vector_store = None
        self.graph_store = None
        self.relational_store = None
        self.schema_cache = {}
    
    def set_stores(self, vector_store, graph_store, relational_store):
        """Set storage backends"""
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.relational_store = relational_store
    
    def translate(self, question: str, context: Dict = None) -> Dict:
        """
        Translate natural language to SQL
        
        Args:
            question: Natural language question
            context: Optional context (schema hints, user preferences)
            
        Returns:
            Dictionary with SQL, explanation, lineage, confidence
        """
        logger.info(f"Translating: {question[:100]}...")
        
        # Step 1: Intent classification
        intent = self._classify_intent(question)
        
        # Step 2: Entity extraction
        entities = self._extract_entities(question)
        
        # Step 3: Schema lookup
        relevant_schema = self._lookup_schema(entities)
        
        # Step 4: Generate SQL (using Tier 1 model with tool calling)
        sql_result = self._generate_sql(question, entities, relevant_schema)
        
        # Step 5: Validate SQL
        validation = self._validate_sql(sql_result["sql"])
        
        # Step 6: Get lineage trace
        lineage = self._get_lineage(sql_result["tables_used"], sql_result["columns_used"])
        
        return {
            "sql": sql_result["sql"],
            "explanation": sql_result["explanation"],
            "lineage_trace": lineage,
            "confidence": sql_result["confidence"],
            "tables_used": sql_result["tables_used"],
            "columns_used": sql_result["columns_used"],
            "validation_errors": validation["errors"],
            "validation_warnings": validation["warnings"],
        }
    
    def _classify_intent(self, question: str) -> Dict:
        """Classify query intent"""
        question_lower = question.lower()
        
        intent = {
            "type": "select",
            "aggregation": None,
            "filters": [],
            "group_by": False,
            "time_range": None,
        }
        
        q = question_lower
        
        # Determine operation type
        if any(kw in q for kw in ["count", "how many", "number of"]):
            intent["aggregation"] = "count"
        elif any(kw in q for kw in ["sum", "total", "amount"]):
            intent["aggregation"] = "sum"
        elif any(kw in q for kw in ["average", "avg", "mean"]):
            intent["aggregation"] = "avg"
        elif any(kw in q for kw in ["max", "maximum", "highest"]):
            intent["aggregation"] = "max"
        elif any(kw in q for kw in ["min", "minimum", "lowest"]):
            intent["aggregation"] = "min"
        
        # Detect grouping
        if any(kw in q for kw in ["by ", "per ", "group by", "grouped by"]):
            intent["group_by"] = True
        
        # Detect time range
        import re
        time_patterns = [
            (r"last\s+(\d+)\s+(day|week|month|year)s?", "relative"),
            (r"past\s+(\d+)\s+(day|week|month|year)s?", "relative"),
            (r"in\s+(january|february|march|april|may|june|july|august|september|october|november|december)", "month"),
            (r"in\s+(\d{4})", "year"),
        ]
        
        for pattern, ttype in time_patterns:
            import re
            if re.search(pattern, q, re.IGNORECASE):
                intent["time_range"] = {"type": ttype}
                break
        
        return intent
    
    def _extract_entities(self, question: str) -> Dict:
        """Extract entities from question"""
        entities = {
            "trade_ids": [],
            "counterparties": [],
            "break_codes": [],
            "columns": [],
            "tables": [],
            "dates": [],
            "amounts": [],
        }
        
        question_lower = question.lower()
        
        # Trade IDs
        import re
        trade_pattern = r'\b(TRD[_\-]?\d{8,}|TRADE[_\-]?\d+)\b'
        entities["trade_ids"] = re.findall(r'\b(TRD[_\-]?\d{8,}|TRADE[_\-]?\d+)\b', question, re.IGNORECASE)
        
        # Counterparties
        cp_pattern = r'\b(GS|MS|JPM|CITI|BARC|DB|UBS|CS|BAML|HSBC|GOLDMAN|MORGAN|BARCLAYS)\b'
        entities["counterparties"] = re.findall(r'\b(GS|MS|JPM|CITI|BARC|DB|UBS|CS|BAML|HSBC|GOLDMAN|MORGAN|BARCLAYS)\b', question, re.IGNORECASE)
        
        # Break codes
        entities["break_codes"] = re.findall(r'\b(SAMT|SDAT|CPID|TRDT|QTYM|PRCM|CURM|BRK[_\-]?\w+)\b', question, re.IGNORECASE)
        
        # Columns (common ones)
        col_keywords = ["settlement", "trade", "amount", "date", "quantity", "price", "currency", "counterparty", "status"]
        for col in ["settlement_amount", "trade_date", "trade_id", "quantity", "price", "currency", "counterparty", "status"]:
            if col.replace("_", " ") in question.lower():
                entities["columns"].append(col)
        
        # Table hints
        table_keywords = ["trade", "recon", "confirmation", "settlement", "fee", "counterparty"]
        for table in ["TRADE_CORE", "RECON_RESULTS", "CONFIRMATIONS", "SETTLEMENTS", "FEE_SCHEDULE", "COUNTERPARTY"]:
            if any(kw in question.lower() for kw in table.lower().split("_")):
                entities["tables"].append(table)
        
        return entities
    
    def _lookup_schema(self, entities: Dict) -> Dict:
        """Lookup relevant schema from database"""
        # TODO: Implement actual schema lookup from relational store
        return {
            "tables": {
                "TRADE_CORE": {
                    "columns": ["TRADE_ID", "TRD_DT", "CP_CD", "TRD_STATUS", "SETT_AMT", "SETT_CCY"],
                    "description": "Core trade information",
                },
                "RECON_RESULTS": {
                    "columns": ["TRADE_ID", "SETT_AMT", "CONF_AMT", "BREAK_CODE", "RECON_DT"],
                    "description": "Reconciliation results",
                },
                "CONFIRMATIONS": {
                    "columns": ["TRADE_ID", "CONF_AMT", "CONF_DT", "CP_CD"],
                    "description": "Counterparty confirmations",
                },
                "FEE_SCHEDULE": {
                    "columns": ["CP_CD", "FEE_PCT", "FEE_TYPE", "EFF_DT"],
                    "description": "Fee schedules by counterparty",
                },
            },
            "relationships": [
                {"from": "TRADE_CORE", "to": "RECON_RESULTS", "on": "TRADE_ID"},
                {"from": "TRADE_CORE", "to": "CONFIRMATIONS", "on": "TRADE_ID"},
                {"from": "TRADE_CORE", "to": "FEE_SCHEDULE", "on": "CP_CD"},
            ],
        }
    
    def _generate_sql(self, question: str, entities: Dict, schema: Dict) -> Dict:
        """Generate SQL using LLM (placeholder - would call Tier 1 model)"""
        # This would call the Tier 1 model with tools
        # For now, return template-based SQL
        
        sql = self._template_sql(entities)
        
        return {
            "sql": sql,
            "explanation": f"Generated SQL for: {entities.get('trade_ids', ['unknown'])[0] if entities.get('trade_ids') else 'query'}",
            "confidence": 0.75,
            "tables_used": entities.get("tables", []),
            "columns_used": entities.get("columns", []),
        }
    
    def _template_sql(self, entities: Dict) -> str:
        """Generate template-based SQL"""
        # Simple template-based generation
        if entities.get("break_codes"):
            return f"""
SELECT t.TRADE_ID, t.TRD_DT, t.CP_CD, r.SETT_AMT, c.CONF_AMT,
       (r.SETT_AMT - c.CONF_AMT) as DIFF_AMT
FROM RECON_RESULTS r
JOIN TRADE_CORE t ON r.TRADE_ID = t.TRADE_ID
JOIN CONFIRMATIONS c ON r.TRADE_ID = c.TRADE_ID
WHERE r.BREAK_CODE = '{entities['break_codes'][0]}'
"""
        
        if entities.get("counterparties"):
            cp = entities["counterparties"][0]
            return f"""
SELECT t.TRADE_ID, t.TRD_DT, t.SETT_AMT, t.SETT_CCY
FROM TRADE_CORE t
WHERE t.CP_CD = '{entities['counterparties'][0]}'
  AND t.TRD_DT >= CURRENT_DATE - INTERVAL '1 month'
"""
        
        return "SELECT 1 as placeholder"
    
    def _validate_sql(self, sql: str) -> Dict:
        """Validate generated SQL"""
        errors = []
        warnings = []
        
        sql_upper = sql.upper()
        
        # Basic checks
        if not sql.strip():
            errors.append("Empty SQL")
        
        if "SELECT" not in sql_upper:
            errors.append("No SELECT statement")
        
        if "DROP" in sql_upper or "DELETE" in sql_upper or "TRUNCATE" in sql_upper:
            errors.append("Dangerous operation detected")
        
        if ";" not in sql.strip():
            warnings.append("No terminating semicolon")
        
        return {"errors": errors, "warnings": warnings}
    
    def _get_lineage(self, tables: List[str], columns: List[str]) -> List[Dict]:
        """Get lineage trace from graph store"""
        if not self.graph_store:
            return []
        
        lineage = []
        for table in tables:
            # Query graph store for lineage
            pass
        
        return []
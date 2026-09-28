"""
Trade Match Debugger - Debug trade breaks with lineage analysis
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from ..config import get_settings
from ..storage.graph import GraphStore
from ..storage.relational import RelationalStore


class TradeMatchDebugger:
    """Debugs trade match breaks with full lineage analysis"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self.graph_store = None
        self.relational_store = None
    
    def set_stores(self, graph_store: GraphStore, relational_store: RelationalStore):
        self.graph_store = graph_store
        self.relational_store = relational_store
    
    def debug_trade(self, trade_id: str, break_code: str = None) -> Dict:
        """
        Debug a specific trade break with full lineage analysis
        
        Returns:
            Dictionary with lineage trace, mismatch points, root cause, business action
        """
        logger.info(f"Debugging trade: {trade_id}, break_code: {break_code}")
        
        # Step 1: Get trade lineage from graph
        lineage = self._get_trade_lineage(trade_id)
        
        # Step 2: Get trade data from all sources
        trade_data = self._get_trade_data(trade_id)
        
        # Step 3: Trace through transformations
        mismatch_points = self._trace_mismatches(trade_data, break_code)
        
        # Step 4: Identify divergence point
        divergence = self._identify_divergence(mismatch_points)
        
        # Step 5: Generate business explanation
        explanation = self._generate_explanation(divergence, trade_data)
        
        return {
            "trade_id": trade_id,
            "break_reason": break_code,
            "lineage_trace": lineage,
            "mismatch_points": mismatch_points,
            "divergence_point": divergence,
            "root_cause": explanation["root_cause"],
            "business_action": explanation["business_action"],
            "confidence": 0.85,
        }
    
    def _get_trade_lineage(self, trade_id: str) -> List[Dict]:
        """Get full lineage trace for trade from graph"""
        # TODO: Query graph store for trade-specific lineage
        # Path: Source -> Ab Initio -> Oracle -> Recon -> Break
        
        # Placeholder lineage
        return [
            {
                "step": 1,
                "system": "source",
                "component": "SWIFT MT540",
                "field": "19A::SETT",
                "value": "USD 1,000,000",
                "status": "clean",
            },
            {
                "step": 2,
                "system": "ab_initio",
                "graph": "G_TRADE_ENRICH",
                "port": "SETT_AMT",
                "transform": "CAST(REPLACE(SETT_RAW, ',', '') AS DECIMAL(18,2))",
                "output": "1000000.00",
                "status": "clean",
            },
            {
                "step": 3,
                "system": "oracle",
                "procedure": "SP_ENRICH_TRADE",
                "column": "SETT_AMT",
                "logic": "SETT_AMT * (1 + NVL(FEE_PCT, 0))",
                "fee_applied": "0.05% (GS)",
                "output": "1000500.00",
                "status": "fee_applied",
            },
            {
                "step": 4,
                "system": "oracle",
                "procedure": "SP_RECON_MATCH",
                "expected": "1000000.00 (from Confirmation)",
                "actual": "1000500.00 (from Enriched)",
                "difference": "500.00",
                "break_code": "SAMT",
                "status": "break",
            },
        ]
    
    def _get_trade_data(self, trade_id: str) -> Dict:
        """Get trade data from all source systems"""
        # TODO: Query actual data from systems
        return {
            "source_swift": {"19A::SETT": "USD 1,000,000"},
            "ab_initio": {"SETT_AMT": "1000000.00"},
            "oracle_enriched": {"SETT_AMT": "1000500.00", "FEE_PCT": "0.0005"},
            "oracle_recon": {"EXPECTED": "1000000.00", "ACTUAL": "1000500.00", "BREAK": "SAMT"},
            "confirmation": {"SETT_AMT": "1000000.00"},
        }
    
    def _trace_mismatches(self, trade_data: Dict, break_code: str) -> List[Dict]:
        """Trace through data to find mismatches"""
        mismatches = []
        
        # Compare source -> ab_initio
        source_amt = self._parse_amount(trade_data.get("source_swift", {}).get("19A::SETT", ""))
        ab_amt = self._parse_amount(trade_data.get("ab_initio", {}).get("SETT_AMT", ""))
        
        if source_amt != ab_amt:
            mismatches.append({
                "stage": "source_to_abinitio",
                "source_value": source_amt,
                "target_value": ab_amt,
                "match": source_amt == ab_amt,
            })
        
        # Compare ab_initio -> oracle_enriched
        ab_amt = self._parse_amount(trade_data.get("ab_initio", {}).get("SETT_AMT", ""))
        enriched_amt = self._parse_amount(trade_data.get("oracle_enriched", {}).get("SETT_AMT", ""))
        
        if ab_amt != enriched_amt:
            fee = trade_data.get("oracle_enriched", {}).get("FEE_PCT", "0")
            mismatches.append({
                "stage": "abinitio_to_enriched",
                "source_value": ab_amt,
                "target_value": enriched_amt,
                "difference": enriched_amt - ab_amt,
                "reason": f"Fee applied: {fee}",
                "match": False,
            })
        
        # Compare enriched -> reconciliation
        enriched_amt = self._parse_amount(trade_data.get("oracle_enriched", {}).get("SETT_AMT", ""))
        expected_amt = self._parse_amount(trade_data.get("oracle_recon", {}).get("EXPECTED", ""))
        actual_amt = self._parse_amount(trade_data.get("oracle_recon", {}).get("ACTUAL", ""))
        
        if enriched_amt != expected_amt:
            mismatches.append({
                "stage": "enriched_to_recon_expected",
                "source_value": enriched_amt,
                "target_value": expected_amt,
                "match": False,
            })
        
        if actual_amt != expected_amt:
            mismatches.append({
                "stage": "recon_match",
                "expected_value": expected_amt,
                "actual_value": actual_amt,
                "difference": actual_amt - expected_amt,
                "break_code": "SAMT",
                "match": False,
            })
        
        return mismatches
    
    def _identify_divergence(self, mismatches: List[Dict]) -> Dict:
        """Identify the root divergence point"""
        for mismatch in mismatches:
            if not mismatch.get("match", True):
                return {
                    "stage": mismatch["stage"],
                    "reason": mismatch.get("reason", "Value mismatch"),
                    "source_value": mismatch.get("source_value"),
                    "target_value": mismatch.get("target_value"),
                    "difference": mismatch.get("difference"),
                }
        
        return {"stage": "unknown", "reason": "No clear divergence found"}
    
    def _generate_explanation(self, divergence: Dict, trade_data: Dict) -> Dict:
        """Generate business-language explanation"""
        stage = divergence.get("stage", "")
        
        if stage == "abinitio_to_enriched":
            return {
                "root_cause": "Fee schedule applied during enrichment but not reflected in counterparty confirmation",
                "business_action": "Confirm with counterparty if fee should be included in settlement amount or handled separately",
            }
        elif stage == "enriched_to_recon_expected":
            return {
                "root_cause": "Enriched settlement amount differs from counterparty confirmation",
                "business_action": "Reconcile fee schedules with counterparty agreements",
            }
        elif stage == "recon_match":
            return {
                "root_cause": "Settlement amount in enriched data differs from counterparty confirmation",
                "business_action": "Resolve break by confirming fee handling with counterparty",
            }
        elif stage == "source_to_abinitio":
            return {
                "root_cause": "Data transformation issue between source and Ab Initio",
                "business_action": "Verify Ab Initio transform logic for settlement amount parsing",
            }
        else:
            return {
                "root_cause": "Value mismatch detected in reconciliation pipeline",
                "business_action": "Investigate divergence point and resolve with counterparty",
            }
    
    def analyze_break_code(self, break_code: str, counterparty: str = None) -> Dict:
        """Analyze a specific break code across trades"""
        # TODO: Query historical data
        return {
            "break_code": break_code,
            "description": self._get_break_description(break_code),
            "common_causes": self._get_common_causes(break_code),
            "affected_trades": 0,
        }
    
    def _get_break_description(self, code: str) -> str:
        descriptions = {
            "SAMT": "Settlement Amount Mismatch",
            "SDAT": "Settlement Date Mismatch",
            "CPID": "Counterparty ID Mismatch",
            "TRDT": "Trade Date Mismatch",
            "QTYM": "Quantity Mismatch",
            "PRCM": "Price Mismatch",
            "CURM": "Currency Mismatch",
        }
        return descriptions.get(code, "Unknown Break Code")
    
    def _get_common_causes(self, code: str) -> List[str]:
        causes = {
            "SAMT": [
                "Fee schedules applied in enrichment but not in confirmation",
                "Rounding differences in currency conversion",
                "Different price sources used",
            ],
            "SDAT": [
                "Timezone differences in date processing",
                "Holiday calendar discrepancies",
                "T+1 vs T+2 settlement convention mismatch",
            ],
        }
        return causes.get(code, ["Unknown cause"])
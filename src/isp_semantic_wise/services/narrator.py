"""
Root Cause Narrator - Generates business-language narratives from technical traces
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from ..config import get_settings
from ..config.models import get_tier2_model


class RootCauseNarrator:
    """Generates business-language root cause narratives from technical traces"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self.llm_client = None  # Injected Tier 2 model
    
    def set_llm_client(self, client):
        """Set LLM client for Tier 2 model"""
        self.llm_client = client
    
    def narrate(self, incident_data: Dict, format: str = "structured") -> Dict:
        """
        Generate business-language root cause narrative
        
        Args:
            incident_data: Technical trace, error logs, trade context
            format: Output format (structured, narrative, executive)
            
        Returns:
            Dictionary with narrative, root cause, impact, actions, prevention
        """
        logger.info("Generating root cause narrative")
        
        if self.llm_client:
            return self._llm_narrate(incident_data, format)
        else:
            return self._template_narrate(incident_data, format)
    
    def _llm_narrate(self, incident_data: Dict, format: str) -> Dict:
        """Generate narrative using Tier 2 LLM"""
        prompt = self._build_prompt(incident_data, format)
        
        # TODO: Call Tier 2 model
        # response = self.llm_client.chat.completions.create(...)
        
        # For now, fall back to template
        return self._template_narrate(incident_data, format)
    
    def _build_prompt(self, incident_data: Dict, format: str) -> str:
        """Build prompt for Tier 2 model"""
        base_prompt = f"""
You are a senior capital markets post-trade analyst. Analyze the following technical incident 
and write a business-language root cause analysis.

INCIDENT DATA:
{incident_data}

FORMAT: {format}

REQUIRED OUTPUT STRUCTURE:
1. EXECUTIVE SUMMARY (1 paragraph)
2. TECHNICAL TRACE (simplified for business audience)
3. ROOT CAUSE (in business terms, not technical jargon)
4. BUSINESS IMPACT ASSESSMENT
5. RECOMMENDED ACTIONS (prioritized, with owners if possible)
6. PREVENTION MEASURES

GUIDELINES:
- Use business language, not technical jargon
- Focus on business impact, not technical details
- Be specific about financial/risk impact
- Actions should be actionable and assigned
- Prevention should address systemic issues
"""
        return base_prompt
    
    def _template_narrate(self, incident_data: Dict, format: str) -> Dict:
        """Template-based narration when LLM unavailable"""
        
        # Extract key info
        trade_id = incident_data.get("trade_id", "Unknown")
        break_code = incident_data.get("break_code", "Unknown")
        divergence = incident_data.get("divergence", {})
        lineage = incident_data.get("lineage", [])
        trade_context = incident_data.get("trade_context", {})
        
        # Build narrative
        if format == "executive":
            return self._executive_format(incident_data)
        elif format == "narrative":
            return self._narrative_format(incident_data)
        else:
            return self._structured_format(incident_data)
    
    def _structured_format(self, data: Dict) -> Dict:
        """Structured format output"""
        divergence = data.get("divergence", {})
        lineage = data.get("lineage", [])
        trade_id = data.get("trade_id", "Unknown")
        break_code = data.get("break_code", "Unknown")
        
        # Build executive summary
        stage = divergence.get("stage", "unknown")
        reason = divergence.get("reason", "Value mismatch")
        
        executive_summary = f"""
Trade {trade_id} broke with code {break_code} due to a mismatch at the {stage.replace('_', ' ')} stage. 
The root cause is {divergence.get('reason', 'a value mismatch')} resulting in a difference of {divergence.get('difference', 'unknown amount')}. 
Immediate action required: {self._get_action(divergence.get('stage', ''))}.
"""
        
        # Technical trace (simplified)
        tech_trace = []
        for step in data.get("lineage", []):
            tech_trace.append(f"Step {step.get('step')}: {step.get('system')} - {step.get('component', step.get('graph', ''))} - {step.get('status', '')}")
        
        # Root cause in business terms
        root_cause = self._business_root_cause(divergence.get("stage", ""))
        
        # Impact assessment
        impact = self._assess_impact(data)
        
        # Recommended actions
        actions = self._recommended_actions(divergence.get("stage", ""), data.get("trade_context", {}))
        
        # Prevention
        prevention = self._prevention_measures(divergence.get("stage", ""))
        
        return {
            "narrative": "",
            "executive_summary": executive_summary.strip(),
            "root_cause": root_cause,
            "impact_assessment": impact,
            "recommended_actions": actions,
            "prevention_measures": prevention,
            "confidence": 0.8,
        }
    
    def _executive_format(self, data: Dict) -> Dict:
        result = self._structured_format(data)
        return {
            "narrative": result["executive_summary"],
            "executive_summary": result["executive_summary"],
            "root_cause": result["root_cause"],
            "impact_assessment": result["impact_assessment"],
            "recommended_actions": result["recommended_actions"][:2],
            "prevention_measures": result["prevention_measures"][:2],
            "confidence": 0.8,
        }
    
    def _narrative_format(self, data: Dict) -> Dict:
        result = self._structured_format(data)
        
        narrative = f"""
{result['executive_summary']}

Technical investigation traced the trade through {len(data.get('lineage', []))} processing stages. 
The divergence occurred at {data.get('divergence', {}).get('stage', 'unknown stage').replace('_', ' ')}, 
where {data.get('divergence', {}).get('reason', 'a mismatch occurred')}.

{result['root_cause']}

Business Impact: {data.get('impact_assessment', 'Under assessment')}.

Recommended Actions:
"""
        for i, action in enumerate(result['recommended_actions'], 1):
            narrative += f"{i}. {action['action']} (Owner: {action.get('owner', 'TBD')}, Priority: {action.get('priority', 'Medium')}, Timeline: {action.get('timeline', 'TBD')})\n"
        
        narrative += "\nPrevention Measures:\n"
        for i, prev in enumerate(result['prevention_measures'], 1):
            narrative += f"{i}. {prev}\n"
        
        return {
            "narrative": narrative.strip(),
            "executive_summary": result["executive_summary"],
            "root_cause": result["root_cause"],
            "impact_assessment": result["impact_assessment"],
            "recommended_actions": result["recommended_actions"],
            "prevention_measures": result["prevention_measures"],
            "confidence": 0.8,
        }
    
    def _business_root_cause(self, stage: str) -> str:
        causes = {
            "abinitio_to_enriched": "Fee schedule applied during enrichment but not reflected in counterparty confirmation",
            "enriched_to_recon_expected": "Enriched settlement amount differs from counterparty confirmation",
            "recon_match": "Settlement amount in enriched data differs from counterparty confirmation",
            "source_to_abinitio": "Data transformation issue between source and Ab Initio",
            "recon_match": "Settlement amount in enriched data differs from counterparty confirmation",
        }
        return causes.get(stage, "Value mismatch detected in reconciliation pipeline")
    
    def _assess_impact(self, data: Dict) -> str:
        trade_id = data.get("trade_id", "")
        break_code = data.get("break_code", "")
        
        if break_code == "SAMT":
            diff = data.get("divergence", {}).get("difference", 0)
            if isinstance(diff, (int, float)) and diff > 10000:
                return f"HIGH - Trade {trade_id} has settlement amount discrepancy of ${diff:,.2f}. Impacts P&L, regulatory reporting, and counterparty relationship."
            return f"MEDIUM - Trade {trade_id} has settlement amount discrepancy. Requires investigation."
        return f"LOW - Trade {trade_id} has {break_code} break. Routine investigation needed."
    
    def _recommended_actions(self, stage: str, context: Dict) -> List[Dict]:
        actions_map = {
            "abinitio_to_enriched": [
                {"action": "Confirm fee inclusion with counterparty", "owner": "Operations", "priority": "High", "timeline": "24 hours"},
                {"action": "Review fee schedule configuration in enrichment", "owner": "IT/BA", "priority": "High", "timeline": "48 hours"},
                {"action": "Update reconciliation logic to handle fee-inclusive amounts", "owner": "IT", "priority": "Medium", "timeline": "1 week"},
            ],
            "enriched_to_recon_expected": [
                {"action": "Reconcile fee schedules with counterparty agreements", "owner": "Operations/Legal", "priority": "High", "timeline": "24 hours"},
                {"action": "Update reconciliation tolerance rules", "owner": "IT", "priority": "Medium", "timeline": "1 week"},
            ],
            "recon_match": [
                {"action": "Manually resolve trade break", "owner": "Operations", "priority": "High", "timeline": "4 hours"},
                {"action": "Root cause analysis for recurring breaks", "owner": "BA/IT", "priority": "Medium", "timeline": "1 week"},
            ],
        }
        return actions_map.get(stage, [
            {"action": "Investigate divergence point", "owner": "BA", "priority": "High", "timeline": "24 hours"},
            {"action": "Resolve trade break manually", "owner": "Operations", "priority": "High", "timeline": "4 hours"},
        ])
    
    def _prevention_measures(self, stage: str) -> List[str]:
        measures_map = {
            "abinitio_to_enriched": [
                "Automated fee schedule validation against counterparty agreements",
                "Reconciliation rule to flag fee-inclusive vs fee-exclusive mismatches",
                "Quarterly fee schedule reconciliation with all major counterparties",
            ],
            "enriched_to_recon_expected": [
                "Automated reconciliation of fee schedules across systems",
                "Counterparty confirmation of fee handling conventions",
            ],
            "recon_match": [
                "Enhanced break categorization and auto-routing",
                "Machine learning model to predict break root causes",
            ],
        }
        return measures_map.get(stage, [
            "Add automated data quality checks at divergence point",
            "Implement lineage-based alerting for value mismatches",
        ])
    
    def _get_action(self, stage: str) -> str:
        actions = {
            "abinitio_to_enriched": "confirm fee handling with counterparty",
            "enriched_to_recon_expected": "reconcile fee schedules",
            "recon_match": "resolve trade break and investigate root cause",
            "source_to_abinitio": "verify Ab Initio transform logic",
        }
        return actions.get(stage, "investigate divergence point")
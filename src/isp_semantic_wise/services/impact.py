"""
Impact Analyzer Service - Analyzes downstream impact of proposed changes
Uses chaos document and NetworkX graph for comprehensive impact analysis
"""
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from loguru import logger

from ..config import get_settings
from ..storage.graph import GraphStore
from ..storage.relational import RelationalStore


@dataclass
class ImpactResult:
    """Result of impact analysis"""
    change_summary: str
    affected_artifacts: List[Dict]
    risk_score: float
    risk_level: str
    breaking_changes: List[Dict]
    behavioral_changes: List[Dict]
    performance_impact: Optional[str]
    recommendations: List[str]
    migration_effort: str  # "low", "medium", "high"


@dataclass
class ChangeRequest:
    """Request for impact analysis"""
    change_type: str  # column, procedure, transform, parameter, schedule, graph
    source_system: str  # ab_initio, oracle, unix, pyspark
    artifact_path: str  # full path to artifact
    change_description: str
    proposed_value: Optional[str] = None
    max_depth: int = 5


class ImpactAnalyzer:
    """Analyzes downstream impact of proposed changes"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self.graph_store = None
        self.relational_store = None
    
    def set_stores(self, graph_store: GraphStore, relational_store: RelationalStore):
        self.graph_store = graph_store
        self.relational_store = relational_store
    
    def analyze(self, change_request: Dict) -> Dict:
        """
        Analyze impact of proposed change
        
        Args:
            change_request: Dictionary with change details
                - change_type: column, procedure, transform, parameter, schedule, graph
                - source_system: ab_initio, oracle, unix, pyspark
                - artifact_path: full path to artifact
                - change_description: what is changing
                - proposed_value: new value (optional)
                - max_depth: traversal depth (default 5)
                
        Returns:
            ImpactResult with risk assessment and affected components
        """
        logger.info(f"Analyzing impact: {change_request}")
        
        change_type = change_request.get("change_type", "")
        source_system = change_request.get("source_system", "")
        artifact_path = change_request.get("artifact_path", "")
        change_description = change_request.get("change_description", "")
        max_depth = change_request.get("max_depth", 5)
        
        # Step 1: Find affected artifacts via graph traversal
        affected = self._traverse_downstream(artifact_path, max_depth)
        
        # Step 2: Classify impact types
        breaking = []
        behavioral = []
        performance = None
        
        for artifact in affected:
            impact_type = self._classify_impact(change_request, artifact)
            artifact["impact_type"] = impact_type
            
            if impact_type == "breaking":
                breaking.append(artifact)
            elif impact_type == "behavioral":
                behavioral.append(artifact)
            elif impact_type == "performance":
                performance = "Potential performance impact on downstream processing"
        
        # Step 3: Calculate risk score
        risk_score = self._calculate_risk_score(breaking, behavioral, change_request)
        risk_level = self._risk_level(risk_score)
        
        # Step 4: Generate recommendations
        recommendations = self._generate_recommendations(risk_level, breaking, behavioral, change_request)
        
        # Step 5: Estimate migration effort
        migration_effort = self._estimate_effort(breaking, behavioral, change_request)
        
        return {
            "change_summary": f"{change_request.get('change_type', 'Change')} on {artifact_path}: {change_request.get('change_description', '')}",
            "affected_artifacts": affected,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "breaking_changes": breaking,
            "behavioral_changes": behavioral,
            "performance_impact": performance,
            "recommendations": recommendations,
            "migration_effort": migration_effort
        }
    
    def _traverse_downstream(self, start_path: str, max_depth: int) -> List[Dict]:
        """Traverse graph downstream from change point"""
        if not self.graph_store:
            return self._mock_downstream(start_path, max_depth)
        
        # Find node by path
        node_id = self._find_node_by_path(start_path)
        if not node_id:
            return []
        
        # BFS traversal downstream
        affected = []
        current_level = {node_id}
        visited = set()
        
        for depth in range(max_depth):
            next_level = set()
            for node in current_level:
                if node in visited:
                    continue
                visited.add(node)
                
                node_data = self.graph_store.get_node(node)
                if node_data:
                    affected.append({
                        "node_id": node,
                        "path": node_data.get("path", ""),
                        "type": node_data.get("artifact_type", ""),
                        "source_system": node_data.get("source_system", ""),
                        "depth": depth,
                        "name": node_data.get("name", "")
                    }
                
                # Get successors
                for succ in self.graph_store.successors(node):
                    if succ not in visited:
                        next_level.add(succ)
            
            current_level = next_level
            if not current_level:
                break
        
        return affected
    
    def _mock_downstream(self, start_path: str, max_depth: int) -> List[Dict]:
        """Mock downstream for testing without graph store"""
        mock_paths = {
            "TRADE_CORE.SETT_AMT": [
                "SP_ENRICH_TRADE.SETT_AMT", "SP_RECON_MATCH", "RECON_RESULTS",
                "RECON_REPORT", "FEE_CALCULATION"
            ],
            "AB_INITIO.G_TRADE_ENRICH.SETT_AMT": [
                "SP_ENRICH_TRADE.SETT_AMT", "SP_RECON_MATCH"
            ],
            "FEE_SCHEDULE.FEE_PCT": [
                "SP_ENRICH_TRADE.SETT_AMT", "SP_RECON_MATCH"
            ],
        }
        
        downstream = mock_paths.get(start_path, [])
        return [
            {"path": path, "type": "procedure" if "SP_" in path else "table", 
             "source_system": "oracle", "depth": 1, "name": path.split(".")[-1]}
            for path in downstream
        ]
    
    def _find_node_by_path(self, path: str) -> Optional[str]:
        """Find graph node by path"""
        if not self.graph_store:
            return None
        # Would query Neo4j for node with matching path property
        return None
    
    def _classify_impact(self, change_request: Dict, artifact: Dict) -> str:
        """Classify impact type for an artifact"""
        change_type = change_request.get("change_type", "")
        artifact_type = artifact.get("type", "")
        
        # Breaking changes
        if change_type == "column":
            if "data type" in change_request.get("change_description", "").lower():
                return "breaking"
            if "drop" in change_request.get("change_description", "").lower():
                return "breaking"
        
        if change_type == "procedure" and "signature" in change_request.get("change_description", "").lower():
            return "breaking"
        
        if change_type == "transform" and "logic" in change_request.get("change_description", "").lower():
            return "behavioral"
        
        if change_type == "parameter":
            return "behavioral"
        
        if change_type == "schedule":
            return "behavioral"
        
        return "behavioral"
    
    def _calculate_risk_score(self, breaking: List, behavioral: List, change_request: Dict) -> float:
        """Calculate risk score 0-1"""
        score = 0.0
        
        # Breaking changes weight heavily
        score += len(breaking) * 0.25
        
        # Behavioral changes moderate
        score += len(behavioral) * 0.1
        
        # Change type modifiers
        change_type = change_request.get("change_type", "")
        if change_type == "column":
            score += 0.15
        elif change_type == "procedure":
            score += 0.1
        elif change_type == "transform":
            score += 0.15
        elif change_type == "column":
            score += 0.15
        
        # Source system modifiers
        source = change_request.get("source_system", "")
        if source == "oracle":
            score += 0.1  # Core processing
        elif source == "ab_initio":
            score += 0.15  # ETL layer
        
        return min(1.0, score)
    
    def _risk_level(self, score: float) -> str:
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, risk_level: str, breaking: List, behavioral: List, change_request: Dict) -> List[str]:
        recommendations = []
        
        if risk_level in ["critical", "high"]:
            recommendations.append("Require mandatory code review and approval from Tech Lead")
            recommendations.append("Mandatory integration testing in staging environment")
            recommendations.append("Prepare rollback plan with documented steps")
        
        if breaking:
            recommendations.append("Identify all downstream consumers and notify stakeholders")
            recommendations.append("Coordinate deployment window with affected teams")
        
        if risk_level in ["medium", "low"]:
            recommendations.append("Enhanced monitoring for 48 hours post-deployment")
            recommendations.append("Automated regression tests for affected paths")
        
        if risk_level == "low":
            recommendations.append("Standard deployment process sufficient")
        
        return recommendations
    
    def _estimate_effort(self, breaking: List, behavioral: List, change_request: Dict) -> str:
        """Estimate migration/change effort"""
        total_affected = len(breaking) + len(behavioral)
        
        if len(breaking) > 5:
            return "high"
        elif len(breaking) > 2 or len(behavioral) > 5:
            return "medium"
        else:
            return "low"
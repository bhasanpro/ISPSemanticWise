"""
Model Router - Routes queries to appropriate model tier
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from ..config import get_settings, Settings


class ModelRouter:
    """Routes queries to appropriate model tier based on task type"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self._load_routing_config()
    
    def _load_routing_config(self):
        """Load routing config from models.yaml"""
        models_config = self.settings.load_models_config()
        
        self.tier1_keywords = models_config.get("routing", {}).get("tier_1_keywords", [])
        self.tier2_keywords = models_config.get("routing", {}).get("tier_2_keywords", [])
        self.default_tier = models_config.get("routing", {}).get("default_tier", "tier_1")
        self.confidence_threshold = models_config.get("routing", {}).get("confidence_threshold", 0.7)
        
        # Tier configurations
        self.tier1_config = models_config.get("tier_1", {})
        self.tier2_config = models_config.get("tier_2", {})
        self.hybrid_config = models_config.get("hybrid", {})
    
    def route(self, query: str, context: Dict = None) -> Dict:
        """
        Determine which model tier to use for a query
        
        Returns:
            Dict with tier, model, confidence, and routing reason
        """
        # Check for explicit tier in context
        if context and context.get("force_tier"):
            return {
                "tier": context["force_tier"],
                "model": self._get_default_model(context["force_tier"]),
                "confidence": 1.0,
                "reason": "explicit_override",
            }
        
        # Check for hybrid service routing
        if context and context.get("service"):
            service_routing = self._route_service(context["service"])
            if service_routing:
                return service_routing
        
        # Keyword-based routing
        tier, confidence, reason = self._keyword_routing(query)
        
        return {
            "tier": tier,
            "model": self._get_default_model(tier),
            "confidence": confidence,
            "reason": reason,
        }
    
    def _route_service(self, service: str) -> Optional[Dict]:
        """Route based on service name"""
        hybrid_services = self.hybrid_config.get("services", [])
        
        for svc in hybrid_services:
            if svc["name"] == service:
                return {
                    "tier": "hybrid",
                    "model": "hybrid",
                    "confidence": 1.0,
                    "reason": f"hybrid_service_{service}",
                    "hybrid_config": svc,
                }
        
        # Check if service has fixed tier
        service_tiers = {
            "nl2sql": "tier_1",
            "query_routing": "tier_1",
            "entity_extraction": "tier_1",
            "lineage_traversal": "tier_1",
            "glossary_generation": "tier_2",
            "root_cause_narrative": "tier_2",
            "impact_analysis": "tier_2",
            "code_understanding": "tier_2",
            "documentation_generation": "tier_2",
        }
        
        if service in service_tiers:
            tier = service_tiers[service]
            return {
                "tier": tier,
                "model": self._get_default_model(tier),
                "confidence": 0.9,
                "reason": f"service_{service}",
            }
        
        return None
    
    def _keyword_routing(self, query: str) -> tuple:
        """Route based on query keywords"""
        query_lower = query.lower()
        
        tier2_score = 0
        tier1_score = 0
        matched_tier2 = []
        matched_tier1 = []
        
        for kw in self.tier2_keywords:
            if kw.lower() in query_lower:
                tier2_score += 1
                matched_tier2.append(kw)
        
        for kw in self.tier1_keywords:
            if kw.lower() in query_lower:
                tier1_score += 1
                matched_tier1.append(kw)
        
        # Determine tier
        if tier2_score > tier1_score:
            confidence = min(0.9, 0.5 + tier2_score * 0.1)
            return "tier_2", min(0.95, confidence), f"tier2_keywords:{matched_tier2}"
        elif tier1_score > tier2_score:
            confidence = min(0.9, 0.5 + tier1_score * 0.1)
            return "tier_1", min(0.95, confidence), f"tier1_keywords:{matched_tier1}"
        else:
            # Tie - use default
            tier = self.default_tier
            return tier, 0.6, "default_tier"
    
    def _get_default_model(self, tier: str) -> str:
        """Get default model for tier"""
        if tier == "tier_1":
            return self.tier1_config.get("default_model", "meta/llama-3.2-11b-vision-instruct")
        elif tier == "tier_2":
            return self.tier2_config.get("default_model", "nvidia/nemotron-3-super-120b-a12b")
        else:
            return "hybrid"
    
    def get_model_config(self, tier: str) -> Dict:
        """Get full model configuration for tier"""
        if tier == "tier_1":
            config = self.tier1_config.copy()
            config["model"] = self._get_default_model("tier_1")
            return config
        elif tier == "tier_2":
            config = self.tier2_config.copy()
            config["model"] = self._get_default_model("tier_2")
            return config
        else:
            return {"model": "hybrid"}
    
    def get_hybrid_config(self, service: str) -> Optional[Dict]:
        """Get hybrid routing config for service"""
        hybrid_services = self.hybrid_config.get("services", [])
        for svc in hybrid_services:
            if svc["name"] == service:
                return svc
        return None
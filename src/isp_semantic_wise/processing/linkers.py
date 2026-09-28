"""
Entity Linker - Links extracted entities to business terms and technical artifacts
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from loguru import logger
from difflib import get_close_matches


@dataclass
class EntityLink:
    """Represents a link between extracted entity and known entity"""
    extracted_entity: str
    extracted_type: str
    linked_entity_id: str
    linked_type: str
    confidence: float
    match_method: str  # exact, fuzzy, llm, semantic


class EntityLinker:
    """Links extracted entities to known business terms and technical artifacts"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.use_llm_verification = config.get("use_llm_verification", True)
        self.llm_client = None  # Will be set externally
        
        # Caches
        self.business_terms_cache: Dict[str, Dict] = {}
        self.technical_artifacts_cache: Dict[str, Dict] = {}
    
    def load_caches(self, business_terms: List[Dict], technical_artifacts: List[Dict]):
        """Load reference caches"""
        self.business_terms_cache = {
            term["term"].lower(): term for term in business_terms
        }
        # Also index by synonyms
        for term in business_terms:
            for syn in term.get("synonyms", []):
                self.business_terms_cache[syn.lower()] = term
        
        self.technical_artifacts_cache = {
            art["path"].lower(): art for art in technical_artifacts
        }
    
    def link_entities(self, entities: List[Dict]) -> List[EntityLink]:
        """Link extracted entities to known entities"""
        links = []
        
        for entity in entities:
            entity_text = entity.get("name", "") or entity.get("text", "")
            entity_type = entity.get("type", "unknown")
            
            if not entity_text:
                continue
            
            # Try exact match first
            link = self._exact_match(entity_text, entity_type)
            if link and link.confidence >= self.confidence_threshold:
                links.append(link)
                continue
            
            # Try fuzzy match
            link = self._fuzzy_match(entity_text, entity_type)
            if link and link.confidence >= self.confidence_threshold:
                links.append(link)
                continue
            
            # Try semantic match (embedding-based)
            link = self._semantic_match(entity_text, entity_type)
            if link and link.confidence >= self.confidence_threshold:
                links.append(link)
                continue
            
            # LLM verification if enabled
            if self.use_llm_verification and self.llm_client:
                link = self._llm_verify(entity_text, entity_type)
                if link and link.confidence >= self.confidence_threshold:
                    links.append(link)
        
        return links
    
    def _exact_match(self, text: str, entity_type: str) -> Optional[EntityLink]:
        """Try exact match in caches"""
        text_lower = text.lower()
        
        # Check business terms
        if text_lower in self.business_terms_cache:
            term = self.business_terms_cache[text_lower]
            return EntityLink(
                extracted_entity=text,
                extracted_type="business_term",
                linked_entity_id=term.get("id", ""),
                linked_type="business_term",
                confidence=1.0,
                match_method="exact",
            )
        
        # Check technical artifacts
        for path, artifact in self.technical_artifacts_cache.items():
            if path.endswith(text.lower()) or text.lower() in path:
                return EntityLink(
                    extracted_entity=text,
                    extracted_type="technical",
                    linked_entity_id=artifact.get("id", ""),
                    linked_type=artifact.get("artifact_type", "technical"),
                    confidence=0.9,
                    match_method="exact_path",
                )
        
        return None
    
    def _fuzzy_match(self, text: str, entity_type: str) -> Optional[EntityLink]:
        """Fuzzy string matching"""
        from difflib import get_close_matches
        
        text_lower = text.lower()
        
        # Business terms
        term_names = list(self.business_terms_cache.keys())
        matches = get_close_matches(text_lower, term_names, n=3, cutoff=0.8)
        if matches:
            best = matches[0]
            term = self.business_terms_cache[best]
            return EntityLink(
                extracted_entity=text,
                extracted_type="business_term",
                linked_entity_id=term.get("id", ""),
                linked_type="business_term",
                confidence=0.85,
                match_method="fuzzy",
            )
        
        # Technical artifacts
        tech_names = list(self.technical_artifacts_cache.keys())
        matches = get_close_matches(text_lower, tech_names, n=3, cutoff=0.75)
        if matches:
            best = matches[0]
            artifact = self.technical_artifacts_cache[best]
            return EntityLink(
                extracted_entity=text,
                extracted_type="technical",
                linked_entity_id=artifact.get("id", ""),
                linked_type=artifact.get("artifact_type", "technical"),
                confidence=0.8,
                match_method="fuzzy",
            )
        
        return None
    
    def _semantic_match(self, text: str, entity_type: str) -> Optional[EntityLink]:
        """Semantic matching using embeddings (placeholder)"""
        # Would use embedding similarity search
        # For now, return None
        return None
    
    def _llm_verify(self, text: str, entity_type: str) -> Optional[EntityLink]:
        """Use LLM to verify entity linking"""
        if not self.llm_client:
            return None
        
        # Would call LLM to verify mapping
        # Placeholder for now
        return None


class BusinessTermLinker(EntityLinker):
    """Specialized linker for business terms"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.term_hierarchy = {}  # parent-child relationships
    
    def load_taxonomy(self, terms: List[Dict]):
        """Load business term taxonomy with hierarchy"""
        for term in terms:
            term_id = term.get("id")
            if term_id:
                self.term_hierarchy[term_id] = {
                    "parent": term.get("parent_term_id"),
                    "children": term.get("child_term_ids", []),
                    "category": term.get("category"),
                }
    
    def find_related_terms(self, term_id: str, max_depth: int = 2) -> List[str]:
        """Find related terms in taxonomy"""
        related = set()
        to_visit = [term_id]
        visited = set()
        depth = 0
        
        while to_visit and depth < max_depth:
            next_visit = []
            for tid in to_visit:
                if tid in visited:
                    continue
                visited.add(tid)
                
                term_info = self.term_hierarchy.get(tid, {})
                if term_info.get("parent"):
                    next_visit.append(term_info["parent"])
                next_visit.extend(term_info.get("children", []))
                
                related.add(tid)
            
            to_visit = next_visit
            depth += 1
        
        return list(related)


class TechnicalArtifactLinker(EntityLinker):
    """Specialized linker for technical artifacts"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.lineage_graph = None  # NetworkX graph for lineage
    
    def load_lineage(self, graph):
        """Load lineage graph for traversal"""
        self.lineage_graph = graph
    
    def find_downstream(self, artifact_path: str, max_depth: int = 5) -> List[str]:
        """Find downstream artifacts"""
        if not self.lineage_graph:
            return []
        
        # Find node by path
        node_id = None
        for node, data in self.lineage_graph.nodes(data=True):
            if data.get("path", "").endswith(artifact_path):
                node_id = node
                break
        
        if not node_id:
            return []
        
        # Traverse downstream
        downstream = set()
        current = {node_id}
        for _ in range(max_depth):
            next_nodes = set()
            for node in current:
                if node in downstream:
                    continue
                downstream.add(node)
                
                for succ in self.lineage_graph.successors(node):
                    if succ not in downstream:
                        next_nodes.add(succ)
            
            current = next_nodes - downstream
            if not current:
                break
        
        return list(downstream)
    
    def find_upstream(self, artifact_path: str, max_depth: int = 5) -> List[str]:
        """Find upstream artifacts"""
        if not self.lineage_graph:
            return []
        
        # Similar to downstream but with predecessors
        node_id = None
        for node, data in self.lineage_graph.nodes(data=True):
            if data.get("path", "").endswith(artifact_path):
                node_id = node
                break
        
        if not node_id:
            return []
        
        upstream = set()
        current = {node_id}
        for _ in range(max_depth):
            next_nodes = set()
            for node in current:
                for pred in self.lineage_graph.predecessors(node):
                    if pred not in upstream:
                        upstream.add(pred)
                        next_nodes.add(pred)
            
            current = next_nodes
            if not current:
                break
        
        return list(upstream)
"""
Glossary Builder - Generates business glossary from code and documentation
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from ..config import get_settings
from ..processing.embedders import EmbeddingGenerator
from ..processing.linkers import BusinessTermLinker
from ..storage.vector import VectorStore
from ..storage.graph import GraphStore


class GlossaryBuilder:
    """Builds business glossary from code and documentation"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.settings = get_settings()
        self.embedder = EmbeddingGenerator(self.config.get("embedding", {}))
        self.linker = BusinessTermLinker(self.config.get("linker", {}))
        self.vector_store = None
        self.graph_store = None
    
    def set_stores(self, vector_store: VectorStore, graph_store: GraphStore):
        """Set storage backends"""
        self.vector_store = vector_store
        self.graph_store = graph_store
    
    def build_glossary(self, source_data: List[Dict]) -> List[Dict]:
        """
        Build business glossary from source artifacts
        
        Args:
            source_data: List of technical artifacts with extracted entities
            
        Returns:
            List of business term definitions
        """
        logger.info(f"Building glossary from {len(source_data)} artifacts")
        
        # Extract candidate business terms from source
        candidates = self._extract_candidates(source_data)
        logger.info(f"Found {len(candidates)} candidate terms")
        
        # Cluster similar candidates
        clusters = self._cluster_candidates(candidates)
        logger.info(f"Clustered into {len(clusters)} term groups")
        
        # Generate definitions for each cluster
        glossary = []
        for cluster in clusters:
            term = self._generate_term_definition(cluster)
            if term:
                glossary.append(term)
        
        logger.info(f"Generated glossary with {len(glossary)} terms")
        return glossary
    
    def _extract_candidates(self, artifacts: List[Dict]) -> List[Dict]:
        """Extract candidate business terms from artifacts"""
        candidates = []
        
        for artifact in artifacts:
            artifact_type = artifact.get("artifact_type", "")
            
            if artifact_type in ["procedure", "view", "table", "transform", "variable"]:
                # Extract from names and comments
                name = artifact.get("name", "")
                path = artifact.get("path", "")
                code = artifact.get("code_snippet", "")
                
                # Extract from name (camelCase, snake_case)
                terms = self._extract_terms_from_name(name)
                terms.extend(self._extract_terms_from_name(path))
                
                # Extract from comments in code
                comments = self._extract_comments(artifact.get("code_snippet", ""))
                for comment in comments:
                    terms.extend(self._extract_terms_from_text(comment))
                
                for term in terms:
                    candidates.append({
                        "term": term,
                        "source_artifact": artifact,
                        "context": "code_name" if term in name else "code_path" if term in path else "comment",
                    })
        
        return candidates
    
    def _extract_terms_from_name(self, name: str) -> List[str]:
        """Extract business terms from camelCase/snake_case names"""
        import re
        terms = []
        
        # Split camelCase and PascalCase
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', name)
        # Also split snake_case
        snake_words = name.split('_')
        
        all_words = words + snake_words
        
        # Filter and combine
        for word in all_words:
            if len(word) >= 3 and word.isalpha():
                # Single words
                if len(word) >= 4:
                    yield word
        
        # Also try bigrams
        words_list = list(all_words)
        for i in range(len(words_list) - 1):
            if words_list[i].isalpha() and words_list[i+1].isalpha():
                bigram = f"{words_list[i]} {words_list[i+1]}"
                if len(bigram) > 5:
                    yield bigram
    
    def _extract_comments(self, code: str) -> List[str]:
        """Extract comments from code"""
        import re
        comments = []
        
        # SQL/PLSQL comments
        for match in re.finditer(r'--\s*(.+)$', code, re.MULTILINE):
            comments.append(match.group(1).strip())
        
        # Multi-line comments
        import re
        for match in re.finditer(r'/\*(.*?)\*/', code, re.DOTALL):
            comments.append(match.group(1).strip())
        
        # Shell/Python comments
        for match in re.finditer(r'#\s*(.+)$', code, re.MULTILINE):
            comments.append(match.group(1).strip())
        
        return comments
    
    def _extract_terms_from_text(self, text: str) -> List[str]:
        """Extract potential business terms from text"""
        import re
        terms = set()
        
        # Capitalized phrases
        for match in re.finditer(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text):
            term = match.group(0)
            if len(term) > 3:
                yield term
        
        # Known business patterns
        patterns = [
            r'\b(Trade|Settlement|Counterparty|Reconciliation|Matching|Confirmation)\w*\b',
            r'\b(Settlement\s+(?:Amount|Date|Currency))\b',
            r'\b(Trade\s+(?:Date|ID|Status))\b',
            r'\b(Break\s+(?:Code|Reason))\b',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                yield match.group(0)
    
    def _cluster_candidates(self, candidates: List[Dict]) -> List[List[Dict]]:
        """Cluster similar candidates together"""
        clusters = []
        used = set()
        
        for i, cand in enumerate(candidates):
            if i in used:
                continue
            
            cluster = [cand]
            used.add(i)
            
            cand_term = cand.get("term", "").lower()
            
            for j, other in enumerate(candidates):
                if j in used or i == j:
                    continue
                
                # Check similarity
                if self._terms_similar(cand.get("term", ""), other.get("term", "")):
                    cluster.append(other)
                    used.add(j)
            
            if cluster:
                yield cluster
    
    def _terms_similar(self, term1: str, term2: str) -> bool:
        """Check if two terms are similar"""
        t1 = term1.lower()
        t2 = term2.lower()
        
        if t1 == t2:
            return True
        
        # Check if one contains the other
        if t1 in t2 or t2 in t1:
            return True
        
        # Word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        overlap = len(words1 & words2)
        
        if len(words1) > 0 and len(words2) > 0:
            overlap_ratio = overlap / min(len(words1), len(words2))
            return overlap_ratio > 0.5
        
        return False
    
    def _generate_term_definition(self, cluster: List[Dict]) -> Optional[Dict]:
        """Generate business term definition from cluster"""
        if not cluster:
            return None
        
        # Select best term from cluster
        best = max(cluster, key=lambda c: len(c.get("term", "")))
        term = best.get("term", "")
        
        # Gather all synonyms
        synonyms = list(set(c.get("term", "") for c in cluster))
        
        # Generate definition (placeholder - would use LLM)
        definition = f"Business term derived from {len(cluster)} source artifacts"
        
        # Determine category
        category = self._infer_category(cluster)
        
        return {
            "term": cluster[0].get("term", ""),
            "synonyms": list(set(s for c in cluster for s in [c.get("term", "")] if s != term)),
            "definition": definition,
            "category": category,
            "confidence_score": min(0.9, 0.5 + len(cluster) * 0.1),
            "source_artifacts": [c.get("source_artifact", {}).get("path", "") for c in cluster],
            "evidence": [c.get("context", "") for c in cluster],
        }
    
    def _infer_category(self, cluster: List[Dict]) -> str:
        """Infer category from cluster"""
        categories = {
            "trade": ["trade", "trd", "transaction"],
            "settlement": ["settlement", "sett", "stlm"],
            "counterparty": ["counterparty", "cp", "party"],
            "reconciliation": ["reconciliation", "recon", "matching", "match"],
            "risk": ["risk", "limit", "exposure"],
            "fee": ["fee", "commission", "charge"],
        }
        
        all_text = " ".join(c.get("term", "").lower() for c in cluster)
        
        for cat, keywords in categories.items():
            if any(kw in all_text for kw in keywords):
                return cat
        
        return "general"
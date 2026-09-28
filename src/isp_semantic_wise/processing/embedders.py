"""
Embedding Generator - Vector embeddings for semantic search
"""
import numpy as np
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, using fallback")


class EmbeddingGenerator:
    """Generates embeddings for text chunks"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.model_name = config.get("model", "sentence-transformers/all-MiniLM-L6-v2")
        self.device = config.get("device", "cpu")
        self.batch_size = config.get("batch_size", 32)
        self.normalize = config.get("normalize", True)
        
        self.model = None
        self.embedding_dim = 384  # Default for MiniLM-L6-v2
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self._load_model()
    
    def _load_model(self):
        """Load sentence transformer model"""
        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self.model_name} (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None
    
    def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for list of texts"""
        if not texts:
            return []
        
        if self.model is None:
            return self._fallback_embeddings(texts)
        
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return self._fallback_embeddings(texts)
    
    def generate_single(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        return self.generate([text])[0]
    
    def _fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Fallback: simple hash-based embeddings (not semantic!)"""
        logger.warning("Using fallback hash-based embeddings - not semantic!")
        embeddings = []
        for text in texts:
            # Simple hash-based pseudo-embedding (NOT for production semantic search)
            hash_val = hash(text)
            np.random.seed(abs(hash_val) % (2**32))
            emb = np.random.normal(0, 1, 384)
            if self.normalize:
                emb = emb / np.linalg.norm(emb)
            embeddings.append(emb.tolist())
        return embeddings
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.embedding_dim


class BatchEmbeddingGenerator(EmbeddingGenerator):
    """Batch embedding generator with progress tracking"""
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self.show_progress = config.get("show_progress", True)
    
    def generate_with_progress(self, texts: List[str], desc: str = "Embedding") -> List[List[float]]:
        """Generate embeddings with progress bar"""
        from tqdm import tqdm
        
        if self.model is None:
            return self._fallback_embeddings(texts)
        
        embeddings = []
        for i in tqdm(range(0, len(texts), self.batch_size), desc=desc, disable=not self.show_progress):
            batch = texts[i:i + self.batch_size]
            batch_emb = self.model.encode(
                batch,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
            )
            embeddings.extend(batch_emb.tolist())
        
        return embeddings
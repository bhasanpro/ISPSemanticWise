"""
Vector Store - ChromaDB abstraction for semantic search
"""
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class VectorStore:
    """Vector store abstraction with ChromaDB backend"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.provider = config.get("provider", "chroma")
        self.client = None
        self.collection = None
        self.embedding_dim = config.get("embedding_dimension", 384)
    
    def initialize(self):
        """Initialize the vector store"""
        if self.provider == "chroma":
            self._init_chroma()
        # elif self.provider == "pinecone":
        #     self._init_pinecone()
        else:
            raise ValueError(f"Unsupported vector store provider: {self.provider}")
    
    def _init_chroma(self):
        """Initialize ChromaDB"""
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb not installed")
        
        settings = ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.config.get("persist_directory", "./data/chroma"),
        )
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(
            name=self.config.get("collection_name", "isp_semantic_chunks"),
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB initialized")
    
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[str], metadatas: List[Dict] = None) -> bool:
        """Add vectors to store"""
        try:
            if self.provider == "chroma":
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas or [{}] * len(ids),
                )
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors: {e}")
            return False
    
    def query(self, query_embedding: List[float], n_results: int = 10, 
              filter: Dict = None) -> Dict:
        """Query similar vectors"""
        try:
            if self.provider == "chroma":
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=filter,
                    include=["documents", "metadatas", "distances"],
                )
                return {
                    "ids": results["ids"][0],
                    "documents": results["documents"][0],
                    "metadatas": results["metadatas"][0],
                    "distances": results["distances"][0],
                }
        except Exception as e:
            logger.error(f"Vector query failed: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}
        
        return {"ids": [], "documents": [], "metadatas": [], "distances": []}
    
    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs"""
        try:
            if self.provider == "chroma":
                self.collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False
    
    def get_count(self) -> int:
        """Get total vector count"""
        try:
            if self.provider == "chroma":
                return self.collection.count()
        except Exception:
            return 0
        return 0
"""
Main Ingestion Pipeline - Orchestrates all connectors and loads to semantic stores
"""
import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from .base import BaseIngestionConnector, IngestionJob, IngestionResult, IngestionStatus
from .enhanced_oracle import EnhancedOracleConnector
from .ab_initio import AbInitioConnector
from .unix import UnixConnector
from .networkx_sync import NetworkXSyncConnector

from ..storage.vector import VectorStore
from ..storage.graph import GraphStore
from ..storage.relational import RelationalStore
from ..processing.embedders import EmbeddingGenerator
from ..processing.linkers import EntityLinker


@dataclass
class PipelineConfig:
    """Configuration for the ingestion pipeline"""
    connectors: Dict[str, Dict] = field(default_factory=dict)
    parallel_feeds: bool = True
    max_workers: int = 4
    batch_size: int = 100
    generate_embeddings: bool = True
    update_graph: bool = True
    update_vector_store: bool = True
    update_relational: bool = True


class IngestionPipeline:
    """
    Main ingestion pipeline that orchestrates all connectors
    and loads data into the semantic stores (Vector, Graph, Relational)
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.connectors: Dict[str, BaseIngestionConnector] = {}
        self.vector_store: Optional[VectorStore] = None
        self.graph_store: Optional[GraphStore] = None
        self.relational_store: Optional[RelationalStore] = None
        self.embedder = None
        self.linker = None
        self.jobs: Dict[str, IngestionJob] = {}
    
    def initialize(self, vector_store: VectorStore, graph_store: GraphStore, 
                   relational_store: RelationalStore, embedder=None, linker=None):
        """Initialize storage backends"""
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.relational_store = relational_store
        self.embedder = embedder
        self.linker = linker
        
        # Initialize connectors
        self._initialize_connectors()
    
    def _initialize_connectors(self):
        """Initialize all configured connectors"""
        for name, config in self.config.connectors.items():
            connector_type = config.get("type")
            
            if connector_type == "oracle":
                self.connectors[name] = EnhancedOracleConnector(config)
            elif connector_type == "ab_initio":
                self.connectors[name] = AbInitioConnector(config)
            elif connector_type == "unix":
                self.connectors[name] = UnixConnector(config)
            elif connector_type == "networkx_sync":
                self.connectors[name] = NetworkXSyncConnector(config)
            else:
                logger.warning(f"Unknown connector type: {connector_type}")
    
    def run_full_ingestion(self, feed_names: List[str] = None) -> Dict[str, IngestionResult]:
        """Run full ingestion pipeline for all or specified feeds"""
        logger.info("Starting full ingestion pipeline")
        
        results = {}
        
        # Determine which feeds to process
        feeds_to_process = self._get_feeds_to_process(feed_names)
        
        # Process feeds (parallel if configured)
        if self.config.parallel_feeds and len(feeds_to_process) > 1:
            results = self._run_parallel(feeds_to_process)
        else:
            results = {}
            for feed_name in feeds_to_process:
                results[feed_name] = self._process_feed(feed_name)
        
        # Post-process: generate embeddings, update graph, link entities
        self._post_process(results)
        
        return results
    
    def _get_feeds_to_process(self, feed_names: Optional[List[str]]) -> List[str]:
        """Determine which feeds to process"""
        if feed_names:
            return [f for f in feed_names if f in self.connectors]
        return list(self.connectors.keys())
    
    def _run_parallel(self, feed_names: List[str]) -> Dict[str, IngestionResult]:
        """Run ingestion in parallel for multiple feeds"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_feed = {
                executor.submit(self._process_feed, feed_name): feed_name 
                for feed_name in feed_names
            }
            
            for future in as_completed(future_to_feed):
                feed_name = future_to_feed[future]
                try:
                    results[feed_name] = future.result()
                except Exception as e:
                    logger.error(f"Feed {feed_name} failed: {e}")
                    # Create failed result
                    results[feed_name] = IngestionResult(
                        job_id=str(uuid.uuid4()),
                        success=False,
                        items=[],
                        errors=[{"error": str(e)}],
                        metadata={"feed": feed_name}
                    )
        
        return results
    
    def _process_feed(self, feed_name: str) -> IngestionResult:
        """Process a single feed through the full pipeline"""
        logger.info(f"Processing feed: {feed_name}")
        
        connector = self.connectors.get(feed_name)
        if not connector:
            return IngestionResult(
                job_id=str(uuid.uuid4()),
                success=False,
                items=[],
                errors=[{"error": f"Connector not found: {feed_name}"}]
            )
        
        job = IngestionJob(
            job_type=type(connector).__name__,
            source_path=feed_name,
            status=IngestionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        all_items = []
        all_errors = []
        
        try:
            # Discover sources
            sources = connector.discover()
            logger.info(f"Discovered {len(sources)} sources for {feed_name}")
            
            # Process each source
            for source in sources:
                try:
                    # Extract
                    raw_data = connector.extract(source)
                    logger.debug(f"Extracted {len(raw_data)} items from {source}")
                    
                    # Transform
                    transformed = connector.transform(raw_data)
                    
                    # Load to storage
                    result = self._load_to_stores(transformed, source)
                    
                    all_items.extend(result.items)
                    
                except Exception as e:
                    logger.error(f"Error processing {source}: {e}")
                    self.jobs[feed_name].items_failed += 1
                    self.jobs[feed_name].errors.append({"source": source, "error": str(e)})
            
            # Update job status
            self.jobs[feed_name] = IngestionResult(
                job_id=str(uuid.uuid4()),
                success=len([e for e in feed_results if not e.success]) == 0,
                items=all_items,
                errors=all_errors,
                metadata={"feed": feed_name, "total_items": len(all_items)}
            )
            
        except Exception as e:
            logger.error(f"Feed {feed_name} failed: {e}")
            return IngestionResult(
                job_id=str(uuid.uuid4()),
                success=False,
                items=[],
                errors=[{"error": str(e)}],
                metadata={"feed": feed_name}
            )
        
        return IngestionResult(
            job_id=str(uuid.uuid4()),
            success=True,
            items=all_items,
            errors=[],
            metadata={"feed": feed_name}
        )
    
    def _load_to_stores(self, items: List[Dict], source: str) -> IngestionResult:
        """Load transformed items to all storage backends"""
        results = IngestionResult(job_id=str(uuid.uuid4()), success=True, items=[])
        
        for item in items:
            try:
                # 1. Load to Relational Store (Oracle)
                if self.config.update_relational and self.relational_store:
                    self._load_to_relational(item)
                
                # 2. Load to Graph Store (Neo4j)
                if self.config.update_graph and self.graph_store:
                    self._load_to_graph(item)
                
                # 3. Generate embeddings and load to Vector Store (ChromaDB)
                if self.config.generate_embeddings and self.config.update_vector_store and self.vector_store:
                    self._load_to_vector(item)
                
                results.items.append(item)
                
            except Exception as e:
                logger.error(f"Failed to load item: {e}")
                results.errors.append({"item": item.get("name", "unknown"), "error": str(e)})
        
        results.success = len(results.errors) == 0
        return results
    
    def _load_to_relational(self, item: Dict):
        """Load item to Oracle relational store"""
        artifact_type = item.get("artifact_type", "unknown")
        
        if artifact_type in ["table", "feed_table"]:
            self.relational_store.upsert_technical_artifact({
                "artifact_type": "table",
                "name": item.get("name"),
                "source_system": item.get("source_system", "oracle"),
                "path": item.get("path", ""),
                "code_snippet": item.get("code_snippet", ""),
                "metadata": json.dumps(item.get("metadata", {}))
            })
            
            # If feed table, also upsert feed mapping
            if item.get("artifact_type") == "feed_table":
                metadata = item.get("metadata", {})
                feed_name = metadata.get("feed_name", "unknown")
                self._upsert_feed_table_mapping(item, feed_name)
        
        elif artifact_type in ["procedure", "function"]:
            self.relational_store.upsert_technical_artifact({
                "artifact_type": "procedure",
                "name": item.get("name"),
                "source_system": item.get("source_system", "oracle"),
                "path": item.get("path", ""),
                "code_snippet": item.get("code_snippet", ""),
                "metadata": json.dumps(item.get("metadata", {}))
            })
    
    def _load_to_graph(self, item: Dict):
        """Load item to Neo4j graph"""
        artifact_type = item.get("artifact_type", "unknown")
        name = item.get("name", "")
        path = item.get("path", "")
        
        # Create node
        node_props = {
            "name": name,
            "path": path,
            "source_system": item.get("source_system", "oracle"),
            "artifact_type": artifact_type,
            "metadata": json.dumps(item.get("metadata", {}))
        }
        
        self.graph_store.add_node(name, ["Artifact", artifact_type.capitalize()], node_props)
        
        # Create relationships based on metadata
        metadata = item.get("metadata", {})
        
        # Downstream impacts
        if "downstream_impact" in metadata:
            for ds_table in metadata["downstream_impact"].get("downstream_tables", []):
                self.graph_store.add_edge(
                    path, ds_table, "FEEDS_INTO",
                    {"source": "impact_analysis"}
                )
        
        # Technical dependencies
        if "dependencies" in metadata:
            for dep in metadata["dependencies"]:
                self.graph_store.add_edge(
                    path, dep, "DEPENDS_ON",
                    {"source": "dependency"}
                )
    
    def _load_to_vector(self, item: Dict):
        """Generate embedding and load to ChromaDB"""
        if not self.embedder or not self.vector_store:
            return
        
        # Create text for embedding
        text_parts = [
            item.get("name", ""),
            item.get("artifact_type", ""),
            item.get("business_context", ""),
            item.get("code_snippet", "")[:500]  # First 500 chars
        ]
        text = " ".join(filter(None, text_parts))
        
        if not text.strip():
            return
        
        # Generate embedding
        embedding = self.embedder.generate_single(text)
        
        # Prepare metadata
        metadata = {
            "name": item.get("name", ""),
            "artifact_type": item.get("artifact_type", ""),
            "source_system": item.get("source_system", ""),
            "path": item.get("path", ""),
            "source": item.get("source", "unknown")
        }
        
        # Add to vector store
        self.vector_store.add(
            ids=[item.get("path", str(uuid.uuid4()))],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
    
    def _post_process(self, results: Dict[str, IngestionResult]):
        """Post-process: entity linking, graph enrichment"""
        if not self.linker or not self.graph_store:
            return
        
        # Collect all entities
        all_entities = []
        for result in results.values():
            for item in result.items:
                all_entities.append(item)
        
        if not all_entities:
            return
        
        # Link entities
        logger.info(f"Linking {len(all_entities)} entities...")
        links = self.linker.link_entities(all_entities)
        
        # Create links in graph
        for link in links:
            if link.confidence > 0.7:
                self.graph_store.add_edge(
                    link.extracted_entity,
                    link.linked_entity_id,
                    link.match_method.upper(),
                    {"confidence": link.confidence}
                )
        
        logger.info(f"Created {len([l for l in links if l.confidence > 0.7])} high-confidence links")


# Factory function
def create_ingestion_pipeline(config: Dict) -> IngestionPipeline:
    """Factory to create ingestion pipeline with all configurations"""
    
    pipeline_config = PipelineConfig(
        connectors=config.get("connectors", {}),
        parallel_feeds=config.get("parallel_feeds", True),
        max_workers=config.get("max_workers", 4),
        batch_size=config.get("batch_size", 100),
        generate_embeddings=config.get("generate_embeddings", True),
        update_graph=config.get("update_graph", True),
        update_vector_store=config.get("update_vector_store", True),
        update_relational=config.get("update_relational", True),
    )
    
    pipeline = IngestionPipeline(pipeline_config)
    return pipeline


# Example usage
if __name__ == "__main__":
    import yaml
    
    # Load config
    with open("config/settings.yaml") as f:
        config = yaml.safe_load(f)
    
    # Create pipeline
    pipeline = create_ingestion_pipeline(config)
    
    # Initialize stores (would be passed from main app)
    # pipeline.initialize(vector_store, graph_store, relational_store, embedder, linker)
    
    # Run ingestion
    # results = pipeline.run_full_ingestion(feed_names=["broadridge_trades", "ref_data_fees"])
    # print(json.dumps(results, indent=2, default=str))
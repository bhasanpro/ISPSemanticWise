"""
NetworkX Sync Connector - Syncs existing NetworkX observability graph
"""

import pickle
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from .base import BaseIngestionConnector, IngestionResult


class NetworkXSyncConnector(BaseIngestionConnector):
    """Connector to sync existing NetworkX observability graph"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.graph_path = Path(config.get("graph_path", "./data/networkx/observability_graph.gpickle"))
        self.sync_interval = config.get("sync_interval_seconds", 3600)
        self.enrich_with_ingested = config.get("enrich_with_ingested", True)
        self.graph = None
    
    def discover(self) -> List[str]:
        """Discover graph file"""
        if self.graph_path.exists():
            return [str(self.graph_path)]
        return []
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Load NetworkX graph from pickle"""
        try:
            with open(source, 'rb') as f:
                self.graph = pickle.load(f)
            
            logger.info(f"Loaded NetworkX graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            
            # Convert graph to items
            items = self._graph_to_items(self.graph)
            return items
        except Exception as e:
            logger.error(f"Failed to load NetworkX graph: {e}")
            raise
    
    def _graph_to_items(self, graph: nx.DiGraph) -> List[Dict[str, Any]]:
        """Convert NetworkX graph to standard items"""
        items = []
        
        # Nodes as technical artifacts
        for node_id, node_data in graph.nodes(data=True):
            items.append({
                "artifact_type": "networkx_node",
                "name": str(node_id),
                "source_system": "networkx",
                "path": f"networkx/{node_id}",
                "code_snippet": "",
                "metadata": {
                    "node_id": str(node_id),
                    **node_data,
                },
            })
        
        # Edges as transformations/dependencies
        for source, target, edge_data in graph.edges(data=True):
            items.append({
                "artifact_type": "networkx_edge",
                "name": f"{source} -> {target}",
                "source_system": "networkx",
                "path": f"networkx/{source}->{target}",
                "code_snippet": "",
                "metadata": {
                    "source": str(source),
                    "target": str(target),
                    **edge_data,
                },
            })
        
        return items
    
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform NetworkX data to standard format"""
        # Already in good format, add enrichment
        for item in raw_data:
            item.setdefault("source_system", "networkx")
            item.setdefault("metadata", {})
            item["metadata"]["synced_at"] = "auto"
        return raw_data
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to storage - this enriches the existing graph"""
        # If we have ingested data, enrich the graph
        if self.enrich_with_ingested:
            self._enrich_graph(transformed_data)
        
        # Save updated graph
        self._save_graph()
        
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )
    
    def _enrich_graph(self, ingested_data: List[Dict[str, Any]]):
        """Enrich NetworkX graph with ingested metadata"""
        if self.graph is None:
            return
        
        for item in ingested_data:
            artifact_type = item.get("artifact_type", "")
            path = item.get("path", "")
            metadata = item.get("metadata", {})
            
            # Try to match node
            node_id = path.replace("networkx/", "")
            if node_id in self.graph.nodes:
                # Enrich existing node
                self.graph.nodes[node_id].update({
                    "enriched_metadata": metadata,
                    "enriched_at": "auto",
                })
            else:
                # Add as new node if it's a business term or technical artifact
                if artifact_type in ["business_term", "technical_artifact", "transformation"]:
                    self.graph.add_node(node_id, **metadata)
    
    def _save_graph(self):
        """Save updated graph back to pickle"""
        if self.graph and self.graph_path:
            backup_path = self.graph_path.with_suffix('.gpickle.backup')
            self.graph_path.rename(backup_path)
            with open(self.graph_path, 'wb') as f:
                pickle.dump(self.graph, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Saved enriched NetworkX graph to {self.graph_path}")
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to storage"""
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )
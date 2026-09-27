"""
Ab Initio Connector - Parses Ab Initio graphs, transforms, and metadata
"""

import xml.etree.ElementTree as ET
import xmltodict
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

from .base import BaseIngestionConnector, IngestionResult


class AbInitioConnector(BaseIngestionConnector):
    """Connector for Ab Initio ETL graphs and transforms"""
    
    SUPPORTED_EXTENSIONS = {".mp", ".xfr", ".dml", ".xml", ".grf"}
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.graph_path = Path(config.get("graph_path", "/data/ab_initio/graphs"))
        self.xfr_path = Path(config.get("xfr_path", "/data/ab_initio/xfrs"))
        self.dml_path = Path(config.get("dml_path", "/data/ab_initio/dmls"))
        self.file_patterns = config.get("file_patterns", ["*.mp", "*.xfr", "*.dml", "*.xml"])
        self.batch_size = config.get("batch_size", 50)
        self.parse_timeout = config.get("parse_timeout_seconds", 300)
    
    def discover(self) -> List[str]:
        """Discover Ab Initio files"""
        files = []
        for pattern in self.file_patterns:
            for path in [self.graph_path, self.xfr_path, self.dml_path]:
                files.extend(path.rglob(pattern))
        return [str(f) for f in files]
    
    def extract(self, source: str) -> List[Dict[str, Any]]:
        """Extract raw data from Ab Initio file"""
        path = Path(source)
        items = []
        
        try:
            if path.suffix in {".mp", ".grf", ".xml"}:
                items = self._parse_graph_file(path)
            elif path.suffix == ".xfr":
                items = self._parse_transform_file(path)
            elif path.suffix == ".dml":
                items = self._parse_dml_file(path)
        except Exception as e:
            logger.error(f"Failed to extract {source}: {e}")
            raise
        
        return items
    
    def _parse_graph_file(self, path: Path) -> List[Dict[str, Any]]:
        """Parse Ab Initio graph (.mp/.grf/.xml)"""
        items = []
        
        try:
            # Try GraphML first
            if path.suffix == ".xml":
                tree = ET.parse(path)
                root = tree.getroot()
                graph_data = self._parse_graphml(root)
            else:
                # Ab Initio .mp files are binary, need Ab Initio SDK
                # For now, try as text/XML
                content = path.read_text(encoding='utf-8', errors='ignore')
                if content.strip().startswith("<"):
                    graph_data = self._parse_xml_graph(content)
                else:
                    logger.warning(f"Binary .mp file not parseable without SDK: {path}")
                    return []
            
            if graph_data:
                items.append({
                    "type": "ab_initio_graph",
                    "source_path": str(path),
                    "graph_name": path.stem,
                    "data": graph_data,
                })
        except Exception as e:
            logger.error(f"Failed to parse graph {path}: {e}")
        
        return items
    
    def _parse_graphml(self, root) -> Dict[str, Any]:
        """Parse GraphML format"""
        # Implement GraphML parsing
        return {"format": "graphml", "nodes": [], "edges": []}
    
    def _parse_xml_graph(self, content: str) -> Dict[str, Any]:
        """Parse Ab Initio XML graph format"""
        try:
            data = xmltodict.parse(content)
            return {"format": "ab_initio_xml", "data": data}
        except Exception as e:
            logger.error(f"XML parsing failed: {e}")
            return {"format": "ab_initio_xml", "raw": content[:10000]}
    
    def _parse_transform_file(self, path: Path) -> List[Dict[str, Any]]:
        """Parse .xfr transform file"""
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        # Parse Ab Initio transform syntax
        transforms = self._parse_xfr_content(content)
        
        return [{
            "type": "ab_initio_transform",
            "source_path": str(path),
            "transform_name": path.stem,
            "transforms": transforms,
        }]
    
    def _parse_xfr_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse Ab Initio transform (.xfr) content"""
        transforms = []
        
        # Simple regex-based parsing (replace with proper parser)
        # Ab Initio transform syntax: out.port :: transform(in.port);
        pattern = r'(\w+\.\w+)\s*::\s*([^;]+);'
        matches = re.findall(pattern, content)
        
        for out_port, logic in matches:
            transforms.append({
                "output_port": out_port.strip(),
                "logic": logic.strip(),
                "input_ports": self._extract_input_ports(logic),
            })
        
        return transforms
    
    def _extract_input_ports(self, logic: str) -> List[str]:
        """Extract input port references from transform logic"""
        # Simple extraction - improve with proper parser
        port_pattern = r'(?:in|out)\.(\w+)'
        return list(set(re.findall(port_pattern, logic)))
    
    def _parse_dml_file(self, path: Path) -> List[Dict[str, Any]]:
        """Parse .dml metadata file"""
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        return [{
            "type": "ab_initio_dml",
            "source_path": str(path),
            "record_name": path.stem,
            "raw_content": content,
        }]
    
    def transform(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform raw Ab Initio data to standard format"""
        transformed = []
        
        for item in raw_data:
            if item["type"] == "ab_initio_graph":
                transformed.extend(self._transform_graph(item))
            elif item["type"] == "ab_initio_transform":
                transformed.extend(self._transform_transforms(item))
            elif item["type"] == "ab_initio_dml":
                transformed.extend(self._transform_dml(item))
        
        return transformed
    
    def _transform_graph(self, item: Dict) -> List[Dict]:
        """Transform graph to standard artifacts"""
        artifacts = []
        graph_data = item.get("data", {})
        
        # Extract nodes as technical artifacts
        nodes = graph_data.get("nodes", [])
        for node in nodes:
            artifacts.append({
                "artifact_type": "graph_node",
                "name": node.get("name", ""),
                "source_system": "ab_initio",
                "path": f"{item['graph_name']}/{node.get('name', '')}",
                "code_snippet": str(node),
                "metadata": {
                    "graph_name": item["graph_name"],
                    "node_type": node.get("type", ""),
                    "component": node.get("component", ""),
                },
            })
        
        # Extract edges as transformations
        edges = graph_data.get("edges", [])
        for edge in edges:
            artifacts.append({
                "artifact_type": "transformation",
                "name": f"{edge.get('source', '')} -> {edge.get('target', '')}",
                "source_system": "ab_initio",
                "path": f"{item['graph_name']}/{edge.get('source', '')}->{edge.get('target', '')}",
                "code_snippet": str(edge),
                "metadata": {
                    "graph_name": item["graph_name"],
                    "source_port": edge.get("source_port", ""),
                    "target_port": edge.get("target_port", ""),
                },
            })
        
        return artifacts
    
    def _transform_transforms(self, item: Dict) -> List[Dict]:
        """Transform transforms to standard artifacts"""
        artifacts = []
        
        for transform in item.get("transforms", []):
            artifacts.append({
                "artifact_type": "transformation",
                "name": transform.get("output_port", ""),
                "source_system": "ab_initio",
                "path": f"{item['transform_name']}/{transform.get('output_port', '')}",
                "code_snippet": transform.get("logic", ""),
                "metadata": {
                    "transform_name": item["transform_name"],
                    "input_ports": transform.get("input_ports", []),
                },
            })
        
        return artifacts
    
    def _transform_dml(self, item: Dict) -> List[Dict]:
        """Transform DML to standard artifacts"""
        # Parse DML for record structure
        return [{
            "artifact_type": "record_definition",
            "name": item["record_name"],
            "source_system": "ab_initio",
            "path": f"dml/{item['record_name']}",
            "code_snippet": item["raw_content"],
            "metadata": {"source_path": item["source_path"]},
        }]
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> IngestionResult:
        """Load to vector DB and graph DB"""
        # TODO: Implement actual loading to ChromaDB and Neo4j
        return IngestionResult(
            job_id=self.job.job_id if self.job else "",
            success=True,
            items=transformed_data,
        )
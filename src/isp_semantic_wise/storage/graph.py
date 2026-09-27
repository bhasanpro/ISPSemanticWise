"""
Graph Store - Neo4j/NetworkX abstraction
"""

from typing import List, Dict, Any, Optional, Set
from loguru import logger

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class GraphStore:
    """Abstract graph store with Neo4j and NetworkX backends"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.provider = config.get("provider", "networkx")
        self.graph = None
        self.driver = None
        
        if self.provider == "neo4j":
            self._init_neo4j()
        elif self.provider == "networkx":
            self._init_networkx()
        else:
            raise ValueError(f"Unsupported graph provider: {self.provider}")
    
    def _init_neo4j(self):
        """Initialize Neo4j connection"""
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j driver not installed")
        
        uri = self.config.get("uri", "bolt://localhost:7687")
        user = self.config.get("user", "neo4j")
        password = self.config.get("password", "password")
        database = self.config.get("database", "neo4j")
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        logger.info("Neo4j connected")
    
    def _init_networkx(self):
        """Initialize NetworkX graph"""
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx not installed")
        
        import networkx as nx
        graph_path = self.config.get("graph_path", "./data/networkx/observability_graph.gpickle")
        
        import pickle
        if Path(graph_path).exists():
            with open(graph_path, 'rb') as f:
                self.graph = pickle.load(f)
            logger.info(f"Loaded NetworkX graph: {self.graph.number_of_nodes()} nodes")
        else:
            self.graph = nx.DiGraph()
            logger.info("Created new NetworkX graph")
    
    # ==========================================
    # NODE OPERATIONS
    # ==========================================
    
    def add_node(self, node_id: str, labels: List[str] = None, properties: Dict = None) -> bool:
        """Add node to graph"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    labels_str = ":" + ":".join(labels) if labels else ""
                    props = properties or {}
                    props_str = ", ".join([f"{k}: ${k}" for k in props.keys()])
                    query = f"CREATE (n{labels_str} {{{props_str}}}) SET n.id = $id"
                    params = {"id": node_id, **properties}
                    session.run(query, params)
            elif self.provider == "networkx":
                self.graph.add_node(node_id, **(properties or {}))
            return True
        except Exception as e:
            logger.error(f"Failed to add node: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get node by ID"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    result = session.run("MATCH (n) WHERE n.id = $id RETURN n", id=node_id)
                    record = result.single()
                    if record:
                        return dict(record["n"])
            elif self.provider == "networkx":
                if self.graph.has_node(node_id):
                    return dict(self.graph.nodes[node_id])
        except Exception as e:
            logger.error(f"Failed to get node: {e}")
        return None
    
    def update_node(self, node_id: str, properties: Dict) -> bool:
        """Update node properties"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    props_str = ", ".join([f"n.{k} = ${k}" for k in properties.keys()])
                    query = f"MATCH (n) WHERE n.id = $id SET {props_str}"
                    params = {"id": node_id, **properties}
                    session.run(query, params)
            elif self.provider == "networkx":
                if self.graph.has_node(node_id):
                    self.graph.nodes[node_id].update(properties)
            return True
        except Exception as e:
            logger.error(f"Failed to update node: {e}")
            return False
    
    def delete_node(self, node_id: str) -> bool:
        """Delete node"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    session.run("MATCH (n) WHERE n.id = $id DETACH DELETE n", id=node_id)
            elif self.provider == "networkx":
                if self.graph.has_node(node_id):
                    self.graph.remove_node(node_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete node: {e}")
            return False
    
    # ==========================================
    # EDGE OPERATIONS
    # ==========================================
    
    def add_edge(self, source_id: str, target_id: str, 
                 relationship: str = "RELATES_TO", properties: Dict = None) -> bool:
        """Add edge between nodes"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    props = properties or {}
                    props_str = ", ".join([f"r.{k} = ${k}" for k in props.keys()]) if properties else ""
                    query = f"""
                        MATCH (a), (b) 
                        WHERE a.id = $source AND b.id = $target
                        CREATE (a)-[r:{relationship} {{{','.join([f'{k}: ${k}' for k in properties.keys()])}}}]->(b)
                    """ if properties else f"""
                        MATCH (a), (b) 
                        WHERE a.id = $source AND b.id = $target
                        CREATE (a)-[r:{relationship}]->(b)
                    """
                    params = {"source": node_id, "target": target_id, **(properties or {})}
                    session.run(query, params)
            elif self.provider == "networkx":
                import networkx as nx
                if isinstance(self.graph, nx.DiGraph):
                    self.graph.add_edge(node_id, target_id, 
                                      relationship=relationship, 
                                      **(properties or {}))
                else:
                    self.graph.add_edge(node_id, target_id,
                                      relationship=relationship,
                                      **(properties or {}))
            return True
        except Exception as e:
            logger.error(f"Failed to add edge: {e}")
            return False
    
    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """Get neighboring nodes"""
        neighbors = []
        try:
            if self.provider == "neo4j":
                dir_clause = ""
                if direction == "outgoing":
                    dir_clause = "->"
                elif direction == "incoming":
                    dir_clause = "<-"
                
                query = f"MATCH (a)-[r{direction_clause}]-(b) WHERE a.id = $id RETURN b.id"
                with self.driver.session(database=self.database) as session:
                    result = session.run(query, id=node_id)
                    neighbors = [record["b.id"] for record in result]
            elif self.provider == "networkx":
                if direction in ["outgoing", "both"]:
                    neighbors.extend(self.graph.successors(node_id))
                if direction in ["incoming", "both"]:
                    neighbors.extend(self.graph.predecessors(node_id))
        except Exception as e:
            logger.error(f"Failed to get neighbors: {e}")
        return list(set(neighbors))
    
    def successors(self, node_id: str) -> List[str]:
        """Get successor nodes"""
        return self.get_neighbors(node_id, "outgoing")
    
    def predecessors(self, node_id: str) -> List[str]:
        """Get predecessor nodes"""
        return self.get_neighbors(node_id, "incoming")
    
    # ==========================================
    # TRAVERSAL
    # ==========================================
    
    def shortest_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between nodes"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    result = session.run("""
                        MATCH p = shortestPath((a)-[*]-(b))
                        WHERE a.id = $source AND b.id = $target
                        RETURN p
                    """, source=source, target=target)
                    record = result.single()
                    if record:
                        return [node["id"] for node in record["p"].nodes]
            elif self.provider == "networkx":
                import networkx as nx
                if nx.has_path(self.graph, node_id, target):
                    return nx.shortest_path(self.graph, source, target)
        except Exception as e:
            logger.error(f"Failed to find path: {e}")
        return []
    
    def traverse_downstream(self, start_node: str, max_depth: int = 5) -> List[str]:
        """Traverse downstream from node"""
        visited = set()
        current = {node_id}
        downstream = []
        
        for _ in range(max_depth):
            next_level = set()
            for node in current:
                if node in visited:
                    continue
                visited.add(node)
                
                neighbors = self.successors(node)
                for n in neighbors:
                    if n not in visited:
                        downstream.append(n)
                        next_level.add(n)
            
            current = next_level
            if not current:
                break
        
        return downstream
    
    def traverse_upstream(self, start_node: str, max_depth: int = 5) -> List[str]:
        """Traverse upstream from node"""
        visited = set()
        current = {node_id}
        upstream = []
        
        for _ in range(max_depth):
            next_level = set()
            for node in current:
                if node in visited:
                    continue
                visited.add(node)
                
                neighbors = self.predecessors(node)
                for n in neighbors:
                    if n not in visited:
                        upstream.append(n)
                        next_level.add(n)
            
            current = next_level
            if not current:
                break
        
        return upstream
    
    # ==========================================
    # UTILITIES
    # ==========================================
    
    def get_stats(self) -> Dict:
        """Get graph statistics"""
        try:
            if self.provider == "neo4j":
                with self.driver.session(database=self.database) as session:
                    nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
                    edges = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
                    return {"nodes": nodes, "edges": edges}
            elif self.provider == "networkx":
                return {
                    "nodes": self.graph.number_of_nodes(),
                    "edges": self.graph.number_of_edges(),
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
        return {"nodes": 0, "edges": 0}
    
    def close(self):
        """Close connections"""
        if self.provider == "neo4j" and self.driver:
            self.driver.close()
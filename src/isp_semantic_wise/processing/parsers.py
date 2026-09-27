"""
Code Parsers - Tree-sitter based parsers for different languages
"""

import tree_sitter
from tree_sitter import Language, Parser
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from loguru import logger


class CodeParser(ABC):
    """Abstract base class for code parsers"""
    
    def __init__(self):
        self.parser = Parser()
        self.language = None
    
    @abstractmethod
    def get_language(self) -> Language:
        """Get tree-sitter language"""
        pass
    
    def parse(self, code: str) -> tree_sitter.Tree:
        """Parse code and return AST"""
        if self.language is None:
            self.language = self.get_language()
        self.parser.set_language(self.language)
        return self.parser.parse(bytes(code, "utf8"))
    
    @abstractmethod
    def extract_entities(self, tree: tree_sitter.Tree, code: str) -> List[Dict]:
        """Extract entities from parsed tree"""
        pass
    
    def extract_functions(self, tree: tree_sitter.Tree, code: str) -> List[Dict]:
        """Extract function/procedure definitions"""
        return []
    
    def extract_variables(self, tree: tree_sitter.Tree, code: str) -> List[Dict]:
        """Extract variable declarations"""
        return []


class PLSQLParser(CodeParser):
    """Parser for Oracle PL/SQL"""
    
    def get_language(self) -> Language:
        # Tree-sitter PL/SQL - may need custom grammar
        # For now, use a fallback
        try:
            import tree_sitter_plsql
            return Language(tree_sitter_plsql.language())
        except ImportError:
            logger.warning("tree-sitter-plsql not available, using fallback")
            return None
    
    def extract_entities(self, tree, code: str) -> List[Dict]:
        """Extract PL/SQL entities"""
        entities = []
        
        # Fallback to regex-based extraction if tree-sitter not available
        if tree is None:
            return self._regex_extract(code)
        
        # Tree-sitter extraction
        cursor = tree.walk()
        entities = self._traverse_for_entities(cursor, code)
        
        return entities
    
    def _regex_extract(self, code: str) -> List[Dict]:
        """Fallback regex-based extraction"""
        import re
        
        entities = []
        
        # Procedure/Function
        proc_pattern = r'(PROCEDURE|FUNCTION)\s+(\w+)\s*\([^)]*\)\s*(IS|AS)'
        for match in re.finditer(proc_pattern, code, re.IGNORECASE):
            entities.append({
                "type": "procedure" if match.group(1).upper() == "PROCEDURE" else "function",
                "name": match.group(2),
                "signature": match.group(0),
            })
        
        # Tables referenced
        table_pattern = r'\b(FROM|JOIN|UPDATE|INSERT INTO|DELETE FROM)\s+([A-Z_][A-Z0-9_]*)'
        for match in re.finditer(table_pattern, code, re.IGNORECASE):
            entities.append({
                "type": "table_reference",
                "name": match.group(2).upper(),
                "context": match.group(0),
            })
        
        # Columns
        col_pattern = r'\b([A-Z_][A-Z0-9_]*)\.([A-Z_][A-Z0-9_]*)\b'
        for match in re.finditer(col_pattern, code):
            entities.append({
                "type": "column_reference",
                "table": match.group(1).upper(),
                "column": match.group(2).upper(),
            })
        
        return entities
    
    def _traverse_for_entities(self, cursor, code: str) -> List[Dict]:
        """Traverse tree-sitter AST for entities"""
        entities = []
        
        def visit(node):
            if node.type in ("procedure_declaration", "function_declaration"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    entities.append({
                        "type": "procedure" if "procedure" in node.type else "function",
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "start_line": node.start_point[0],
                        "end_line": node.end_point[0],
                    })
            elif node.type == "table_reference":
                # Extract table name
                pass
            
            for child in node.children:
                visit(child)
        
        visit(cursor.node)
        return entities


class PythonParser(CodeParser):
    """Parser for Python code"""
    
    def get_language(self) -> Language:
        import tree_sitter_python
        return Language(tree_sitter_python.language())
    
    def extract_entities(self, tree, code: str) -> List[Dict]:
        entities = []
        
        def visit(node):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    entities.append({
                        "type": "function",
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "start_line": node.start_point[0],
                        "end_line": node.end_point[0],
                        "args": self._extract_args(node, code),
                    })
            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    entities.append({
                        "type": "class",
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "start_line": node.start_point[0],
                        "end_line": node.end_point[0],
                    })
            elif node.type == "import_statement" or node.type == "import_from_statement":
                entities.append({
                    "type": "import",
                    "text": code[node.start_byte:node.end_byte],
                })
            
            for child in node.children:
                visit(child)
        
        visit(tree.root_node)
        return entities
    
    def _extract_args(self, node, code: str) -> List[str]:
        """Extract function arguments"""
        args = []
        params = node.child_by_field_name("parameters")
        if params:
            for child in params.children:
                if child.type == "identifier":
                    args.append(code[child.start_byte:child.end_byte])
        return args


class BashParser(CodeParser):
    """Parser for Bash/KSH shell scripts"""
    
    def get_language(self) -> Language:
        import tree_sitter_bash
        return Language(tree_sitter_bash.language())
    
    def extract_entities(self, tree, code: str) -> List[Dict]:
        entities = []
        
        def visit(node):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    entities.append({
                        "type": "function",
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "start_line": node.start_point[0],
                    })
            elif node.type == "variable_assignment":
                name_node = node.child_by_field_name("name")
                value_node = node.child_by_field_name("value")
                if name_node:
                    entities.append({
                        "type": "variable",
                        "name": code[name_node.start_byte:name_node.end_byte],
                        "value": code[value_node.start_byte:value_node.end_byte] if value_node else "",
                    })
            elif node.type == "command":
                # Extract command name
                for child in node.children:
                    if child.type == "command_name":
                        entities.append({
                            "type": "command",
                            "name": code[child.start_byte:child.end_byte],
                            "line": node.start_point[0],
                        })
                        break
            
            for child in node.children:
                visit(child)
        
        visit(tree.root_node)
        return entities


class AbInitioParser(CodeParser):
    """Parser for Ab Initio transforms and graphs"""
    
    def get_language(self) -> Language:
        # No tree-sitter grammar for Ab Initio yet
        # Use custom parsing
        return None
    
    def parse(self, code: str):
        # Return mock tree for compatibility
        return None
    
    def extract_entities(self, tree, code: str) -> List[Dict]:
        """Extract Ab Initio entities using custom parsing"""
        import re
        
        entities = []
        
        # Transform: out.port :: logic;
        transform_pattern = r'(\w+\.\w+)\s*::\s*([^;]+);'
        for match in re.finditer(transform_pattern, code):
            entities.append({
                "type": "transform",
                "output_port": match.group(1).strip(),
                "logic": match.group(2).strip(),
                "input_ports": self._extract_input_ports(match.group(2)),
            })
        
        # Graph components
        comp_pattern = r'COMPONENT\s+(\w+)'
        for match in re.finditer(comp_pattern, code, re.IGNORECASE):
            entities.append({
                "type": "component",
                "name": match.group(1),
            })
        
        return entities
    
    def _extract_input_ports(self, logic: str) -> List[str]:
        import re
        port_pattern = r'(?:in|out)\.(\w+)'
        return list(set(re.findall(port_pattern, logic)))


# Factory
def get_parser(language: str) -> CodeParser:
    """Get parser for language"""
    parsers = {
        "plsql": PLSQLParser(),
        "sql": PLSQLParser(),
        "python": PythonParser(),
        "py": PythonParser(),
        "bash": BashParser(),
        "sh": BashParser(),
        "ksh": BashParser(),
        "ab_initio": AbInitioParser(),
        "xfr": AbInitioParser(),
    }
    return parsers.get(language.lower(), CodeParser())
"""
Semantic Chunkers - Code and document chunking strategies
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from loguru import logger


class BaseChunker(ABC):
    """Abstract base class for chunkers"""
    
    @abstractmethod
    def chunk(self, content: str, metadata: Dict = None) -> List[Dict]:
        """Chunk content into pieces"""
        pass


class SemanticChunker(BaseChunker):
    """Semantic-aware chunking that respects code structure"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.chunk_size = self.config.get("chunk_size", 100)
        self.chunk_overlap = self.config.get("chunk_overlap", 20)
        self.min_chunk_size = self.config.get("min_chunk_size", 20)
    
    def chunk(self, content: str, metadata: Dict = None) -> List[Dict]:
        """Chunk content semantically"""
        # Detect content type and delegate
        if self._is_code(content):
            return self._chunk_code(content, metadata)
        else:
            return self._chunk_document(content, metadata)
    
    def _is_code(self, content: str) -> bool:
        """Heuristic to detect code vs documentation"""
        code_indicators = [
            "CREATE PROCEDURE", "CREATE FUNCTION", "CREATE TABLE",
            "def ", "function ", "SELECT ", "INSERT ", "UPDATE ",
            "import ", "from ", "class ", "def ",
            "#!/bin/bash", "#!/bin/ksh", "export ", "if [",
        ]
        content_upper = content.upper()
        return any(indicator in content_upper for indicator in code_indicators)
    
    def _chunk_code(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk code by functions/procedures"""
        chunks = []
        lines = content.split('\n')
        
        # Simple function/procedure boundary detection
        current_chunk = []
        current_start = 0
        brace_count = 0
        in_function = False
        
        for i, line in enumerate(lines):
            current_chunk.append(line)
            
            # Track braces for function boundaries
            brace_count += line.count('{') - line.count('}')
            brace_count += line.count('BEGIN') - line.count('END')
            
            # Detect function start
            stripped = line.strip().upper()
            if any(stripped.startswith(kw) for kw in ['CREATE PROCEDURE', 'CREATE FUNCTION', 'FUNCTION ', 'PROCEDURE ', 'def ']):
                if in_function and current_chunk:
                    # Save previous chunk
                    chunks.append(self._make_chunk(current_chunk, current_start, i-1, metadata))
                    current_chunk = [line]
                    current_start = len('\n'.join(lines[:i]))
                else:
                    in_function = True
            
            # Detect function end
            if in_function and brace_count <= 0 and current_chunk:
                # Check for END; or }
                if any(kw in line.upper() for kw in ['END;', 'END ;', '}']):
                    chunks.append(self._make_chunk(current_chunk, current_start, i, metadata))
                    current_chunk = []
                    in_function = False
        
        # Remaining
        if current_chunk:
            chunks.append(self._make_chunk(current_chunk, current_start, len(lines)-1, metadata))
        
        # If no functions found, fall back to fixed-size chunking
        if not chunks:
            return self._fixed_chunk(content, metadata)
        
        return chunks
    
    def _make_chunk(self, lines: List[str], start: int, end: int, metadata: Dict) -> Dict:
        """Create chunk dict"""
        content = '\n'.join(lines)
        return {
            "content": content,
            "start_line": metadata.get("start_line", 0) + start if metadata else start,
            "end_line": metadata.get("start_line", 0) + end if metadata else end,
            "metadata": {**(metadata or {}), "chunk_type": "code_function"},
        }
    
    def _chunk_document(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk document by sections/paragraphs"""
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        current_start = 0
        
        for i, para in enumerate(paragraphs):
            if len(current_chunk) + len(para) > self.chunk_size * 10:  # Approximate chars
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": {**(metadata or {}), "chunk_type": "document_section"},
                    })
                    current_chunk = para
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": {**(metadata or {}), "chunk_type": "document_section"},
            })
        
        return chunks
    
    def _fixed_chunk(self, content: str, metadata: Dict) -> List[Dict]:
        """Fixed-size chunking fallback"""
        chunks = []
        words = content.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            if len(chunk_words) < self.min_chunk_size:
                break
            chunks.append({
                "content": " ".join(chunk_words),
                "metadata": {**(metadata or {}), "chunk_type": "fixed"},
            })
        
        return chunks


class CodeChunker(BaseChunker):
    """Code-specific chunker with AST awareness"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_chunk_size = config.get("max_chunk_size", 150)
        self.min_chunk_size = config.get("min_chunk_size", 20)
    
    def chunk(self, content: str, metadata: Dict = None) -> List[Dict]:
        """Chunk code using language-specific strategies"""
        # For now, delegate to semantic chunker
        chunker = SemanticChunker(self.config)
        return chunker.chunk(content, metadata)


class DocChunker(BaseChunker):
    """Document chunker for non-code content"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.chunk_size = config.get("chunk_size", 500)
        self.chunk_overlap = config.get("chunk_overlap", 50)
    
    def chunk(self, content: str, metadata: Dict = None) -> List[Dict]:
        """Chunk document by headers and paragraphs"""
        chunks = []
        
        # Split by markdown headers first
        import re
        sections = re.split(r'(^|\n)(#{1,6}\s+.+)', content)
        
        current_section = ""
        current_header = ""
        
        for part in sections:
            if re.match(r'^#{1,6}\s+', part.strip()):
                # Save previous section
                if current_section.strip():
                    chunks.append({
                        "content": f"{current_header}\n{current_section}".strip(),
                        "metadata": {**(metadata or {}), "header": current_header.strip(), "chunk_type": "document_section"},
                    })
                current_header = part.strip()
                current_section = ""
            else:
                current_section += part
        
        # Last section
        if current_section.strip():
            chunks.append({
                "content": f"{current_header}\n{current_section}".strip(),
                "metadata": {**(metadata or {}), "header": current_header.strip(), "chunk_type": "document_section"},
            })
        
        # If no headers, fall back to paragraph chunking
        if not chunks:
            return self._paragraph_chunk(content, metadata)
        
        return chunks
    
    def _paragraph_chunk(self, content: str, metadata: Dict) -> List[Dict]:
        """Chunk by paragraphs with overlap"""
        chunks = []
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) > self.chunk_size * 4:  # Approximate chars
                if current_chunk:
                    chunks.append({
                        "content": current_chunk,
                        "metadata": {**(metadata or {}), "chunk_type": "document_paragraph"},
                    })
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        if current_chunk:
            chunks.append({
                "content": current_chunk,
                "metadata": {**(metadata or {}), "chunk_type": "document_paragraph"},
            })
        
        return chunks


def get_chunker(chunker_type: str, config: Dict = None) -> BaseChunker:
    """Factory for chunkers"""
    chunkers = {
        "semantic": SemanticChunker,
        "code": CodeChunker,
        "document": DocChunker,
        "doc": DocChunker,
    }
    return chunkers.get(chunker_type, SemanticChunker)(config)
"""
Data models for AST analysis.

This module contains all the data structures used for representing
AST nodes and relationships across all supported languages.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ASTNode:
    """Represents a node in the AST with metadata and content."""

    id: int
    repo_id: str
    type: str  # 'file', 'class', 'function', 'variable', etc.
    path: Optional[str] = None
    name: str = ""
    content: str = ""
    start_line: int = -1
    end_line: int = -1
    content_hash: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert node to dictionary for serialization."""
        return {
            "id": self.id,
            "repo_id": self.repo_id,
            "type": self.type,
            "path": self.path,
            "name": self.name,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }


@dataclass
class ASTEdge:
    """Represents a relationship between two AST nodes."""

    from_id: int
    to_id: int
    type: str  # 'contains', 'imports', 'calls', etc.
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert edge to dictionary for serialization."""
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "type": self.type,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisResult:
    """Container for analysis results."""

    language: str
    nodes: List[ASTNode]
    edges: List[ASTEdge]
    imports: Dict[str, str] = field(default_factory=dict)
    function_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert result to dictionary for serialization."""
        return {
            "language": self.language,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "imports": self.imports,
            "function_count": self.function_count,
            "error": self.error,
        }

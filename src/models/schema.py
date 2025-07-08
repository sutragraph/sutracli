"""
Pydantic models for tree-sitter JSON parsing and SQLite graph representation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CodeNode(BaseModel):
    """Represents a node in the parsed tree-sitter JSON."""
    id: int
    type: str
    name: Optional[str] = None
    file: Optional[str] = None
    path: Optional[str] = None
    lines: Optional[List[int]] = None  # Will store [start_line, end_line]
    content: Optional[str] = None  # Changed from code_snippet to content
    content_hash: Optional[str] = None  # Added content_hash field from tree-sitter

    # Project identification fields
    project_name: Optional[str] = None
    project_version: Optional[str] = None

    # Allow additional fields from tree-sitter
    model_config = {"extra": "allow"}


class CodeEdge(BaseModel):
    """Represents an edge/relationship in the parsed tree-sitter JSON."""
    from_id: int
    to_id: Optional[int] = None  # Made optional to handle external references
    type: str

    # Project identification fields
    project_name: Optional[str] = None

    # Allow additional fields from tree-sitter
    model_config = {"extra": "allow"}


class Project(BaseModel):
    """Represents a project/codebase being analyzed."""

    name: str
    version: Optional[str] = "1.0.0"
    description: Optional[str] = None
    language: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    source_file: Optional[str] = None  # Path to the JSON file


class ParsedCodebase(BaseModel):
    """Container for parsed tree-sitter data."""
    nodes: List[CodeNode]
    edges: List[CodeEdge]
    statistics: Optional[Dict[str, Any]] = None
    project: Optional[Project] = None


class SQLiteNode(BaseModel):
    """Represents a node ready for SQLite insertion."""

    node_id: int  # Original tree-sitter node ID
    project_id: int  # Reference to project table
    node_type: str
    name: Optional[str] = None
    file_hash_id: Optional[int] = None
    lines: Optional[List[int]] = None  # [start_line, end_line]
    code_snippet: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class SQLiteRelationship(BaseModel):
    """Represents a relationship ready for SQLite insertion."""

    from_node_id: int
    to_node_id: Optional[int]
    project_id: int  # Reference to project table
    relationship_type: str
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GraphData(BaseModel):
    """Container for processed graph data ready for database insertion."""
    nodes: List[SQLiteNode]
    relationships: List[SQLiteRelationship]


class FileHash(BaseModel):
    """Represents a file hash entry for tracking file content changes."""

    file_hash_id: Optional[int] = None 
    project_id: int  
    file_path: str
    content_hash: str  
    file_size: Optional[int] = None
    language: Optional[str] = None  # Added language field
    name: Optional[str] = None  # Added name field (filename)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProjectInfo(BaseModel):
    """Information about a project in the multi-project system."""
    name: str
    description: Optional[str] = None
    source_files: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    version: Optional[str] = None
    language: Optional[str] = None
    repository_url: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MultiProjectData(BaseModel):
    """Container for multiple projects data."""
    projects: Dict[str, ProjectInfo]
    graph_data: Dict[str, GraphData]  # project_name -> GraphData

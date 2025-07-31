"""
Pydantic models for code parsing and SQLite graph representation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class File(BaseModel):
    """Represents a file in the code extraction."""
    id: int  # CRC32 hash ID
    project_id: int
    file_path: str
    language: str
    content: str
    content_hash: str


class CodeBlock(BaseModel):
    """Represents a code block extracted from parsing."""
    id: int  # Incremental ID
    file_id: int
    parent_block_id: Optional[int] = None
    type: str  # import, function, class, variable, interface, enum, export
    name: str
    content: str
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    children: List["CodeBlock"] = Field(default_factory=list)


class Relationship(BaseModel):
    """Represents a relationship between files or blocks."""
    source_id: int
    target_id: int
    type: str  # import, calls, extends, implements, references
    metadata: Optional[Dict[str, Any]] = None


class Project(BaseModel):
    """Represents a project/codebase being analyzed."""
    name: str
    version: Optional[str] = "1.0.0"


class ExtractionData(BaseModel):
    """Container for complete code extraction data from JSON export."""
    metadata: Dict[str, Any]  # Export metadata (timestamp, version, etc.)
    files: Dict[str, "FileData"]  # file_path -> file data


class FileData(BaseModel):
    """Represents file data from code extraction JSON."""
    id: int
    file_path: str
    language: str
    content: str
    content_hash: str
    blocks: List[CodeBlock]
    relationships: List[Relationship]


# Update forward references
CodeBlock.model_rebuild()
ExtractionData.model_rebuild()

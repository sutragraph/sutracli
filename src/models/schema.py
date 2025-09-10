"""
Pydantic models for database and application-level operations.
Contains all core data models for the indexer and application.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BlockType(Enum):
    """Types of code blocks that can be extracted."""

    ENUM = "enum"
    VARIABLE = "variable"
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    TYPE = "type"
    IMPORT = "import"
    EXPORT = "export"


class CodeBlock(BaseModel):
    """Represents a code block extracted from AST."""

    type: BlockType
    name: str
    content: str
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    id: int = 0  # Will be set by extractor
    children: List["CodeBlock"] = Field(default_factory=list)

    # Database operation fields - used during insertion to maintain relationships
    file_id: Optional[int] = None  # ID of the file this block belongs to
    parent_block_id: Optional[int] = None  # ID of the parent block for nested blocks


class Relationship(BaseModel):
    """Represents a relationship between two files."""

    source_id: int  # ID of the source file
    target_id: int  # ID of the target file
    import_content: str  # The original import statement
    symbols: List[str] = []  # Symbols imported (optional, default empty list)
    type: str = "import"  # Type of relationship (default: import)


class FileData(BaseModel):
    """Represents file data from code extraction."""

    id: int
    file_path: str
    language: str
    content: str
    content_hash: str
    blocks: List[CodeBlock]
    relationships: List[Relationship]
    unsupported: bool = False  # True if file type is not supported by any extractor


class ExtractionData(BaseModel):
    """Container for complete code extraction data from JSON export."""

    metadata: Dict[str, Any]  # Export metadata (timestamp, version, etc.)
    files: Dict[str, FileData]  # file_path -> file data


class File(BaseModel):
    """Represents a file in the database with project association."""

    id: int  # CRC32 hash ID
    project_id: int  # Database foreign key
    file_path: str
    language: str
    content: str
    content_hash: str


class Project(BaseModel):
    """Represents a project/codebase in the database."""

    id: int  # Database ID
    name: str
    path: str
    description: str
    created_at: str
    updated_at: str
    cross_indexing_done: bool = False  # Whether cross-indexing is completed


CodeBlock.model_rebuild()

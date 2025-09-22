"""
Sutra Memory Manager Models

Data classes and enums for the memory management system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from baml_client.types import TracedElement, UntracedElement


class TaskStatus(Enum):
    """Task status enumeration"""

    PENDING = "pending"
    CURRENT = "current"
    COMPLETED = "completed"


@dataclass
class Task:
    """Task representation"""

    id: str
    description: str
    status: TaskStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CodeSnippet:
    """Code snippet representation with comprehensive trace chain analysis"""

    id: str
    file_path: str
    start_line: int
    end_line: int
    description: str
    content: str = ""  # Actual code content (main snippet only)
    is_traced: bool = False  # Whether trace chains have been fully analyzed
    root_elements: List[TracedElement] = field(
        default_factory=list
    )  # List of root-level traced elements
    # Code elements that still need trace chain analysis
    needs_tracing: List[UntracedElement] = field(default_factory=list)
    # High-level summary of complete trace chains (e.g., "validation → obj.property → dataCheck → db_query")
    call_chain_summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FileChange:
    """File change representation"""

    path: str
    operation: str  # modified, deleted, added
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HistoryEntry:
    """History entry representation"""

    timestamp: datetime
    summary: str
    iteration_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_result: Optional[dict] = None
    validation_result: Optional[dict] = None
    user_query: Optional[str] = None

    def __post_init__(self):
        if self.iteration_id is None:
            self.iteration_id = str(int(self.timestamp.timestamp()))

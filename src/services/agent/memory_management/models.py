"""
Sutra Memory Manager Models

Data classes and enums for the memory management system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

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
    description: str = ""
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


class MemorySection(Enum):
    """Memory section enumeration for type-safe section operations"""

    TASKS = "tasks"
    CODE_SNIPPETS = "code_snippets"
    HISTORY = "history"
    FILE_CHANGES = "file_changes"
    COUNTERS = "counters"
    FEEDBACK_SECTION = "feedback_section"
    PROJECT_INFO = "project_info"

    @classmethod
    def all_sections(cls) -> Set[str]:
        """Get all section names as a set"""
        return {section.value for section in cls}


@dataclass
class MemorySectionData:
    """Memory section data container"""

    tasks: Dict[str, Task] = field(default_factory=dict)
    code_snippets: Dict[str, CodeSnippet] = field(default_factory=dict)
    history: List[HistoryEntry] = field(default_factory=list)
    file_changes: List[FileChange] = field(default_factory=list)
    counters: Dict[str, int] = field(default_factory=dict)
    feedback_section: Optional[str] = None
    project_info: Optional[str] = None

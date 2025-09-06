"""
Sutra Memory Manager Models

Data classes and enums for the memory management system.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


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
    """Code snippet representation"""

    id: str
    file_path: str
    start_line: int
    end_line: int
    description: str
    content: str = ""  # Actual code content
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

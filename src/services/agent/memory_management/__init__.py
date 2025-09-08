"""
Sutra Memory Management Package

This package provides modular memory management functionality for the Sutra system.

Components:
- Models: Data classes and enums (Task, CodeSnippet, etc.)
- Memory Operations: Core task and code snippet management
- XML Processor: XML parsing and processing
- State Persistence: Import/export functionality
- Memory Formatter: LLM context formatting
- Code Fetcher: Database code retrieval

Main Interface:
- SutraMemoryManager: Main orchestrator class that combines all components
"""

from .sutra_memory_manager import (
    SutraMemoryManager,
)

from .models import TaskStatus, Task, CodeSnippet, FileChange, HistoryEntry
from .memory_operations import MemoryOperations
from .state_persistence import StatePersistence
from .memory_formatter import MemoryFormatter, clean_sutra_memory_content
from .code_fetcher import CodeFetcher
from .memory_updater import MemoryUpdater

__all__ = [
    # Main interface
    "SutraMemoryManager",
    # Models
    "TaskStatus",
    "Task",
    "CodeSnippet",
    "FileChange",
    "HistoryEntry",
    # Individual components (for advanced usage)
    "MemoryOperations",
    "StatePersistence",
    "MemoryFormatter",
    "CodeFetcher",
    "MemoryUpdater",
    # Utility functions
    "clean_sutra_memory_content",
]

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

# Import the new modular SutraMemoryManager
from .sutra_memory_manager import (
    SutraMemoryManager,
    TaskStatus,
    Task,
    CodeSnippet,
    FileChange,
    HistoryEntry,
    clean_sutra_memory_content,
)

# Import individual components for advanced usage
from .models import TaskStatus, Task, CodeSnippet, FileChange, HistoryEntry
from .memory_operations import MemoryOperations
from .xml_processor import XMLProcessor
from .state_persistence import StatePersistence
from .memory_formatter import MemoryFormatter, clean_sutra_memory_content
from .code_fetcher import CodeFetcher

# Export all public interfaces
__all__ = [
    # Main interface
    'SutraMemoryManager',
    
    # Models
    'TaskStatus',
    'Task',
    'CodeSnippet', 
    'FileChange',
    'HistoryEntry',
    
    # Individual components (for advanced usage)
    'MemoryOperations',
    'XMLProcessor',
    'StatePersistence',
    'MemoryFormatter',
    'CodeFetcher',
    
    # Utility functions
    'clean_sutra_memory_content',
]
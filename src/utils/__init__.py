"""
Utility functions module initialization.
Includes utilities moved from indexer.utils for better organization.
"""

from .helpers import (
    load_json_file,
    normalize_node_type,
    normalize_relationship_type,
    chunk_list,
)
from .system_utils import (
    get_operating_system,
    get_default_shell,
    get_home_directory,
    get_current_directory,
)

# File utilities (moved from indexer.utils)
from .file_utils import (
    get_language_from_extension,
    should_ignore_file,
    should_ignore_directory,
    is_text_file,
    read_file_content,
)

# Patterns and configurations (moved from indexer.utils)
from .ignore_patterns import IGNORE_FILE_PATTERNS, IGNORE_DIRECTORY_PATTERNS
from .langauge_extension_map import LANGUAGE_EXTENSION_MAP

# JSON serialization utilities (moved from indexer.utils)
from .json_serializer import make_json_serializable

# Incremental hash utilities (moved from indexer.utils)
from .incremental_hash import IncrementalHashGenerator

__all__ = [
    # Original utils
    "load_json_file",
    "normalize_node_type",
    "normalize_relationship_type",
    "chunk_list",
    "get_operating_system",
    "get_default_shell",
    "get_home_directory",
    "get_current_directory",
    # File utilities (moved from indexer.utils)
    "get_language_from_extension",
    "should_ignore_file",
    "should_ignore_directory",
    "is_text_file",
    "read_file_content",
    # JSON serialization utilities
    "make_json_serializable",
    # Patterns and configurations
    "IGNORE_FILE_PATTERNS",
    "IGNORE_DIRECTORY_PATTERNS",
    "LANGUAGE_EXTENSION_MAP",
    # Incremental hash utilities
    "IncrementalHashGenerator",
]

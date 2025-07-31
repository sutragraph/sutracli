"""
Utils package for AST Parser

This package provides utility functions and configurations for the AST parser.
"""

from .file_utils import (
    get_language_from_extension,
    should_ignore_file,
    should_ignore_directory,
    is_text_file,
    read_file_content,
)

from .ignore_patterns import IGNORE_FILE_PATTERNS, IGNORE_DIRECTORY_PATTERNS

from .langauge_extension_map import LANGUAGE_EXTENSION_MAP

from .json_serializer import make_json_serializable

__all__ = [
    # File utilities
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
]

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

from .supported_languages import SUPPORTED_LANGUAGES

__all__ = [
    # File utilities
    "get_language_from_extension",
    "should_ignore_file",
    "should_ignore_directory",
    "is_text_file",
    "read_file_content",
    # Patterns and configurations
    "IGNORE_FILE_PATTERNS",
    "IGNORE_DIRECTORY_PATTERNS",
    "SUPPORTED_LANGUAGES",
]

"""
File utility functions for AST Parser

This module provides utility functions for file operations, language detection,
and ignore pattern matching.
"""

import fnmatch
from pathlib import Path
from typing import Optional, Union, Dict, List

from tree_sitter_language_pack import SupportedLanguage
from .ignore_patterns import IGNORE_FILE_PATTERNS, IGNORE_DIRECTORY_PATTERNS
from .langauge_extension_map import LANGUAGE_EXTENSION_MAP


def get_language_from_extension(
    file_path: Union[str, Path],
) -> Optional[SupportedLanguage]:
    """
    Get the language name from file extension or filename.

    Args:
        file_path: Path to the file

    Returns:
        Language name if supported, None otherwise
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    filename = file_path.name

    # Check exact filename matches first
    for language, patterns in LANGUAGE_EXTENSION_MAP.items():
        if filename in patterns:
            return language

    # Check extension matches
    for language, extensions in LANGUAGE_EXTENSION_MAP.items():
        if extension in extensions:
            return language

    return None


def should_ignore_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file should be ignored based on patterns.

    Args:
        file_path: Path to the file

    Returns:
        True if file should be ignored, False otherwise
    """
    file_path = Path(file_path)
    filename = file_path.name

    # Check against ignore patterns
    for pattern in IGNORE_FILE_PATTERNS:
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False


def should_ignore_directory(dir_path: Union[str, Path]) -> bool:
    """
    Check if a directory should be ignored based on patterns.

    Args:
        dir_path: Path to the directory

    Returns:
        True if directory should be ignored, False otherwise
    """
    dir_path = Path(dir_path)
    dirname = dir_path.name

    # Check against ignore patterns
    for pattern in IGNORE_DIRECTORY_PATTERNS:
        if fnmatch.fnmatch(dirname, pattern):
            return True

    return False


def is_text_file(file_path: Union[str, Path], chunk_size: int = 512) -> bool:
    """
    Check if a file is likely a text file by analyzing its content.

    Args:
        file_path: Path to the file
        chunk_size: Number of bytes to read for analysis (default: 512)

    Returns:
        True if file appears to be text, False otherwise
    """
    file_path = Path(file_path)

    if not file_path.exists() or not file_path.is_file():
        return False

    try:
        with open(file_path, "rb") as f:
            chunk = f.read(chunk_size)

        # Empty files are considered text
        if not chunk:
            return True

        # Check for null bytes which strongly indicate binary content
        if b"\x00" in chunk:
            return False

        # Try to decode using common encodings
        encodings = ["utf-8", "latin-1", "cp1252", "ascii"]
        for encoding in encodings:
            try:
                chunk.decode(encoding)
                return True
            except UnicodeDecodeError:
                continue

        return False

    except Exception:
        return False


def read_file_content(file_path: Union[str, Path]) -> Optional[str]:
    """
    Read file content with error handling and encoding detection.

    Args:
        file_path: Path to the file

    Returns:
        File content as string, None if reading failed
    """
    file_path = Path(file_path)

    if not file_path.exists() or not file_path.is_file():
        return None

    # Try different encodings
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception:
            return None

    return None

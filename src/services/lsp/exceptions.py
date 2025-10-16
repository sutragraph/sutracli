"""
LSP error types for better error categorization.

This module provides an enum for categorizing LSP-related errors
without complex exception hierarchies.
"""

from enum import Enum


class LSPErrorType(Enum):
    """Types of LSP errors for categorization."""

    FILE_NOT_FOUND = "file_not_found"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    SERVER_INSTALL_FAILED = "server_install_failed"
    SERVER_START_FAILED = "server_start_failed"

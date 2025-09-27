"""
Database error types for better error categorization.

This module provides an enum for categorizing database errors
without complex exception hierarchies.
"""

from enum import Enum


class DatabaseErrorType(Enum):
    """Types of database errors for categorization."""

    FILE_NOT_FOUND = "file_not_found"
    MISSING_PARAMETER = "missing_parameter"
    RESOURCE_NOT_FOUND = "resource_not_found"
    UNKNOWN_QUERY = "unknown_query"
    DATABASE_CONNECTION = "database_connection"
    INVALID_PARAMETER = "invalid_parameter"
    NO_DATA_AVAILABLE = "no_data_available"

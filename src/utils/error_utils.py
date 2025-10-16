"""
Generic error utilities for creating and raising typed exceptions.

This module provides utilities to create exceptions with associated error types
in a clean, reusable way across the application.
"""

from enum import Enum
from typing import NoReturn, Type, Union


def raiseError(
    error_type: Union[Enum, str],
    message: str,
    exception_class: Type[Exception] = ValueError,
) -> NoReturn:
    """
    Create and raise an exception with an associated error type.

    This utility function reduces repetitive code when creating exceptions
    that need to be categorized with specific error types.

    Args:
        error_type: The error type enum or string to associate with the exception
        message: The error message to display
        exception_class: The exception class to instantiate (defaults to ValueError)

    Raises:
        The specified exception with error_type attribute set

    Examples:
        >>> from tools.tool_database.exceptions import DatabaseErrorType
        >>> raiseError(DatabaseErrorType.FILE_NOT_FOUND, "File not found", FileNotFoundError)

        >>> raiseError(DatabaseErrorType.MISSING_PARAMETER, "Missing param 'id'")

        >>> raiseError("custom_error", "Something went wrong", RuntimeError)
    """
    error = exception_class(message)
    setattr(error, "error_type", error_type)
    raise error

"""JSON Serialization Utilities

This module provides utilities for converting complex Python objects
to JSON-serializable format, handling various edge cases like Enums,
custom objects, bytes, and Path objects.
"""

from enum import Enum
from pathlib import Path
from typing import Any


def make_json_serializable(obj: Any) -> Any:
    """
    Convert complex objects to JSON-serializable format.

    This function recursively processes objects and converts them to types
    that can be serialized to JSON. It handles:
    - Enum objects (returns their value)
    - Custom objects with __dict__ (converts to dict, skipping private attributes)
    - Dictionaries (recursively processes values)
    - Lists and tuples (recursively processes items)
    - Bytes objects (decodes to UTF-8 or returns size info)
    - Path objects (converts to string)
    - Other complex objects (converts to string representation)
    - Basic types (returns as-is)

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, Enum):
        # Handle Enum objects by returning their value
        return obj.value
    elif hasattr(obj, "__dict__"):
        # Handle custom objects with __dict__
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):  # Skip private attributes
                result[key] = make_json_serializable(value)
        return result
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, bytes):
        # Convert bytes to string representation
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return f"<bytes: {len(obj)} bytes>"
    elif isinstance(obj, Path):
        return str(obj)
    elif hasattr(obj, "__str__") and not isinstance(
        obj, (str, int, float, bool, type(None))
    ):
        # Handle other complex objects by converting to string
        return str(obj)
    else:
        # Return as-is for basic types (str, int, float, bool, None)
        return obj

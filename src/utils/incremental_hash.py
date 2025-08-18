"""
Incremental Hash Generator Utility

This module provides functionality for generating incremental numeric IDs based on a base file ID.
Used for creating unique identifiers for code blocks that maintain a relationship with their
parent file while ensuring uniqueness within the file.
"""


class IncrementalHashGenerator:
    """Generator for creating incremental IDs based on a base file ID."""

    def __init__(self, base_id: int):
        """Initialize the hash generator with a base file ID.

        Args:
            base_id: The base file ID to use as starting point
        """
        self.base_value = base_id
        self.current_increment = 0

    def next_id(self) -> int:
        """Generate the next incremental ID.

        Returns:
            An integer ID that is unique within the context of the base file ID
        """
        self.current_increment += 1
        return self.base_value + self.current_increment

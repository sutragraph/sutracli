"""
Custom exceptions for XML parsing failures.
"""


class XMLParsingFailedException(Exception):
    """Exception raised when XML parsing fails and should trigger a retry."""
    
    def __init__(self, message: str, failed_block_index: int = None, original_error: Exception = None):
        self.message = message
        self.failed_block_index = failed_block_index
        self.original_error = original_error
        super().__init__(self.message)
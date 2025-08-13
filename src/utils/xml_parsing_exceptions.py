"""
Custom exceptions for XML parsing failures and user cancellation.
"""

class XMLParsingFailedException(Exception):
    """Exception raised when XML parsing fails and should trigger a retry."""

    def __init__(self, message: str, failed_block_index: int = None, original_error: Exception = None):
        self.message = message
        self.failed_block_index = failed_block_index
        self.original_error = original_error
        super().__init__(self.message)


class UserCancelledException(Exception):
    """Exception raised when user cancels the operation (e.g., via Ctrl+C in debug mode)."""

    def __init__(self, message: str = "User cancelled the operation"):
        self.message = message
        super().__init__(self.message)

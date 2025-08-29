"""Global console instance for consistent Rich output across the application."""

from rich.console import Console

# Global console instance - shared across all modules
console = Console()

# Alternative instances for specific use cases
error_console = Console(stderr=True)

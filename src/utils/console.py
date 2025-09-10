"""Global console singleton with consistent color scheme for Rich output."""

from rich.console import Console
from rich.theme import Theme
from prompt_toolkit import prompt
from typing import Optional


class SutraConsole:
    """Singleton console class with consistent color scheme and styling."""

    _instance: Optional['SutraConsole'] = None
    _console: Optional[Console] = None

    # Color scheme for consistent styling across the application
    COLOR_SCHEME = {
        # Status colors
        'success': 'bold green',
        'error': 'bold red',
        'warning': 'bold yellow',
        'info': 'bold blue',
        'process': 'bold cyan',
        'highlight': 'bold magenta',

        # Text colors
        'primary': 'white',
        'secondary': 'bright_white',
        'dim': 'dim white',
        'accent': 'bright_blue',

        # UI elements
        'panel_border': 'bright_blue',
        'panel_title': 'bold bright_blue',
        'table_header': 'bold cyan',
        'prompt': 'bold cyan',

        # Semantic colors
        'path': 'bright_yellow',
        'command': 'bright_green',
        'value': 'bright_magenta',
        'key': 'cyan',
    }

    def __new__(cls) -> 'SutraConsole':
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the console only once."""
        if self._console is None:
            # Create custom theme from color scheme
            theme = Theme(self.COLOR_SCHEME)
            self._console = Console(theme=theme, force_interactive=True)

    @property
    def console(self) -> Console:
        """Get the rich console instance."""
        return self._console

    def print(self, *args, **kwargs):
        """Print with the global console."""
        return self._console.print(*args, **kwargs)

    def success(self, message: str):
        """Print success message."""
        self._console.print(f"✅ {message}", style="success")

    def error(self, message: str):
        """Print error message."""
        self._console.print(f"❌ {message}", style="error")

    def warning(self, message: str):
        """Print warning message."""
        self._console.print(f"⚠️  {message}", style="warning")

    def info(self, message: str):
        """Print info message."""
        self._console.print(f"ℹ️  {message}", style="info")

    def process(self, message: str):
        """Print process/loading message."""
        self._console.print(f"🔄 {message}", style="process")

    def highlight(self, message: str):
        """Print highlighted message."""
        self._console.print(f"✨ {message}", style="highlight")

    def path(self, message: str):
        """Print path with consistent styling."""
        self._console.print(message, style="path")

    def command(self, message: str):
        """Print command with consistent styling."""
        self._console.print(message, style="command")

    def dim(self, message: str):
        """Print dimmed text."""
        self._console.print(message, style="dim")

    def input(self, prompt_text: str, default: str = None, multiline: bool = True) -> str:
        """Get user input using standard prompt_toolkit multiline behavior."""
        try:
            result = prompt(
                prompt_text,
                multiline=True,
                mouse_support=True,
                default=default or "",
            )
            return result.strip() if result else ""

        except (EOFError, KeyboardInterrupt):
            raise


# Global singleton instance
console = SutraConsole()

# Expose the rich console for advanced usage
rich_console = console.console

"""
Factory class for creating language-specific LSP server instances.
"""

from typing import Dict, Optional, Type

from .base_lsp import BaseLSP
from .javascript_lsp import JavaScriptLSP
from .python_lsp import PythonLSP
from .typescript_lsp import TypeScriptLSP


class LSPFactory:
    """
    Factory class for creating language-specific LSP server instances.

    This factory manages the creation of LSP instances for different languages,
    providing a centralized point for language-specific configuration and setup.
    """

    # Registry of available LSP classes
    _lsp_classes: Dict[str, Type[BaseLSP]] = {
        "typescript": TypeScriptLSP,
        "javascript": JavaScriptLSP,
        "python": PythonLSP,
    }

    @classmethod
    def create_lsp(cls, language: str, workspace_root: Optional[str] = None) -> BaseLSP:
        """
        Create an LSP server instance for the specified language.

        Args:
            language: The language name (e.g., "typescript", "javascript", "python")
            workspace_root: Optional workspace root directory for LSP context

        Returns:
            An instance of the appropriate LSP class for the language

        Raises:
            ValueError: If the language is not supported
        """
        if language not in cls._lsp_classes:
            raise ValueError(
                f"Unsupported language: {language}. Supported languages: {list(cls._lsp_classes.keys())}"
            )

        lsp_class = cls._lsp_classes[language]
        return lsp_class(workspace_root=workspace_root)

    @classmethod
    def get_supported_languages(cls) -> list:
        """
        Get a list of supported languages.

        Returns:
            List of supported language names
        """
        return list(cls._lsp_classes.keys())

    @classmethod
    def register_lsp(cls, language: str, lsp_class: Type[BaseLSP]):
        """
        Register a new LSP class for a language.

        Args:
            language: The language name
            lsp_class: The LSP class to register
        """
        cls._lsp_classes[language] = lsp_class

"""
LSP-based linting system for code quality checking.

Main Components:
- LintChecker: Simple interface for checking lint on source files
- LSPManager: Intelligent server manager (get_server() handles everything)
- Downloader: LSP server installation (ensure_lsp_installed())
- LANGUAGE_MAP: Configuration for supported languages
- LSPErrorType: Typed errors for better error handling

Usage:
    from src.services.lsp import LintChecker

    lint_issues = LintChecker.check_lint("myfile.py")
    # Everything else is automatic!
"""

from .downloader import Downloader
from .exceptions import LSPErrorType
from .jsonrpc_client import JSONRPCClient
from .languages import BaseLSP, JavaScriptLSP, LSPFactory, PythonLSP, TypeScriptLSP
from .lint_checker import LintChecker
from .lsp_manager import LSPManager

__version__ = "1.0.0"
__all__ = [
    "LintChecker",
    "LSPManager",
    "Downloader",
    "JSONRPCClient",
    "LSPErrorType",
    "BaseLSP",
    "TypeScriptLSP",
    "JavaScriptLSP",
    "PythonLSP",
    "LSPFactory",
]

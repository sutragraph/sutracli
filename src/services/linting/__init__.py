"""
Linting service for code validation and formatting.
"""

from .linting_service import LintingService
from .base_linter import BaseLinter, LintResult
from .utils.eslint_check import check_and_install_eslint

__all__ = ['LintingService', 'BaseLinter', 'LintResult', 'check_and_install_eslint']
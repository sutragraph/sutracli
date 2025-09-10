"""
CLI module for SutraKit - AI-powered code analysis and automation tool.

This module provides command-line interface functionality for the SutraKit package.
"""

from .setup import main as setup_main
from .main import main

__all__ = ['setup_main', 'main']

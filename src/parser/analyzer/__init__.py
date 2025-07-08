"""
Tree-sitter Code Analyzer

A powerful, extensible code analysis tool built on tree-sitter that extracts
Abstract Syntax Trees (AST) and analyzes code structure across multiple programming languages.
"""

__version__ = "1.0.0"
__author__ = "Tree-sitter Analyzer Team"

from .analyzer import Analyzer
from .models import ASTNode, ASTEdge, AnalysisResult
from .factory import AnalyzerFactory, get_analyzer_factory
from .config import ConfigManager, get_config_manager

__all__ = [
    "Analyzer",
    "ASTNode",
    "ASTEdge",
    "AnalysisResult",
    "AnalyzerFactory",
    "get_analyzer_factory",
    "ConfigManager",
    "get_config_manager",
]

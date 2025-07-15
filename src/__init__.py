"""
Main package initialization.
"""

import os

# Set tokenizers parallelism before any imports to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from .graph import TreeSitterToSQLiteConverter, SQLiteConnection, GraphOperations
from .models import CodeNode, CodeEdge, ParsedCodebase
from .processors import GraphDataProcessor
from .parser.analyzer import Analyzer

__version__ = "1.0.0"

__all__ = [
    "TreeSitterToSQLiteConverter",
    "CodeNode",
    "CodeEdge",
    "ParsedCodebase",
    "SQLiteConnection",
    "GraphOperations",
    "GraphDataProcessor",
    "Analyzer",
]

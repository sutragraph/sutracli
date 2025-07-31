"""
Main package initialization.
"""

import os

# Set tokenizers parallelism before any imports to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from .graph import ASTToSqliteConverter, SQLiteConnection, GraphOperations
from .models import CodeNode, CodeEdge, ParsedCodebase
from .processors import GraphDataProcessor
# Import indexer for code extraction
from .indexer import export_ast_to_json

__version__ = "1.0.0"

__all__ = [
    "ASTToSqliteConverter",
    "CodeNode",
    "CodeEdge",
    "ParsedCodebase",
    "SQLiteConnection",
    "GraphOperations",
    "GraphDataProcessor",
    "export_ast_to_json",
]

"""
Code indexer for extracting AST data from source files.
Replaces the old tree-sitter parser with a more focused extraction system.
"""

from .export_ast_to_json import main as export_ast_to_json

__all__ = ["export_ast_to_json"]

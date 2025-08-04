"""
Main package initialization.
"""

import os

# Set tokenizers parallelism before any imports to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

__version__ = "1.0.0"

# Note: Imports removed to avoid circular dependencies
# Import modules directly when needed:
# from graph import ASTToSqliteConverter, SQLiteConnection, GraphOperations
# from models import Project, File, FileData, BlockType, CodeBlock, Relationship, ExtractionData
# from indexer import export_ast_to_json

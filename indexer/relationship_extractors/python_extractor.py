"""Python Relationship Extractor

Extracts relationships between Python files based on import statements
using Tree-sitter for more accurate parsing.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from tree_sitter_language_pack import get_parser, get_language

from extractors import BlockType
from . import BaseRelationshipExtractor, Relationship


class PythonRelationshipExtractor(BaseRelationshipExtractor):
    """Extractor for relationships between Python files."""

    @property
    def language(self) -> str:
        """Return the language this extractor handles."""
        return "python"

    def extract_relationships(self, extraction_results: Dict[str, Dict[str, Any]]) -> List[Relationship]:
        """Extract relationships between Python files based on import statements."""
        relationships = []

        # Process each file's extraction results
        for source_file_path, result in extraction_results.items():
            # Get the source file ID
            source_file_id = result.get("id")
            if not source_file_id:
                continue

            # Get all import blocks from this file
            blocks = result.get("blocks", [])
            import_blocks = [block for block in blocks if hasattr(block, 'type') and block.type == BlockType.IMPORT]

            # Process each import block
            for import_block in import_blocks:
                # Resolve the import to a target file path
                content = import_block.content if hasattr(import_block, 'content') else ""
                
                # Resolve the import to a target file path
                target_file_path = self._resolve_import_path(source_file_path, content)
                if not target_file_path or target_file_path not in extraction_results:
                    continue

                # Get the target file ID
                target_file_id = extraction_results[target_file_path].get("id")
                if not target_file_id:
                    continue

                # Create a relationship
                symbols = import_block.symbols if hasattr(import_block, 'symbols') else []
                relationship = Relationship(
                    source_file=source_file_id,
                    target_file=target_file_id,
                    import_content=content,
                    symbols=symbols
                )
                relationships.append(relationship)

        return relationships

    def _resolve_import_path(self, source_file_path: str, import_content: str) -> Optional[str]:
        """Resolve a Python import statement to an actual file path."""
        source_file_path = Path(source_file_path)
        source_dir = source_file_path.parent

        # Extract the module path from the import statement
        module_path = self._extract_module_path(import_content)
        if not module_path:
            return None

        # Handle relative imports
        if module_path.startswith("."):
            return self._resolve_relative_import(source_dir, module_path)

        # Handle absolute imports
        return self._resolve_absolute_import(source_dir, module_path)

    def _extract_module_path(self, import_content: str) -> Optional[str]:
        """Extract the module path from a Python import statement using Tree-sitter."""
        try:
            # Get the Python parser from tree-sitter-language-pack
            parser = get_parser("python")
            if not parser:
                return self._fallback_extract_module_path(import_content)
            
            # Parse the import statement
            tree = parser.parse(bytes(import_content, "utf-8"))
            root_node = tree.root_node

            # Get the language for queries
            language = get_language("python")
            if not language:
                return self._fallback_extract_module_path(import_content)

            # Query for import statements - fixed syntax
            query_string = """
            (import_statement
              name: (dotted_name) @module_name)
            
            (import_from_statement
              module_name: (dotted_name) @module_name)
            
            (import_from_statement
              module_name: (relative_import) @module_name)
            """

            # Create query and execute it using the parser
            query = language.query(query_string)
            # Create a query cursor and execute the query
            from tree_sitter import QueryCursor
            query_cursor = QueryCursor(query)
            # Get captures from the query cursor
            captures = query_cursor.captures(tree.root_node)
            
            # Process captures - tree-sitter 0.25 format
            # In version 0.25.0, captures() returns a dict where keys are capture names and values are lists of nodes
            if "module_name" in captures and captures["module_name"]:
                # Get the first node that matched the module_name pattern
                node = captures["module_name"][0]
                return node.text.decode("utf-8")

        except Exception as e:
            print(f"Error parsing import statement with Tree-sitter: {e}")
            # Fallback to simple regex parsing
            return self._fallback_extract_module_path(import_content)

        return None

    def _fallback_extract_module_path(self, import_content: str) -> Optional[str]:
        """Fallback method to extract module path using simple string parsing."""
        import re
        
        # Handle "from module import ..." statements
        from_match = re.match(r'from\s+([\w\.]+)\s+import', import_content.strip())
        if from_match:
            return from_match.group(1)
        
        # Handle "import module" statements
        import_match = re.match(r'import\s+([\w\.]+)', import_content.strip())
        if import_match:
            return import_match.group(1)
        
        return None

    def _resolve_relative_import(self, source_dir: Path, module_path: str) -> Optional[str]:
        """Resolve a relative import to an actual file path."""
        # Count the number of dots for relative imports
        dot_count = 0
        for char in module_path:
            if char == '.':
                dot_count += 1
            else:
                break

        # Remove the dots from the module path
        module_path = module_path[dot_count:]

        # Go up the directory tree based on the number of dots
        target_dir = source_dir
        for _ in range(dot_count - 1):
            target_dir = target_dir.parent

        # Convert module path to directory path
        if module_path:
            module_parts = module_path.split('.')
            target_path = target_dir.joinpath(*module_parts)
        else:
            target_path = target_dir

        # Check if the target is a Python file
        py_file = target_path.with_suffix('.py')
        if py_file.exists():
            return str(py_file)

        # Check if the target is a directory with __init__.py
        init_file = target_path / '__init__.py'
        if init_file.exists():
            return str(init_file)

        return None

    def _resolve_absolute_import(self, source_dir: Path, module_path: str) -> Optional[str]:
        """Resolve an absolute import to an actual file path."""
        # Find the project root (the directory containing the top-level package)
        project_root = self._find_project_root(source_dir)
        if not project_root:
            return None

        # Convert module path to directory path
        module_parts = module_path.split('.')
        target_path = project_root.joinpath(*module_parts)

        # Check if the target is a Python file
        py_file = target_path.with_suffix('.py')
        if py_file.exists():
            return str(py_file)

        # Check if the target is a directory with __init__.py
        init_file = target_path / '__init__.py'
        if init_file.exists():
            return str(init_file)

        return None

    def _find_project_root(self, start_dir: Path) -> Optional[Path]:
        """Find the project root directory by looking for common project markers."""
        current_dir = start_dir
        while current_dir.parent != current_dir:  # Stop at filesystem root
            # Check for common project markers
            for marker in ['setup.py', 'pyproject.toml', '.git', '.hg']:
                if (current_dir / marker).exists():
                    return current_dir

            # Move up one directory
            current_dir = current_dir.parent

        # If no project root found, return the start directory
        return start_dir
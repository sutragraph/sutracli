"""TypeScript Relationship Extractor

Extracts relationships between TypeScript/JavaScript files based on import statements
using Tree-sitter for more accurate parsing.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from tree_sitter_language_pack import get_parser, get_language

from extractors import BlockType
from . import BaseRelationshipExtractor, Relationship


class TypeScriptRelationshipExtractor(BaseRelationshipExtractor):
    """Extractor for relationships between TypeScript/JavaScript files."""

    @property
    def language(self) -> str:
        """Return the language this extractor handles."""
        return "typescript"

    def extract_relationships(self, extraction_results: Dict[str, Dict[str, Any]]) -> List[Relationship]:
        """Extract relationships between TypeScript files based on import statements."""
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
        """Resolve a TypeScript import statement to an actual file path."""
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
        """Extract the module path from a TypeScript import statement using Tree-sitter."""
        try:
            # Try to get the TypeScript parser
            parser = get_parser("typescript")
            if not parser:
                # Fallback to JavaScript parser if TypeScript is not available
                parser = get_parser("javascript")
                if not parser:
                    return self._fallback_extract_module_path(import_content)
            
            # Parse the import statement
            tree = parser.parse(bytes(import_content, "utf-8"))
            root_node = tree.root_node

            # Get the language for queries (try TypeScript first, then JavaScript)
            language = get_language("typescript")
            if not language:
                language = get_language("javascript")
                if not language:
                    return self._fallback_extract_module_path(import_content)

            # Query for different types of imports - fixed syntax
            query_string = """
            (import_statement
              source: (string) @module_path)
            
            (call_expression
              function: (identifier) @func_name
              arguments: (arguments
                (string) @module_path))
            
            (call_expression
              function: (import) @import_func
              arguments: (arguments
                (string) @module_path))
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
            if "module_path" in captures and captures["module_path"]:
                # Get the first node that matched the module_path pattern
                node = captures["module_path"][0]
                # Remove quotes from the string
                module_path = node.text.decode("utf-8")
                clean_path = module_path.strip('"\'')
                return clean_path

        except Exception as e:
            print(f"Error parsing import statement with Tree-sitter: {e}")
            # Fallback to simple regex parsing
            return self._fallback_extract_module_path(import_content)

        return None

    def _fallback_extract_module_path(self, import_content: str) -> Optional[str]:
        """Fallback method to extract module path using simple string parsing."""
        import re
        
        # Handle ES6 imports: import ... from 'module'
        es6_match = re.search(r'from\s+[\'"]([^\'"]+)[\'"]', import_content)
        if es6_match:
            return es6_match.group(1)
        
        # Handle require statements: require('module')
        require_match = re.search(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', import_content)
        if require_match:
            return require_match.group(1)
        
        # Handle dynamic imports: import('module')
        dynamic_match = re.search(r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', import_content)
        if dynamic_match:
            return dynamic_match.group(1)
        
        # Handle simple import statements: import 'module'
        simple_match = re.search(r'import\s+[\'"]([^\'"]+)[\'"]', import_content)
        if simple_match:
            return simple_match.group(1)
        
        return None

    def _resolve_relative_import(self, source_dir: Path, module_path: str) -> Optional[str]:
        """Resolve a relative import to an actual file path."""
        # Handle relative paths starting with ./ or ../
        if module_path.startswith("."):
            # Determine the target directory based on the number of ../ segments
            target_dir = source_dir
            path_parts = module_path.split('/')
            
            # Process directory navigation parts
            i = 0
            while i < len(path_parts) and (path_parts[i] == '.' or path_parts[i] == '..'):
                if path_parts[i] == '..':
                    target_dir = target_dir.parent
                # '.' means current directory, so no change needed
                i += 1
            
            # Remaining parts form the file path
            remaining_path = '/'.join(path_parts[i:])
            target_path = target_dir / remaining_path
            
            # Check for various file extensions
            for ext in ['', '.ts', '.tsx', '.js', '.jsx', '.d.ts', '/index.ts', '/index.tsx', '/index.js', '/index.jsx']:
                file_path = Path(f"{target_path}{ext}")
                if file_path.exists():
                    return str(file_path)
        
        return None

    def _resolve_absolute_import(self, source_dir: Path, module_path: str) -> Optional[str]:
        """Resolve an absolute import to an actual file path."""
        # Handle node_modules imports (simplified approach)
        if not module_path.startswith(".") and not module_path.startswith("/"):
            # Find the project root (the directory containing node_modules)
            project_root = self._find_project_root(source_dir)
            if project_root:
                # Check in node_modules directory
                node_modules_path = project_root / 'node_modules' / module_path
                
                # Check for package.json to find the main entry point
                package_json = node_modules_path / 'package.json'
                if package_json.exists():
                    # In a real implementation, we would parse package.json to find the main entry point
                    # For simplicity, we'll just check common entry points
                    for entry_point in ['index.js', 'index.ts', 'dist/index.js', 'lib/index.js']:
                        entry_file = node_modules_path / entry_point
                        if entry_file.exists():
                            return str(entry_file)
                
                # Check for direct file references
                for ext in ['', '.ts', '.tsx', '.js', '.jsx', '.d.ts']:
                    file_path = Path(f"{node_modules_path}{ext}")
                    if file_path.exists():
                        return str(file_path)
        
        # Handle project root imports (e.g., imports from tsconfig.json paths)
        project_root = self._find_project_root(source_dir)
        if project_root:
            # Check for tsconfig.json to find path mappings
            tsconfig_path = project_root / 'tsconfig.json'
            if tsconfig_path.exists():
                # In a real implementation, we would parse tsconfig.json to find path mappings
                # For simplicity, we'll just check common patterns
                
                # Try direct resolution from project root
                target_path = project_root / module_path
                for ext in ['', '.ts', '.tsx', '.js', '.jsx', '.d.ts', '/index.ts', '/index.tsx', '/index.js', '/index.jsx']:
                    file_path = Path(f"{target_path}{ext}")
                    if file_path.exists():
                        return str(file_path)
                
                # Try src directory
                src_path = project_root / 'src' / module_path
                for ext in ['', '.ts', '.tsx', '.js', '.jsx', '.d.ts', '/index.ts', '/index.tsx', '/index.js', '/index.jsx']:
                    file_path = Path(f"{src_path}{ext}")
                    if file_path.exists():
                        return str(file_path)
        
        return None

    def _find_project_root(self, start_dir: Path) -> Optional[Path]:
        """Find the project root directory by looking for common project markers."""
        current_dir = start_dir
        while current_dir.parent != current_dir:  # Stop at filesystem root
            # Check for common project markers
            for marker in ['package.json', 'tsconfig.json', '.git', 'node_modules']:
                if (current_dir / marker).exists():
                    return current_dir

            # Move up one directory
            current_dir = current_dir.parent

        # If no project root found, return the start directory
        return start_dir
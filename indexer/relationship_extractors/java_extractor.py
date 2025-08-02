"""Java Relationship Extractor

Extracts relationships between Java files based on import statements
using Tree-sitter for accurate parsing. Works purely with extraction results data
without file system lookups.
"""


from pathlib import Path
from typing import Any, Dict, List, Optional
from tree_sitter_language_pack import get_parser

from extractors import BlockType
from . import BaseRelationshipExtractor, Relationship


class JavaRelationshipExtractor(BaseRelationshipExtractor):
    """Extractor for relationships between Java files using only extraction results data."""



    def extract_relationships(self, extraction_results: Dict[str, Dict[str, Any]]) -> List[Relationship]:
        """Extract relationships between Java files based on import statements."""
        relationships = []

        # Build a registry of available modules from extraction results
        module_registry = self._build_module_registry(extraction_results)

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
                content = import_block.content if hasattr(import_block, 'content') else ""

                # Parse the import statement to extract detailed information
                import_info = self._parse_import_statement(content)
                if not import_info:
                    continue

                # Resolve the import to a target file using our module registry
                target_file_id = self._resolve_import_from_registry(
                    source_file_path, import_info, module_registry
                )

                if target_file_id:
                    # Create a relationship
                    relationship = Relationship(
                        source_file=source_file_id,
                        target_file=target_file_id,
                        import_content=content,
                        symbols=import_info.get('symbols', [])
                    )
                    relationships.append(relationship)

        return relationships

    def _build_module_registry(self, extraction_results: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Build a registry mapping Java package names to file IDs from extraction results."""
        registry = {}

        for file_path, result in extraction_results.items():
            file_id = result.get("id")
            if not file_id:
                continue

            # Convert file path to potential Java package names
            path_obj = Path(file_path)

            # Get the package names relative to different possible roots
            package_names = self._get_potential_module_names(path_obj)

            for package_name in package_names:
                registry[package_name] = file_id

        return registry

    def _get_potential_module_names(self, file_path: Path) -> List[str]:
        """Get potential Java package names for a file path."""
        package_names = []

        # Convert path separators to dots and remove .java extension
        path_parts = file_path.parts

        # Remove .java extension if present
        if file_path.suffix == '.java':
            name = file_path.stem
            # For Java files, replace the last part with the class name
            path_parts = path_parts[:-1] + (name,)

        # Generate package names by considering different root levels
        for i in range(len(path_parts)):
            # Try different starting points in the path
            package_parts = path_parts[i:]
            if package_parts:
                package_name = '.'.join(package_parts)
                package_names.append(package_name)

        return package_names

    def _parse_import_statement(self, import_content: str) -> Optional[Dict[str, Any]]:
        """Parse a Java import statement using manual AST traversal to extract detailed information."""
        try:
            # Get the Java parser
            parser = get_parser("java")
            tree = parser.parse(bytes(import_content.strip(), "utf-8"))

            # Extract information using manual traversal
            package_name = None
            symbols = []
            is_static = False
            is_wildcard = False

            # Find the import declaration node
            import_node = None
            for child in tree.root_node.children:
                if child.type == 'import_declaration':
                    import_node = child
                    break

            if not import_node:
                return None

            # Parse the import declaration
            for child in import_node.children:
                if child.type == 'static':
                    # This is a static import
                    is_static = True
                elif child.type == 'scoped_identifier':
                    # This is the package.Class or package.Class.method
                    package_name = self._safe_text_extract(child)
                elif child.type == 'identifier':
                    # This could be a simple class name
                    if package_name is None:
                        package_name = self._safe_text_extract(child)
                elif child.type == 'asterisk':
                    # This is a wildcard import (import package.*)
                    is_wildcard = True
                    symbols = ['*']

            # For non-wildcard imports, extract the imported symbol
            if package_name and not is_wildcard:
                # Extract the last part as the symbol (class name or method name)
                parts = package_name.split('.')
                if len(parts) > 1:
                    if is_static:
                        # For static imports, the last part is the method/field name
                        symbols = [parts[-1]]
                        # The package name should be everything except the last part
                        package_name = '.'.join(parts[:-1])
                    else:
                        # For regular imports, the last part is the class name
                        symbols = [parts[-1]]
                        # Keep the full package name including the class
                        # package_name remains as is

            if package_name:
                return {
                    'module_name': package_name,
                    'symbols': symbols,
                    'aliases': {},  # Java doesn't support import aliases
                    'is_relative': False,  # Java doesn't have relative imports
                    'is_static': is_static,
                    'is_wildcard': is_wildcard,
                    'raw_content': import_content.strip()
                }

        except Exception as e:
            print(f"Error parsing Java import statement '{import_content}': {e}")

        return None

    def _resolve_import_from_registry(
        self,
        source_file_path: str,
        import_info: Dict[str, Any],
        module_registry: Dict[str, str]
    ) -> Optional[str]:
        """Resolve a Java import to a file ID using the module registry."""
        package_name = import_info['module_name']
        
        # Java only has absolute imports
        return self._resolve_absolute_import(package_name, module_registry)


    def _resolve_absolute_import(
        self,
        package_name: str,
        module_registry: Dict[str, str]
    ) -> Optional[str]:
        """Resolve a Java absolute import using the module registry."""
        # Try direct lookup first
        if package_name in module_registry:
            return module_registry[package_name]

        # Try looking for partial matches (in case of different root paths)
        for registered_name, file_id in module_registry.items():
            if registered_name.endswith(package_name):
                return file_id
            if package_name.endswith(registered_name):
                return file_id

        return None

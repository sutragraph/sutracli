"""Python Relationship Extractor

Extracts relationships between Python files based on import statements
using Tree-sitter for accurate parsing. Works purely with extraction results data
without file system lookups.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from tree_sitter_language_pack import get_parser

from indexer.extractors import BlockType
from indexer.relationship_extractors import BaseRelationshipExtractor, Relationship


class PythonRelationshipExtractor(BaseRelationshipExtractor):
    """Extractor for relationships between Python files using only extraction results data."""

    def extract_relationships(
        self, extraction_results: Dict[str, Dict[str, Any]]
    ) -> List[Relationship]:
        """Extract relationships between Python files based on import statements."""
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
            import_blocks = [
                block
                for block in blocks
                if hasattr(block, "type") and block.type == BlockType.IMPORT
            ]

            # Process each import block
            for import_block in import_blocks:
                content = (
                    import_block.content if hasattr(import_block, "content") else ""
                )

                # Parse the import statement to extract detailed information
                import_info = self._parse_import_statement(content)
                if not import_info:
                    continue

                # Handle special case: when importing symbols from a relative package,
                # check if any of the symbols correspond to module files
                resolved_as_module = False
                if import_info.get("is_relative") and import_info.get("symbols"):
                    for symbol in import_info["symbols"]:
                        # Try to resolve the symbol as a module in the target package
                        symbol_import_info = {
                            "module_name": import_info["module_name"] + "." + symbol,
                            "symbols": [],
                            "is_relative": True,
                        }
                        target_file_id = self._resolve_import_from_registry(
                            source_file_path, symbol_import_info, module_registry
                        )

                        if target_file_id:
                            # Create a relationship for the module file
                            relationship = Relationship(
                                source_id=source_file_id,
                                target_id=target_file_id,
                                import_content=content,
                                symbols=[symbol],
                            )
                            relationships.append(relationship)
                            resolved_as_module = True

                # Only try standard resolution if we didn't resolve symbols as modules
                if not resolved_as_module:
                    target_file_id = self._resolve_import_from_registry(
                        source_file_path, import_info, module_registry
                    )

                    if target_file_id:
                        # Create a relationship
                        relationship = Relationship(
                            source_id=source_file_id,
                            target_id=target_file_id,
                            import_content=content,
                            symbols=import_info.get("symbols", []),
                        )
                        relationships.append(relationship)

        return relationships

    def _build_module_registry(
        self, extraction_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Build a registry mapping module paths to file IDs from extraction results."""
        registry = {}

        for file_path, result in extraction_results.items():
            file_id = result.get("id")
            if not file_id:
                continue

            # Convert file path to potential module names
            path_obj = Path(file_path)

            # Get the module path relative to different possible roots
            module_names = self._get_potential_module_names(path_obj)

            for module_name in module_names:
                registry[module_name] = file_id

        return registry

    def _get_potential_module_names(self, file_path: Path) -> List[str]:
        """Get potential module names for a file path."""
        module_names = []

        # Convert path separators to dots and remove .py extension
        path_parts = file_path.parts

        # Remove .py extension if present
        if file_path.suffix == ".py":
            name = file_path.stem
            if name == "__init__":
                # For __init__.py files, use the parent directory name
                path_parts = path_parts[:-1]
            else:
                # For regular .py files, replace the last part with the stem
                path_parts = path_parts[:-1] + (name,)

        # Generate module names by considering different root levels
        for i in range(len(path_parts)):
            # Try different starting points in the path
            module_parts = path_parts[i:]
            if module_parts:
                module_name = ".".join(module_parts)
                module_names.append(module_name)

        return module_names

    def _parse_import_statement(self, import_content: str) -> Optional[Dict[str, Any]]:
        """Parse a Python import statement using manual AST traversal to extract detailed information."""
        try:
            # Get the Python parser
            parser = get_parser("python")
            tree = parser.parse(bytes(import_content.strip(), "utf-8"))

            # Extract information using manual traversal
            module_name = None
            symbols = []
            aliases = {}
            is_relative = False

            # Find the import statement node
            import_node = None
            import_type = "import"
            for child in tree.root_node.children:
                if child.type in ["import_statement", "import_from_statement"]:
                    import_node = child
                    import_type = "import"
                    break
                elif child.type == "expression_statement":
                    # Check for dynamic imports in expression statements
                    for grandchild in child.children:
                        if grandchild.type == "call":
                            if self._is_dynamic_import_call(grandchild):
                                import_node = grandchild
                                import_type = "dynamic_import"
                                break
                    if import_node:
                        break
                elif child.type == "call":
                    # Direct call expression (might happen in some parsing contexts)
                    if self._is_dynamic_import_call(child):
                        import_node = child
                        import_type = "dynamic_import"
                        break

            if not import_node:
                return None

            if import_type == "dynamic_import":
                # Handle dynamic imports: importlib.import_module() or __import__()
                module_name = self._extract_dynamic_import_module_name(import_node)
                if module_name:
                    if module_name.startswith("."):
                        is_relative = True
                    # Dynamic imports typically import the whole module
                    symbols = ["*"]  # Indicate dynamic import

            elif import_node.type == "import_statement":
                # Handle: import module [as alias]
                for child in import_node.children:
                    if child.type == "dotted_name":
                        module_name = self._safe_text_extract(child)
                    elif child.type == "aliased_import":
                        # Handle aliased imports like "import module as alias"
                        for subchild in child.children:
                            if subchild.type == "dotted_name":
                                module_name = self._safe_text_extract(subchild)
                            elif subchild.type == "identifier":
                                # This is the alias
                                if module_name:
                                    aliases[module_name] = self._safe_text_extract(
                                        subchild
                                    )

            elif import_node.type == "import_from_statement":
                # Handle: from module import symbol [as alias]
                imported_symbols = []
                current_symbol = None

                for child in import_node.children:
                    if child.type == "dotted_name":
                        if module_name is None:
                            # This is the module name
                            module_name = self._safe_text_extract(child)
                        else:
                            # This is an imported symbol
                            current_symbol = self._safe_text_extract(child)
                            imported_symbols.append(current_symbol)
                    elif child.type == "relative_import":
                        module_name = self._safe_text_extract(child)
                        is_relative = True
                    elif child.type == "aliased_import":
                        # Handle aliased imports in from statements
                        for subchild in child.children:
                            if subchild.type == "dotted_name":
                                current_symbol = self._safe_text_extract(subchild)
                                imported_symbols.append(current_symbol)
                            elif subchild.type == "identifier":
                                # This is the alias for the current symbol
                                if current_symbol:
                                    aliases[current_symbol] = self._safe_text_extract(
                                        subchild
                                    )

                symbols = imported_symbols

            if module_name:
                return {
                    "module_name": module_name,
                    "symbols": symbols,
                    "aliases": aliases,
                    "is_relative": is_relative,
                    "raw_content": import_content.strip(),
                }

        except Exception as e:
            print(f"Error parsing import statement '{import_content}': {e}")

        return None

    def _resolve_import_from_registry(
        self,
        source_file_path: str,
        import_info: Dict[str, Any],
        module_registry: Dict[str, str],
    ) -> Optional[str]:
        """Resolve an import to a file ID using the module registry."""
        module_name = import_info["module_name"]
        is_relative = import_info["is_relative"]

        if is_relative:
            return self._resolve_relative_import(
                source_file_path, module_name, module_registry
            )
        else:
            return self._resolve_absolute_import(module_name, module_registry)

    def _resolve_relative_import(
        self, source_file_path: str, module_name: str, module_registry: Dict[str, str]
    ) -> Optional[str]:
        """Resolve a relative import using the module registry."""
        source_path = Path(source_file_path)
        source_dir = source_path.parent

        # Count dots to determine how many levels to go up
        dot_count = 0
        for char in module_name:
            if char == ".":
                dot_count += 1
            else:
                break

        # Remove leading dots
        relative_module = module_name[dot_count:]

        # Calculate target directory by going up the required levels
        target_dir = source_dir
        for _ in range(dot_count - 1):
            target_dir = target_dir.parent

        # If there's a module name after the dots, append it to the path
        if relative_module:
            target_path = target_dir / relative_module.replace(".", "/")
        else:
            target_path = target_dir

        # Try to find matching module names in registry
        possible_names = []

        # Try as a Python file first (prioritize .py files over __init__.py)
        py_file_path = str(target_path.with_suffix(".py"))
        possible_names.extend(self._get_potential_module_names(Path(py_file_path)))

        # Try as a package (__init__.py)
        init_file_path = str(target_path / "__init__.py")
        possible_names.extend(self._get_potential_module_names(Path(init_file_path)))

        # Look for matches in registry
        for name in possible_names:
            if name in module_registry:
                return module_registry[name]

        return None

    def _is_dynamic_import_call(self, node) -> bool:
        """Check if a call node is a dynamic import (importlib.import_module or __import__)."""
        if not hasattr(node, "children") or not node.children:
            return False

        # Get the function being called
        function_node = node.children[0]

        # Check for __import__() calls
        if (
            hasattr(function_node, "type")
            and function_node.type == "identifier"
            and self._safe_text_extract(function_node) == "__import__"
        ):
            return True

        # Check for importlib.import_module() calls
        if hasattr(function_node, "type") and function_node.type == "attribute":
            # Get the full attribute path
            attr_text = self._safe_text_extract(function_node)
            if "importlib.import_module" in attr_text or "import_module" in attr_text:
                return True

        return False

    def _extract_dynamic_import_module_name(self, node) -> Optional[str]:
        """Extract module name from a dynamic import call."""
        if not hasattr(node, "children"):
            return None

        # Look for argument_list containing the module path
        for child in node.children:
            if hasattr(child, "type") and child.type == "argument_list":
                for arg_child in child.children:
                    if hasattr(arg_child, "type") and arg_child.type == "string":
                        # Extract the string content and remove quotes
                        text = self._safe_text_extract(arg_child)
                        return text.strip("'\"")

        return None

    def _resolve_absolute_import(
        self, module_name: str, module_registry: Dict[str, str]
    ) -> Optional[str]:
        """Resolve an absolute import using the module registry."""
        # Try direct lookup first
        if module_name in module_registry:
            return module_registry[module_name]

        # Try looking for partial matches (in case of different root paths)
        for registered_name, file_id in module_registry.items():
            if registered_name.endswith(module_name):
                return file_id
            if module_name.endswith(registered_name):
                return file_id

        return None

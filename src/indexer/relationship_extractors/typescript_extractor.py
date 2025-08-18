"""TypeScript Relationship Extractor

Extracts relationships between TypeScript/JavaScript files based on import statements
using Tree-sitter for accurate parsing. Works purely with extraction results data
without file system lookups.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from tree_sitter_language_pack import get_parser, get_language

from indexer.extractors import BlockType
from indexer.relationship_extractors import BaseRelationshipExtractor, Relationship


class TypeScriptRelationshipExtractor(BaseRelationshipExtractor):
    """Extractor for relationships between TypeScript/JavaScript files using only extraction results data."""

    def extract_relationships(
        self, extraction_results: Dict[str, Dict[str, Any]]
    ) -> List[Relationship]:
        """Extract relationships between TypeScript files based on import statements."""
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

                # Resolve the import to a target file using our module registry
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
        """Get potential module names for a TypeScript/JavaScript file path."""
        module_names = []

        # Remove common extensions
        extensions = [".ts", ".tsx", ".js", ".jsx", ".d.ts"]
        path_without_ext = file_path

        for ext in extensions:
            if file_path.suffix == ext or str(file_path).endswith(ext):
                if ext == ".d.ts":
                    path_without_ext = Path(str(file_path)[:-5])  # Remove .d.ts
                else:
                    path_without_ext = file_path.with_suffix("")
                break

        path_parts = path_without_ext.parts

        # Handle index files - they can be referenced by their directory name
        if path_without_ext.name == "index":
            path_parts = path_parts[:-1]  # Remove 'index' from the path

        # Generate module names by considering different root levels
        for i in range(len(path_parts)):
            # Try different starting points in the path
            module_parts = path_parts[i:]
            if module_parts:
                # Create relative paths with ./ prefix for same directory
                module_path = "/".join(module_parts)
                module_names.append(module_path)
                module_names.append("./" + module_path)

                # Also add without ./ for absolute-style imports
                if len(module_parts) > 1:
                    # For nested paths, also try parent directory references
                    for j in range(1, len(module_parts)):
                        parent_path = "../" * j + "/".join(module_parts[j:])
                        module_names.append(parent_path)

        return module_names

    def _parse_import_statement(self, import_content: str) -> Optional[Dict[str, Any]]:
        """Parse a TypeScript import statement using manual AST traversal to extract detailed information."""
        try:
            # Get the TypeScript parser
            parser = get_parser("typescript")
            tree = parser.parse(bytes(import_content.strip(), "utf-8"))

            # Extract information using manual traversal
            module_name = None
            symbols = []
            aliases = {}
            is_relative = False
            import_type = "import"

            # Find the import-related node
            import_node = None
            for child in tree.root_node.children:
                if child.type == "import_statement":
                    import_node = child
                    import_type = "import"
                    break
                elif child.type == "lexical_declaration":
                    # Check if this is a CommonJS require
                    if "require" in self._safe_text_extract(child):
                        import_node = child
                        import_type = "require"
                        break
                elif child.type == "expression_statement":
                    # Check for bare dynamic imports or require calls
                    for grandchild in child.children:
                        if grandchild.type == "call_expression":
                            # Check for dynamic import: import('./module')
                            if self._is_dynamic_import_call_node(grandchild):
                                import_node = grandchild
                                import_type = "dynamic_import"
                                break
                            # Check for bare require: require('./module')
                            elif self._is_require_call_node(grandchild):
                                import_node = grandchild
                                import_type = "bare_require"
                                break
                    if import_node:
                        break
                elif child.type == "call_expression":
                    # Direct call expression (might happen in some parsing contexts)
                    if self._is_dynamic_import_call_node(child):
                        import_node = child
                        import_type = "dynamic_import"
                        break
                    elif self._is_require_call_node(child):
                        import_node = child
                        import_type = "bare_require"
                        break

            if not import_node:
                return None

            if import_type == "import":
                # Handle ES6 import statements
                for child in import_node.children:
                    if child.type == "string":
                        # Extract module path from string
                        module_name = self._extract_string_value(child)
                        if module_name and module_name.startswith("."):
                            is_relative = True
                    elif child.type == "import_clause":
                        # Extract imported symbols
                        symbols.extend(
                            self._extract_import_clause_symbols(child, aliases)
                        )

            elif import_type == "require":
                # Handle CommonJS require statements
                module_name, require_symbols = self._extract_require_info(import_node)
                if module_name:
                    if module_name.startswith("."):
                        is_relative = True
                    symbols.extend(require_symbols)

            elif import_type == "dynamic_import":
                # Handle dynamic import: import('./module')
                module_name = self._extract_call_string_argument(import_node)
                if module_name and module_name.startswith("."):
                    is_relative = True
                # Dynamic imports don't have specific symbols at parse time
                symbols = ["*"]  # Indicate dynamic import

            elif import_type == "bare_require":
                # Handle bare require: require('./module')
                module_name = self._extract_call_string_argument(import_node)
                if module_name and module_name.startswith("."):
                    is_relative = True
                # Bare require imports everything
                symbols = ["*"]  # Indicate full module import

            if module_name:
                return {
                    "module_name": module_name,
                    "symbols": symbols,
                    "aliases": aliases,
                    "is_relative": is_relative,
                    "import_type": import_type,
                    "raw_content": import_content.strip(),
                }

        except Exception as e:
            print(f"Error parsing import statement '{import_content}': {e}")

        return None

    def _extract_string_value(self, string_node) -> Optional[str]:
        """Extract the actual string value from a string node."""
        try:
            # Look for string_fragment child
            for child in string_node.children:
                if child.type == "string_fragment":
                    return self._safe_text_extract(child)

            # Fallback: extract from the full text and remove quotes
            full_text = self._safe_text_extract(string_node)
            return full_text.strip("'\"")
        except:
            return None

    def _extract_import_clause_symbols(
        self, import_clause_node, aliases: Dict[str, str]
    ) -> List[str]:
        """Extract symbols from an import clause."""
        symbols = []

        for child in import_clause_node.children:
            if child.type == "identifier":
                # Default import
                symbol_name = self._safe_text_extract(child)
                symbols.append(symbol_name)
            elif child.type == "named_imports":
                # Named imports like { function1, function2 }
                for grandchild in child.children:
                    if grandchild.type == "import_specifier":
                        # Extract import specifier details
                        imported_name = None
                        local_name = None

                        for ggchild in grandchild.children:
                            if ggchild.type == "identifier":
                                if imported_name is None:
                                    imported_name = self._safe_text_extract(ggchild)
                                else:
                                    local_name = self._safe_text_extract(ggchild)

                        if imported_name:
                            symbols.append(imported_name)
                            if local_name and local_name != imported_name:
                                aliases[imported_name] = local_name
            elif child.type == "namespace_import":
                # Namespace import like * as module2
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        namespace_name = self._safe_text_extract(grandchild)
                        symbols.append("*")  # Indicate namespace import
                        aliases["*"] = namespace_name
                        break

        return symbols

    def _extract_require_info(
        self, lexical_declaration_node
    ) -> tuple[Optional[str], List[str]]:
        """Extract module name and symbols from a CommonJS require statement."""
        module_name = None
        symbols = []

        # Find the variable declarator
        for child in lexical_declaration_node.children:
            if child.type == "variable_declarator":
                variable_name = None

                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        variable_name = self._safe_text_extract(grandchild)
                        symbols.append(variable_name)
                    elif grandchild.type == "call_expression":
                        # Find the require call
                        for ggchild in grandchild.children:
                            if (
                                ggchild.type == "identifier"
                                and self._safe_text_extract(ggchild) == "require"
                            ):
                                # Found require, now find the arguments
                                for gggchild in grandchild.children:
                                    if gggchild.type == "arguments":
                                        for ggggchild in gggchild.children:
                                            if ggggchild.type == "string":
                                                module_name = (
                                                    self._extract_string_value(
                                                        ggggchild
                                                    )
                                                )
                                                break
                                break
                break

        return module_name, symbols

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

        # Calculate target path based on relative import
        if module_name.startswith("./"):
            # Same directory
            target_path = source_dir / module_name[2:]
        elif module_name.startswith("../"):
            # Parent directory - count the number of ../ segments
            parts = module_name.split("/")
            target_dir = source_dir

            i = 0
            while i < len(parts) and parts[i] == "..":
                target_dir = target_dir.parent
                i += 1

            # Remaining parts form the module path
            if i < len(parts):
                remaining_path = "/".join(parts[i:])
                target_path = target_dir / remaining_path
            else:
                target_path = target_dir
        else:
            # Remove leading ./ if present
            clean_name = module_name.lstrip("./")
            target_path = source_dir / clean_name

        # Try to find matching module names in registry
        possible_names = self._get_potential_module_names(target_path)

        # Also try with common TypeScript/JavaScript extensions
        for ext in ["", ".ts", ".tsx", ".js", ".jsx"]:
            ext_path = target_path.with_suffix(ext)
            possible_names.extend(self._get_potential_module_names(ext_path))

        # Try as index file in directory
        for index_name in ["index.ts", "index.tsx", "index.js", "index.jsx"]:
            index_path = target_path / index_name
            possible_names.extend(self._get_potential_module_names(index_path))

        # Look for matches in registry
        for name in possible_names:
            if name in module_registry:
                return module_registry[name]

        return None

    def _is_dynamic_import_call_node(self, node) -> bool:
        """Check if a call_expression node is a dynamic import call."""
        if not hasattr(node, "children") or not node.children:
            return False

        # Check if the first child is 'import'
        first_child = node.children[0]
        if hasattr(first_child, "type") and first_child.type == "import":
            return True

        return False

    def _is_require_call_node(self, node) -> bool:
        """Check if a call_expression node is a require call."""
        if not hasattr(node, "children") or not node.children:
            return False

        # Check if the first child is an identifier with text 'require'
        first_child = node.children[0]
        if (
            hasattr(first_child, "type")
            and first_child.type == "identifier"
            and self._safe_text_extract(first_child) == "require"
        ):
            return True

        return False

    def _extract_call_string_argument(self, node) -> Optional[str]:
        """Extract the first string argument from a call expression."""
        if not hasattr(node, "children"):
            return None

        # Look for arguments containing the module path
        for child in node.children:
            if hasattr(child, "type") and child.type == "arguments":
                for arg_child in child.children:
                    if hasattr(arg_child, "type") and arg_child.type == "string":
                        # Extract the string content
                        return self._extract_string_value(arg_child)

        return None

    def _resolve_absolute_import(
        self, module_name: str, module_registry: Dict[str, str]
    ) -> Optional[str]:
        """Resolve an absolute import using the module registry."""
        # For absolute imports that aren't relative paths, try to find matches
        # in the registry by checking if any registered names end with the module name

        # Direct lookup first
        if module_name in module_registry:
            return module_registry[module_name]

        # Try with common path prefixes
        common_prefixes = ["src/", "lib/", "dist/", ""]
        for prefix in common_prefixes:
            prefixed_name = prefix + module_name
            if prefixed_name in module_registry:
                return module_registry[prefixed_name]

        # Try looking for partial matches
        for registered_name, file_id in module_registry.items():
            if registered_name.endswith(module_name):
                return file_id
            if module_name.endswith(registered_name):
                return file_id

        return None

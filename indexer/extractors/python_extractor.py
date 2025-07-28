"""Python Extractor for Code Block Extraction

This module provides Python-specific extraction capabilities for identifying
and extracting code blocks from Python AST nodes using tree-sitter.
"""

from typing import List, Any, Dict, Set, Callable, Optional
from tree_sitter_language_pack import SupportedLanguage
from . import BaseExtractor, CodeBlock, BlockType


class PythonExtractor(BaseExtractor):
    """Python-specific extractor for code blocks."""

    def __init__(self, language: SupportedLanguage, symbol_extractor=None):
        super().__init__(language, symbol_extractor)

    # ============================================================================
    # GENERIC HELPER METHODS
    # ============================================================================

    def _get_identifier_name(self, node: Any) -> str:
        """Extract identifier name from a node."""
        if node.type == "identifier":
            return self._get_node_text(node)
        return ""

    def _generic_traversal(
        self,
        root_node: Any,
        target_types: Set[str],
        processor: Callable[[Any], Optional[CodeBlock]],
    ) -> List[CodeBlock]:
        """Generic traversal method for extracting blocks of specific types."""
        blocks = []

        def traverse(node):
            if node.type in target_types:
                block = processor(node)
                if block:
                    blocks.append(block)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks

    def _extract_names_from_node(self, node: Any) -> List[str]:
        """Extract all identifier names from a node (handles various patterns)."""
        names = []

        if node.type == "identifier":
            names.append(self._get_node_text(node))
        elif node.type in ["tuple_pattern", "list_pattern"]:
            names.extend(self._extract_pattern_names(node))
        elif node.type == "assignment":
            names.extend(self._extract_assignment_names(node))
        else:
            # Generic fallback: find all identifiers in the node
            def find_identifiers(n):
                if n.type == "identifier":
                    names.append(self._get_node_text(n))
                for child in n.children:
                    find_identifiers(child)

            find_identifiers(node)

        return list(set(names))  # Remove duplicates

    def _create_block_with_nested(
        self,
        node: Any,
        block_type: BlockType,
        names: List[str],
        nested_types: Dict[str, BlockType] = None,
    ) -> CodeBlock:
        """Create a code block and extract nested elements."""
        block = self._create_code_block(node, block_type, names)

        if nested_types:
            nested_blocks = []
            for node_type, nested_block_type in nested_types.items():
                nested_blocks.extend(
                    self._extract_nested_elements_by_type(
                        node, {node_type}, nested_block_type
                    )
                )
            block.children = nested_blocks

        return block

    def _extract_nested_elements_by_type(
        self, parent_node: Any, target_types: Set[str], block_type: BlockType
    ) -> List[CodeBlock]:
        """Generic method to extract nested elements of specific types."""

        def processor(node):
            names = self._extract_names_from_node(node)
            if names:
                return self._create_code_block(node, block_type, names)
            return None

        return self._generic_traversal(parent_node, target_types, processor)

    # ============================================================================
    # SPECIALIZED NAME EXTRACTION METHODS
    # ============================================================================

    def _extract_assignment_names(self, node: Any) -> List[str]:
        """Extract names from assignment statements."""
        names = []
        if node.type == "assignment":
            left_node = node.child_by_field_name("left")
            if left_node:
                names.extend(self._extract_names_from_node(left_node))
        return names

    def _extract_pattern_names(self, node: Any) -> List[str]:
        """Extract names from pattern nodes (tuple, list patterns)."""
        names = []
        for child in node.children:
            if child.type == "identifier":
                names.append(self._get_node_text(child))
            elif child.type in ["tuple_pattern", "list_pattern"]:
                names.extend(self._extract_pattern_names(child))
        return names

    def _extract_import_name(self, node: Any) -> str:
        """Extract module name from import statement."""
        if node.type == "import_statement":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.type == "dotted_name":
                return self._get_node_text(name_node)
        elif node.type == "import_from_statement":
            module_name = node.child_by_field_name("module_name")
            if module_name:
                return self._get_node_text(module_name)
        return ""

    # ============================================================================
    # MAIN EXTRACTION METHODS
    # ============================================================================

    def extract_imports(self, root_node: Any) -> List[CodeBlock]:
        """Extract import statements."""

        def process_import(node):
            import_name = self._extract_import_name(node)
            names = [import_name] if import_name else []

            # Add imported symbols
            if node.type == "import_from_statement":
                names.extend(self._extract_imported_symbols(node))
            elif node.type == "import_statement":
                name_node = node.child_by_field_name("name")
                if name_node:
                    names.append(self._get_node_text(name_node))

            return self._create_code_block(node, BlockType.IMPORT, names)

        import_types = {"import_statement", "import_from_statement"}
        blocks = self._generic_traversal(root_node, import_types, process_import)

        # Add dynamic imports
        blocks.extend(self._find_dynamic_imports(root_node))
        return blocks

    def extract_exports(self, root_node: Any) -> List[CodeBlock]:
        """Extract export statements (Python __all__ declarations)."""
        return self._extract_top_level_exports(root_node)

    def extract_functions(self, root_node: Any) -> List[CodeBlock]:
        """Extract function definitions."""

        def process_function(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            nested_types = {
                "function_definition": BlockType.FUNCTION,
                "assignment": BlockType.VARIABLE,
            }
            return self._create_block_with_nested(
                node, BlockType.FUNCTION, names, nested_types
            )

        return self._generic_traversal(
            root_node, {"function_definition"}, process_function
        )

    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """Extract class definitions."""

        def process_class(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            nested_types = {
                "function_definition": BlockType.FUNCTION,
                "assignment": BlockType.VARIABLE,
                "class_definition": BlockType.CLASS,
            }
            return self._create_block_with_nested(
                node, BlockType.CLASS, names, nested_types
            )

        return self._generic_traversal(root_node, {"class_definition"}, process_class)

    def extract_variables(self, root_node: Any) -> List[CodeBlock]:
        """Extract variable assignments."""

        def process_variable(node):
            names = self._extract_assignment_names(node)
            return (
                self._create_code_block(node, BlockType.VARIABLE, names)
                if names
                else None
            )

        return self._generic_traversal(root_node, {"assignment"}, process_variable)

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all types of code blocks."""
        all_blocks = []
        all_blocks.extend(self.extract_imports(root_node))
        all_blocks.extend(self.extract_exports(root_node))
        all_blocks.extend(self.extract_functions(root_node))
        all_blocks.extend(self.extract_classes(root_node))
        all_blocks.extend(self.extract_variables(root_node))
        return all_blocks

    # ============================================================================
    # SPECIALIZED EXTRACTION METHODS
    # ============================================================================

    def _find_dynamic_imports(self, root_node: Any) -> List[CodeBlock]:
        """Find dynamic import calls like importlib.import_module()."""
        blocks = []

        def traverse(node):
            if self._is_dynamic_import_call(node):
                import_name = self._extract_dynamic_import_name(node)
                if import_name:
                    block = self._create_code_block(
                        node, BlockType.IMPORT, [import_name]
                    )
                    blocks.append(block)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks

    def _is_dynamic_import_call(self, node: Any) -> bool:
        """Check if node is a dynamic import call."""
        if node.type != "call":
            return False

        function_node = node.child_by_field_name("function")
        if not function_node:
            return False

        function_text = self._get_node_text(function_node)
        dynamic_import_patterns = [
            "importlib.import_module",
            "__import__",
            "importlib.__import__",
        ]

        return any(pattern in function_text for pattern in dynamic_import_patterns)

    def _extract_dynamic_import_name(self, node: Any) -> str:
        """Extract module name from dynamic import call."""
        arguments = node.child_by_field_name("arguments")
        if arguments and arguments.children:
            first_arg = arguments.children[1] if len(arguments.children) > 1 else None
            if first_arg and first_arg.type == "string":
                return self._get_node_text(first_arg).strip("\"'")
        return ""

    def _extract_top_level_exports(self, root_node: Any) -> List[CodeBlock]:
        """Extract __all__ declarations."""
        blocks = []

        for child in root_node.children:
            if child.type == "assignment":
                left_node = child.child_by_field_name("left")
                if left_node and self._get_node_text(left_node) == "__all__":
                    names = ["__all__"]
                    block = self._create_code_block(child, BlockType.EXPORT, names)
                    blocks.append(block)

        return blocks

    def _extract_imported_symbols(self, node: Any) -> List[str]:
        """Extract imported symbols from import_from_statement."""
        names = []
        for child in node.children:
            if child.type == "import_list":
                for import_child in child.children:
                    if import_child.type in ["identifier", "aliased_import"]:
                        if import_child.type == "import_specifier":
                            if import_child.type == "identifier":
                                names.append(self._get_node_text(import_child))
                            elif import_child.type == "aliased_import":
                                name_node = import_child.child_by_field_name("name")
                                if name_node:
                                    names.append(self._get_node_text(name_node))
        return names

    # Note: Interface and enum extraction methods removed as they're not applicable to Python
    def extract_interfaces(self, root_node: Any) -> List[CodeBlock]:
        """Extract interfaces (not applicable to Python)."""
        return []

    def extract_enums(self, root_node: Any) -> List[CodeBlock]:
        """Extract enums (Python enum.Enum classes)."""

        def process_enum(node):
            # Check if this class inherits from Enum
            superclasses = node.child_by_field_name("superclasses")
            if superclasses:
                superclass_text = self._get_node_text(superclasses)
                if "Enum" in superclass_text:
                    name_node = node.child_by_field_name("name")
                    names = [self._get_node_text(name_node)] if name_node else []

                    nested_types = {"assignment": BlockType.VARIABLE}
                    return self._create_block_with_nested(
                        node, BlockType.ENUM, names, nested_types
                    )
            return None

        return self._generic_traversal(root_node, {"class_definition"}, process_enum)

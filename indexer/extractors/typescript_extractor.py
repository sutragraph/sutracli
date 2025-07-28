"""TypeScript Extractor for Code Block Extraction

This module provides TypeScript-specific extraction capabilities for identifying
and extracting code blocks from TypeScript AST nodes using tree-sitter.
"""

from typing import List, Any, Dict, Set, Callable, Optional
from tree_sitter_language_pack import SupportedLanguage
from . import BaseExtractor, CodeBlock, BlockType


class TypeScriptExtractor(BaseExtractor):
    """TypeScript-specific extractor for code blocks."""

    def __init__(self, language: SupportedLanguage, symbol_extractor=None):
        super().__init__(language, symbol_extractor)

    # ============================================================================
    # GENERIC HELPER METHODS
    # ============================================================================

    def _get_identifier_name(self, node: Any) -> str:
        """Extract identifier name from a node."""
        if node.type == "identifier":
            return self._get_node_text(node)
        elif node.type == "property_identifier":
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

        if node.type in ["identifier", "property_identifier"]:
            names.append(self._get_node_text(node))
        elif node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            if name_node:
                names.extend(self._extract_names_from_node(name_node))
        elif node.type in ["object_pattern", "array_pattern"]:
            names.extend(self._extract_destructuring_names(node))
        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))
        elif node.type == "interface_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))
        elif node.type == "enum_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))
        else:
            # Generic fallback: find all identifiers in the node
            def find_identifiers(n):
                if n.type in ["identifier", "property_identifier"]:
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

    def _extract_destructuring_names(self, node: Any) -> List[str]:
        """Extract names from destructuring patterns."""
        names = []

        if node.type == "object_pattern":
            names.extend(self._extract_object_pattern_names(node))
        elif node.type == "array_pattern":
            names.extend(self._extract_array_pattern_names(node))

        return names

    def _extract_object_pattern_names(self, node: Any) -> List[str]:
        """Extract names from object destructuring pattern."""
        names = []
        for child in node.children:
            if child.type == "shorthand_property_identifier_pattern":
                names.append(self._get_node_text(child))
            elif child.type == "pair_pattern":
                value_node = child.child_by_field_name("value")
                if value_node:
                    names.extend(self._extract_names_from_node(value_node))
        return names

    def _extract_array_pattern_names(self, node: Any) -> List[str]:
        """Extract names from array destructuring pattern."""
        names = []
        for child in node.children:
            if child.type == "identifier":
                names.append(self._get_node_text(child))
        return names

    def _extract_variable_names(self, node: Any) -> List[str]:
        """Extract variable names from variable declaration."""
        names = []
        if node.type == "variable_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        names.extend(self._extract_names_from_node(name_node))
        return names

    def _extract_import_name(self, node: Any) -> str:
        """Extract module name from import statement."""
        source_node = node.child_by_field_name("source")
        if source_node and source_node.type == "string":
            return self._get_node_text(source_node).strip("\"'")
        return ""

    def _extract_named_imports(self, node: Any) -> List[str]:
        """Extract named import identifiers."""
        names = []
        for child in node.children:
            if child.type == "named_imports":
                for import_child in child.children:
                    if import_child.type == "import_specifier":
                        name_node = import_child.child_by_field_name("name")
                        if name_node:
                            names.append(self._get_node_text(name_node))
        return names

    def _extract_export_names(self, node: Any) -> List[str]:
        """Extract export names from export statement."""
        names = []

        # Handle different export types
        if node.type == "export_statement":
            for child in node.children:
                if child.type == "export_clause":
                    for export_child in child.children:
                        if export_child.type == "export_specifier":
                            name_node = export_child.child_by_field_name("name")
                            if name_node:
                                names.append(self._get_node_text(name_node))
        elif node.type in [
            "function_declaration",
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
        ]:
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))

        return names

    # ============================================================================
    # MAIN EXTRACTION METHODS
    # ============================================================================

    def extract_imports(self, root_node: Any) -> List[CodeBlock]:
        """Extract import statements."""

        def process_import(node):
            import_name = self._extract_import_name(node)
            names = [import_name] if import_name else []

            # Add imported symbols
            names.extend(self._extract_named_imports(node))

            # Handle default imports
            for child in node.children:
                if child.type == "identifier":
                    names.append(self._get_node_text(child))

            return self._create_code_block(node, BlockType.IMPORT, names)

        import_types = {"import_statement"}
        blocks = self._generic_traversal(root_node, import_types, process_import)

        # Add dynamic imports
        blocks.extend(self._find_dynamic_imports(root_node))
        blocks.extend(self._find_require_calls(root_node))

        return blocks

    def extract_exports(self, root_node: Any) -> List[CodeBlock]:
        """Extract export statements."""

        def process_export(node):
            names = self._extract_export_names(node)
            return (
                self._create_code_block(node, BlockType.EXPORT, names)
                if names
                else None
            )

        export_types = {
            "export_statement",
            "export_default_statement",
            "export_assignment",
        }
        return self._generic_traversal(root_node, export_types, process_export)

    def extract_functions(self, root_node: Any) -> List[CodeBlock]:
        """Extract function declarations."""

        def process_function(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            nested_types = {
                "function_declaration": BlockType.FUNCTION,
                "method_definition": BlockType.FUNCTION,
                "variable_declaration": BlockType.VARIABLE,
            }
            return self._create_block_with_nested(
                node, BlockType.FUNCTION, names, nested_types
            )

        function_types = {
            "function_declaration",
            "function_expression",
            "arrow_function",
            "method_definition",
        }
        return self._generic_traversal(root_node, function_types, process_function)

    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """Extract class declarations."""

        def process_class(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            nested_types = {
                "method_definition": BlockType.FUNCTION,
                "field_definition": BlockType.VARIABLE,
                "class_declaration": BlockType.CLASS,
            }
            return self._create_block_with_nested(
                node, BlockType.CLASS, names, nested_types
            )

        return self._generic_traversal(root_node, {"class_declaration"}, process_class)

    def extract_interfaces(self, root_node: Any) -> List[CodeBlock]:
        """Extract interface declarations."""

        def process_interface(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            nested_types = {
                "property_signature": BlockType.VARIABLE,
                "method_signature": BlockType.FUNCTION,
            }
            return self._create_block_with_nested(
                node, BlockType.INTERFACE, names, nested_types
            )

        return self._generic_traversal(
            root_node, {"interface_declaration"}, process_interface
        )

    def extract_enums(self, root_node: Any) -> List[CodeBlock]:
        """Extract enum declarations."""

        def process_enum(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            nested_types = {"property_identifier": BlockType.VARIABLE}
            return self._create_block_with_nested(
                node, BlockType.ENUM, names, nested_types
            )

        return self._generic_traversal(root_node, {"enum_declaration"}, process_enum)

    def extract_variables(self, root_node: Any) -> List[CodeBlock]:
        """Extract variable declarations."""

        def process_variable(node):
            names = self._extract_variable_names(node)
            return (
                self._create_code_block(node, BlockType.VARIABLE, names)
                if names
                else None
            )

        return self._generic_traversal(
            root_node, {"variable_declaration"}, process_variable
        )

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all types of code blocks."""
        all_blocks = []
        all_blocks.extend(self.extract_imports(root_node))
        all_blocks.extend(self.extract_exports(root_node))
        all_blocks.extend(self.extract_enums(root_node))
        all_blocks.extend(self.extract_variables(root_node))
        all_blocks.extend(self.extract_functions(root_node))
        all_blocks.extend(self.extract_classes(root_node))
        all_blocks.extend(self.extract_interfaces(root_node))
        return all_blocks

    # ============================================================================
    # SPECIALIZED DETECTION METHODS
    # ============================================================================

    def _find_dynamic_imports(self, root_node: Any) -> List[CodeBlock]:
        """Find dynamic import() calls."""
        blocks = []

        def traverse(node):
            if self._is_dynamic_import(node):
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

    def _find_require_calls(self, root_node: Any) -> List[CodeBlock]:
        """Find require() calls."""
        blocks = []

        def traverse(node):
            if self._is_require_call(node):
                import_name = self._extract_require_name(node)
                if import_name:
                    block = self._create_code_block(
                        node, BlockType.IMPORT, [import_name]
                    )
                    blocks.append(block)

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks

    def _is_dynamic_import(self, node: Any) -> bool:
        """Check if node is a dynamic import() call."""
        if node.type != "call_expression":
            return False

        function_node = node.child_by_field_name("function")
        if not function_node:
            return False

        return self._get_node_text(function_node) == "import"

    def _is_require_call(self, node: Any) -> bool:
        """Check if node is a require() call."""
        if node.type != "call_expression":
            return False

        function_node = node.child_by_field_name("function")
        if not function_node:
            return False

        return self._get_node_text(function_node) == "require"

    def _extract_dynamic_import_name(self, node: Any) -> str:
        """Extract module name from dynamic import."""
        arguments = node.child_by_field_name("arguments")
        if arguments and arguments.children:
            first_arg = arguments.children[1] if len(arguments.children) > 1 else None
            if first_arg and first_arg.type == "string":
                return self._get_node_text(first_arg).strip("\"'")
        return ""

    def _extract_require_name(self, node: Any) -> str:
        """Extract module name from require call."""
        arguments = node.child_by_field_name("arguments")
        if arguments and arguments.children:
            first_arg = arguments.children[1] if len(arguments.children) > 1 else None
            if first_arg and first_arg.type == "string":
                return self._get_node_text(first_arg).strip("\"'")
        return ""

    def _get_method_name(self, node: Any) -> str:
        """Extract method name from method definition."""
        key_node = node.child_by_field_name("name")
        if key_node:
            return self._get_node_text(key_node)
        return ""

    def _is_function_assignment(self, node: Any) -> bool:
        """Check if node is a function assignment."""
        if node.type != "assignment_expression":
            return False

        right_node = node.child_by_field_name("right")
        return right_node and right_node.type in [
            "function_expression",
            "arrow_function",
        ]

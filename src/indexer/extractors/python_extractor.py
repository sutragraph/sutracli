"""Python Extractor for Code Block Extraction

This module provides Python-specific extraction capabilities for identifying
and extracting code blocks from Python AST nodes using tree-sitter.
"""

from typing import List, Any, Dict, Set, Callable, Optional
from tree_sitter_language_pack import SupportedLanguage
from . import BaseExtractor, CodeBlock, BlockType


class PythonExtractor(BaseExtractor):
    """Python-specific extractor for code blocks."""

    # Define node types once as class constants
    FUNCTION_TYPES = {"function_definition"}
    CLASS_TYPES = {"class_definition"}
    VARIABLE_TYPES = {"assignment"}

    def __init__(self, language: SupportedLanguage, file_id: int = 0):
        super().__init__(language, file_id)

    # ============================================================================
    # GENERIC HELPER METHODS
    # ============================================================================

    def _get_identifier_name(self, node: Any) -> str:
        """Extract identifier name from a node."""
        if node.type == "identifier":
            return self._get_node_text(node)
        return ""

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

    def _replace_nested_functions_with_references(
        self, original_content: str, nested_functions: List[CodeBlock]
    ) -> str:
        """Replace nested function content with block references for Python."""
        if not nested_functions:
            return original_content

        # Sort nested functions by start position (descending) to avoid offset issues
        sorted_functions = sorted(
            nested_functions, key=lambda f: f.start_line, reverse=True
        )

        for func in sorted_functions:
            # Find the nested function in the parent content
            func_content = func.content
            func_lines = func_content.split("\n")

            # Create Python comment reference
            reference = f"# [BLOCK_REF:{func.id}]"

            # For Python, find the function signature (lines ending with :)
            signature_lines = []
            for line in func_lines:
                signature_lines.append(line)
                if line.strip().endswith(":"):
                    # Found the end of signature, add reference and stop
                    signature_lines.append(f"    {reference}")
                    break
            replacement = "\n".join(signature_lines)

            # Replace the entire function content with the signature + reference
            original_content = original_content.replace(func_content, replacement)

        return original_content

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
        """Extract function definitions with nested function extraction for large functions."""

        def process_function(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            # Use the new nested function extraction logic
            return self._create_function_block_with_nested_extraction(
                node, BlockType.FUNCTION, names, self.FUNCTION_TYPES
            )

        return self._generic_traversal(root_node, self.FUNCTION_TYPES, process_function)

    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """Extract class definitions with 300-line check for methods."""

        def process_class(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            # Create class block without content (since everything is in nested blocks)
            start_line, end_line, start_col, end_col = self._get_node_position(node)

            class_block = CodeBlock(
                type=BlockType.CLASS,
                name=names[0] if names else "anonymous",
                content="",  # No content since everything is in nested blocks
                start_line=start_line,
                end_line=end_line,
                start_col=start_col,
                end_col=end_col,
                id=self._hash_generator.next_id(),
            )

            # Extract nested elements with 300-line check for methods
            nested_blocks = []

            # Extract methods with 300-line nested function extraction
            def process_method(method_node):
                if method_node.type == "function_definition":
                    name_node = method_node.child_by_field_name("name")
                    method_names = [self._get_node_text(name_node)] if name_node else []

                    # Apply 300-line check to methods
                    return self._create_function_block_with_nested_extraction(
                        method_node,
                        BlockType.FUNCTION,
                        method_names,
                        self.FUNCTION_TYPES,
                    )
                return None

            methods = self._generic_traversal(node, self.FUNCTION_TYPES, process_method)
            nested_blocks.extend(methods)

            # Extract class-level variables only (not variables inside methods)
            class_level_variables = self._extract_class_level_variables(node)
            nested_blocks.extend(class_level_variables)

            class_block.children = nested_blocks
            return class_block

        return self._generic_traversal(root_node, self.CLASS_TYPES, process_class)

    def extract_variables(self, root_node: Any) -> List[CodeBlock]:
        """Extract variable assignments."""
        blocks = []

        def process_variable(node):
            names = self._extract_assignment_names(node)
            return (
                self._create_code_block(node, BlockType.VARIABLE, names)
                if names
                else None
            )

        # Only look at direct children of root_node
        for child in root_node.children:
            if child.type in self.VARIABLE_TYPES:
                block = process_variable(child)
                if block:
                    blocks.append(block)

        return blocks

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Extract all types of code blocks."""
        all_blocks = []
        all_blocks.extend(self.extract_imports(root_node))
        all_blocks.extend(self.extract_exports(root_node))
        all_blocks.extend(self.extract_enums(root_node))
        all_blocks.extend(self.extract_variables(root_node))
        all_blocks.extend(self.extract_functions(root_node))
        all_blocks.extend(self.extract_classes(root_node))
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

    def _extract_class_level_variables(self, class_node: Any) -> List[CodeBlock]:
        """Extract only class-level variables, not variables inside methods."""
        variables = []

        # Look for the class body (block node)
        for child in class_node.children:
            if child.type == "block":
                # Now look at direct children of the block for expression_statements
                for block_child in child.children:
                    if block_child.type == "expression_statement":
                        # Check if this expression_statement contains an assignment
                        for expr_child in block_child.children:
                            if expr_child.type == "assignment":
                                # This is a class-level assignment
                                names = self._extract_assignment_names(expr_child)
                                if names:
                                    variable_block = self._create_code_block(
                                        expr_child, BlockType.VARIABLE, names
                                    )
                                    variables.append(variable_block)

        return variables

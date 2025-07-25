"""
Python AST Extractor

Extracts Python code constructs from AST trees.
"""

from typing import Any, List
from . import BaseExtractor, BlockType, CodeBlock


class PythonExtractor(BaseExtractor):
    """Extractor for Python code blocks."""

    def __init__(self, language: str = "python", symbol_extractor=None):
        super().__init__(language, symbol_extractor)

    # _traverse_nodes method moved to BaseExtractor

    def _get_identifier_name(self, node: Any) -> str:
        """Get identifier name from a node."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    return self._get_node_text(child)
        return ""

    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements, including dynamic imports."""
        blocks = []

        # Extract static import statements
        import_nodes = self._traverse_nodes(
            node, ["import_statement", "import_from_statement"]
        )

        for import_node in import_nodes:
            start_line, end_line, start_col, end_col = self._get_node_position(
                import_node
            )
            content = self._get_node_text(import_node)

            # Extract the module name or first imported name as the identifier
            name = self._extract_import_name(import_node)

            blocks.append(
                self._create_code_block(
                    BlockType.IMPORT,
                    name,
                    content,
                    start_line,
                    end_line,
                    start_col,
                    end_col,
                    import_node,
                )
            )

        # Extract dynamic imports
        dynamic_import_nodes = self._find_dynamic_imports(node)

        for dynamic_node in dynamic_import_nodes:
            start_line, end_line, start_col, end_col = self._get_node_position(
                dynamic_node
            )
            content = self._get_node_text(dynamic_node)
            module_name = self._extract_dynamic_import_name(dynamic_node)

            blocks.append(
                self._create_code_block(
                    BlockType.IMPORT,
                    module_name or "dynamic_import",
                    content,
                    start_line,
                    end_line,
                    start_col,
                    end_col,
                    dynamic_node,
                )
            )

        return blocks

    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Extract export declarations."""
        exports = self._extract_top_level_exports(node)
        return exports

    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract function declarations with nested elements as children."""
        functions = self._extract_top_level_functions(node)
        for function in functions:
            function.children = self._extract_nested_elements(node, function)
        return functions

    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract class declarations with nested elements as children."""
        classes = self._extract_top_level_classes(node)
        for class_block in classes:
            class_block.children = self._extract_nested_elements(node, class_block)
        return classes

    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract variable declarations."""
        return self._extract_top_level_variables(node)

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """Python-specific implementation of extract_all.
        Extracts all supported code blocks with hierarchical structure.
        """
        self._blocks = []

        # First, extract all symbols from the entire file
        self._extract_all_symbols(root_node)

        # Then extract top-level blocks with their nested children
        # Python-specific order and handling
        self._blocks.extend(self.extract_imports(root_node))
        self._blocks.extend(self.extract_exports(root_node))  # __all__ declarations
        self._blocks.extend(self.extract_variables(root_node))
        self._blocks.extend(self.extract_functions(root_node))
        self._blocks.extend(self.extract_classes(root_node))

        return self._blocks

    def _find_dynamic_imports(self, node: Any) -> List[Any]:
        """Find dynamic import calls like importlib.import_module() and __import__()."""
        dynamic_imports = []

        def traverse(n):
            if hasattr(n, "type"):
                if n.type == "call":
                    # Check if this is a dynamic import call
                    if self._is_dynamic_import_call(n):
                        dynamic_imports.append(n)

            if hasattr(n, "children"):
                for child in n.children:
                    traverse(child)

        traverse(node)
        return dynamic_imports

    def _is_dynamic_import_call(self, node: Any) -> bool:
        """Check if a call node is a dynamic import."""
        if not hasattr(node, 'children') or not node.children:
            return False

        # Get the function being called
        function_node = node.children[0]

        # Check for __import__() calls
        if (hasattr(function_node, 'type') and function_node.type == 'identifier' and
            hasattr(function_node, 'text') and
            self._get_node_text(function_node).strip() == '__import__'):
            return True

        # Check for importlib.import_module() calls
        if hasattr(function_node, 'type') and function_node.type == 'attribute':
            # Get the full attribute path
            attr_text = self._get_node_text(function_node)
            if 'importlib.import_module' in attr_text or 'import_module' in attr_text:
                return True

        return False

    def _extract_dynamic_import_name(self, node: Any) -> str:
        """Extract module name from a dynamic import call."""
        if not hasattr(node, 'children'):
            return ""

        # Look for argument_list containing the module path
        for child in node.children:
            if hasattr(child, 'type') and child.type == 'argument_list':
                for arg_child in child.children:
                    if hasattr(arg_child, 'type') and arg_child.type == 'string':
                        # Extract the string content
                        text = self._get_node_text(arg_child)
                        # Remove quotes
                        return text.strip('\'"')

        return ""

    def _extract_top_level_exports(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level export declarations (Python uses __all__ for explicit exports)."""
        blocks = []

        # Look for __all__ assignments
        assignment_nodes = self._traverse_nodes(node, ["assignment"])

        for assignment_node in assignment_nodes:
            if hasattr(assignment_node, "children"):
                for child in assignment_node.children:
                    if hasattr(child, "type") and child.type == "identifier":
                        if self._get_node_text(child) == "__all__":
                            start_line, end_line, start_col, end_col = (
                                self._get_node_position(assignment_node)
                            )
                            content = self._get_node_text(assignment_node)

                            blocks.append(
                                self._create_code_block(
                                    BlockType.EXPORT,
                                    "__all__",
                                    content,
                                    start_line,
                                    end_line,
                                    start_col,
                                    end_col,
                                    assignment_node,
                                )
                            )
                            break

        return blocks

    def _extract_assignment_names(self, assignment_node: Any) -> List[str]:
        """Extract variable names from assignment statement."""
        names = []

        if hasattr(assignment_node, "children"):
            for child in assignment_node.children:
                if hasattr(child, "type"):
                    if child.type == "identifier":
                        names.append(self._get_node_text(child))
                    elif child.type == "pattern_list":
                        names.extend(self._extract_pattern_names(child))

        return names

    def _extract_pattern_names(self, pattern_node: Any) -> List[str]:
        """Extract names from pattern (for tuple unpacking, etc.)."""
        names = []

        if hasattr(pattern_node, "children"):
            for child in pattern_node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    names.append(self._get_node_text(child))

        return names

    def _extract_import_name(self, import_node: Any) -> str:
        """Extract the primary name from an import statement."""
        if hasattr(import_node, "children"):
            for child in import_node.children:
                if hasattr(child, "type"):
                    if child.type == "dotted_name":
                        return self._get_node_text(child)
                    elif child.type == "identifier":
                        return self._get_node_text(child)
                    elif child.type == "aliased_import":
                        # For "import x as y", return "y"
                        if hasattr(child, "children"):
                            for grandchild in child.children:
                                if (
                                    hasattr(grandchild, "type")
                                    and grandchild.type == "identifier"
                                ):
                                    return self._get_node_text(grandchild)

        return "unknown"

    def _get_nested_identifier_name(self, node: Any) -> str:
        """Get identifier name from a nested Python node."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    return self._get_node_text(child)
        return ""

    def _get_nested_variable_names(self, node: Any) -> List[str]:
        """Get variable names from a nested Python assignment node."""
        names = []

        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type"):
                    if child.type == "identifier":
                        names.append(self._get_node_text(child))
                    elif child.type == "pattern_list":
                        names.extend(self._extract_pattern_names(child))

        return names

    def _extract_nested_variables(self, parent_node: Any) -> List[CodeBlock]:
        """Extract variable declarations nested within a Python parent node."""
        nested_variables = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                if (
                    node.type == "assignment" and depth > 0
                ):  # Skip direct children, only nested
                    names = self._get_nested_variable_names(node)
                    if names:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)
                        for name in names:
                            nested_variables.append(
                                self._create_code_block(
                                    BlockType.VARIABLE,
                                    name,
                                    content,
                                    start_line,
                                    end_line,
                                    start_col,
                                    end_col,
                                    node,
                                )
                            )

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_variables

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract function declarations nested within a Python parent node."""
        nested_functions = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                function_types = ["function_definition", "async_function_definition"]

                if node.type in function_types and depth > 0:
                    name = self._get_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)

                        nested_functions.append(
                            self._create_code_block(
                                BlockType.FUNCTION,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                node,
                            )
                        )
                        return  # Don't traverse deeper from this function

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_functions

    def _extract_nested_classes(self, parent_node: Any) -> List[CodeBlock]:
        """Extract class declarations nested within a Python parent node."""
        nested_classes = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                if node.type == "class_definition" and depth > 0:
                    name = self._get_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)

                        nested_classes.append(
                            self._create_code_block(
                                BlockType.CLASS,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                node,
                            )
                        )
                        return

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_classes

    def _extract_top_level_functions(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level function declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are function definitions
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type in [
                    "function_definition",
                    "async_function_definition",
                ]:
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(child)
                        )
                        content = self._get_node_text(child)
                        blocks.append(
                            self._create_code_block(
                                BlockType.FUNCTION,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                child,
                            )
                        )

        return blocks

    def _extract_top_level_classes(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level class declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are class definitions
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "class_definition":
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(child)
                        )
                        content = self._get_node_text(child)
                        blocks.append(
                            self._create_code_block(
                                BlockType.CLASS,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                child,
                            )
                        )

        return blocks

    def _extract_top_level_variables(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level variable declarations from Python module."""
        blocks = []

        # Look for direct children of the module that are assignments
        # In Python AST, module-level assignments are often wrapped in expression_statement nodes
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type"):
                    if child.type == "assignment":
                        names = self._extract_assignment_names(child)
                        if names:
                            start_line, end_line, start_col, end_col = (
                                self._get_node_position(child)
                            )
                            content = self._get_node_text(child)
                            for name in names:
                                blocks.append(
                                    self._create_code_block(
                                        BlockType.VARIABLE,
                                        name,
                                        content,
                                        start_line,
                                        end_line,
                                        start_col,
                                        end_col,
                                        child,
                                    )
                                )
                    elif child.type == "expression_statement":
                        # Look for assignment nodes inside expression_statement
                        if hasattr(child, "children"):
                            for grandchild in child.children:
                                if (
                                    hasattr(grandchild, "type")
                                    and grandchild.type == "assignment"
                                ):
                                    names = self._extract_assignment_names(grandchild)
                                    if names:
                                        start_line, end_line, start_col, end_col = (
                                            self._get_node_position(grandchild)
                                        )
                                        content = self._get_node_text(grandchild)
                                        for name in names:
                                            blocks.append(
                                                self._create_code_block(
                                                    BlockType.VARIABLE,
                                                    name,
                                                    content,
                                                    start_line,
                                                    end_line,
                                                    start_col,
                                                    end_col,
                                                    grandchild,
                                                )
                                            )

        return blocks

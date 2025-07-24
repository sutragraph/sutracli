"""
TypeScript AST Extractor

Extracts TypeScript/JavaScript code constructs from AST trees.
"""

from typing import Any, List
from . import BaseExtractor, BlockType, CodeBlock


class TypeScriptExtractor(BaseExtractor):
    """Extractor for TypeScript/JavaScript code blocks."""

    def __init__(self, language: str = "typescript", symbol_extractor=None):
        super().__init__(language, symbol_extractor)

    def _get_identifier_name(self, node: Any) -> str:
        """Get identifier name from a node."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type in [
                    "identifier",
                    "type_identifier",
                ]:
                    return self._get_node_text(child)
        return ""

    def extract_imports(self, node: Any) -> List[CodeBlock]:
        """Extract import statements."""
        imports = []

        def traverse(n):
            if hasattr(n, "type"):
                if n.type == "import_statement":
                    start_line, end_line, start_col, end_col = self._get_node_position(
                        n
                    )
                    content = self._get_node_text(n)

                    # Try to extract the module name
                    module_name = self._extract_import_name(n)

                    imports.append(
                        self._create_code_block(
                            BlockType.IMPORT,
                            module_name,
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            n,
                        )
                    )
                    return  # Don't traverse deeper from this import

            if hasattr(n, "children"):
                for child in n.children:
                    traverse(child)

        traverse(node)
        return imports

    def extract_exports(self, node: Any) -> List[CodeBlock]:
        """Extract export statements with nested elements as children."""
        exports = self._extract_top_level_exports(node)
        for export in exports:
            export.children = self._extract_nested_elements(node, export)
        return exports

    def _extract_top_level_exports(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level export declarations."""
        exports = []

        def traverse(n):
            if hasattr(n, "type"):
                if n.type in ["export_statement", "export_declaration"]:
                    start_line, end_line, start_col, end_col = self._get_node_position(
                        n
                    )
                    content = self._get_node_text(n)

                    # Try to extract what's being exported
                    export_name = self._extract_export_name(n)

                    exports.append(
                        self._create_code_block(
                            BlockType.EXPORT,
                            export_name
                            or "default_export",  # Use default_export if no name found
                            content,
                            start_line,
                            end_line,
                            start_col,
                            end_col,
                            n,
                        )
                    )
                    return  # Don't traverse deeper from this export

            if hasattr(n, "children"):
                for child in n.children:
                    traverse(child)

        traverse(node)
        return exports

    def _get_nested_variable_names(self, node: Any) -> List[str]:
        """Get variable names from a nested node."""
        names = []

        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type"):
                    if child.type == "identifier":
                        names.append(self._get_node_text(child))
                    elif child.type in ["variable_declarator", "property_signature"]:
                        name = self._get_nested_identifier_name(child)
                        if name:
                            names.append(name)

        return names

    def _extract_nested_exports(self, parent_node: Any) -> List[CodeBlock]:
        """Extract export declarations nested within a parent node."""
        nested_exports = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                export_types = ["export_statement", "export_declaration"]

                if (
                    node.type in export_types and depth > 0
                ):  # Skip direct children, only nested
                    name = self._extract_export_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)

                        nested_exports.append(
                            self._create_code_block(
                                BlockType.EXPORT,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                node,
                            )
                        )
                        return  # Don't traverse deeper from this export

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_exports

    def _extract_import_name(self, import_node: Any) -> str:
        """Extract the primary name from an import statement."""
        if hasattr(import_node, "children"):
            for child in import_node.children:
                if hasattr(child, "type"):
                    if child.type == "import_clause":
                        # Look for default import or named imports
                        if hasattr(child, "children"):
                            for grandchild in child.children:
                                if hasattr(grandchild, "type"):
                                    if grandchild.type == "identifier":
                                        return self._get_node_text(grandchild)
                                    elif grandchild.type == "named_imports":
                                        # Get first named import
                                        names = self._extract_named_imports(grandchild)
                                        return names[0] if names else "unknown"
                    elif child.type == "string":
                        # Import without names, use module path
                        return self._get_node_text(child).strip("\"'")

        return "unknown"

    def _extract_named_imports(self, named_imports_node: Any) -> List[str]:
        """Extract names from named imports."""
        names = []
        if hasattr(named_imports_node, "children"):
            for child in named_imports_node.children:
                if hasattr(child, "type") and child.type == "import_specifier":
                    if hasattr(child, "children"):
                        for grandchild in child.children:
                            if (
                                hasattr(grandchild, "type")
                                and grandchild.type == "identifier"
                            ):
                                names.append(self._get_node_text(grandchild))
                                break
        return names

    def _extract_export_name(self, export_node: Any) -> str:
        """Extract the primary name from an export statement."""
        if hasattr(export_node, "children"):
            for child in export_node.children:
                if hasattr(child, "type"):
                    if child.type in [
                        "function_declaration",
                        "class_declaration",
                        "interface_declaration",
                    ]:
                        return self._get_identifier_name(child)
                    elif child.type == "variable_declaration":
                        names = self._extract_variable_names(child)
                        return names[0] if names else "unknown"
                    elif child.type == "export_clause":
                        names = self._extract_export_names(child)
                        return names[0] if names else "unknown"

        return "default"

    def _extract_export_names(self, export_clause: Any) -> List[str]:
        """Extract names from export clause."""
        names = []
        if hasattr(export_clause, "children"):
            for child in export_clause.children:
                if hasattr(child, "type") and child.type == "export_specifier":
                    if hasattr(child, "children"):
                        for grandchild in child.children:
                            if (
                                hasattr(grandchild, "type")
                                and grandchild.type == "identifier"
                            ):
                                names.append(self._get_node_text(grandchild))
                                break
        return names

    def _is_function_assignment(self, declarator_node: Any) -> bool:
        """Check if a variable declarator is a function assignment."""
        if hasattr(declarator_node, "children"):
            for child in declarator_node.children:
                if hasattr(child, "type") and child.type in [
                    "function_expression",
                    "arrow_function",
                    "async_function_expression",
                ]:
                    return True
        return False

    def _extract_variable_names(self, var_node: Any) -> List[str]:
        """Extract variable names from variable declaration."""
        names = []
        if hasattr(var_node, "children"):
            for child in var_node.children:
                if hasattr(child, "type") and child.type == "variable_declarator":
                    name = self._get_identifier_name(child)
                    if name:
                        names.append(name)
                    else:
                        # Handle destructuring
                        names.extend(self._extract_destructuring_names(child))
        return names

    def _extract_destructuring_names(self, declarator_node: Any) -> List[str]:
        """Extract names from destructuring patterns."""
        names = []
        if hasattr(declarator_node, "children"):
            for child in declarator_node.children:
                if hasattr(child, "type"):
                    if child.type == "object_pattern":
                        names.extend(self._extract_object_pattern_names(child))
                    elif child.type == "array_pattern":
                        names.extend(self._extract_array_pattern_names(child))
        return names

    def _extract_object_pattern_names(self, pattern_node: Any) -> List[str]:
        """Extract names from object destructuring pattern."""
        names = []
        if hasattr(pattern_node, "children"):
            for child in pattern_node.children:
                if hasattr(child, "type") and child.type == "pair_pattern":
                    if hasattr(child, "children"):
                        for grandchild in child.children:
                            if (
                                hasattr(grandchild, "type")
                                and grandchild.type == "identifier"
                            ):
                                names.append(self._get_node_text(grandchild))
        return names

    def _extract_array_pattern_names(self, pattern_node: Any) -> List[str]:
        """Extract names from array destructuring pattern."""
        names = []
        if hasattr(pattern_node, "children"):
            for child in pattern_node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    names.append(self._get_node_text(child))
        return names

    def _get_method_name(self, method_node: Any) -> str:
        """Get the name of a method node."""
        if hasattr(method_node, "children"):
            for child in method_node.children:
                if hasattr(child, "type") and child.type == "property_identifier":
                    return self._get_node_text(child)
        return ""

    def extract_enums(self, node: Any) -> List[CodeBlock]:
        """Extract top-level enum declarations with nested elements as children."""
        enums = self._extract_top_level_enums(node)
        for enum in enums:
            enum.children = self._extract_nested_elements(node, enum)
        return enums

    def _extract_top_level_enums(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level enum declarations from TypeScript module."""
        blocks = []

        # Look for direct children of the module that are enum declarations
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "enum_declaration":
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(child)
                        )
                        content = self._get_node_text(child)
                        blocks.append(
                            self._create_code_block(
                                BlockType.ENUM,
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

    def extract_variables(self, node: Any) -> List[CodeBlock]:
        """Extract top-level variable declarations with nested elements as children."""
        variables = self._extract_top_level_variables(node)
        for variable in variables:
            variable.children = self._extract_nested_elements(node, variable)
        return variables

    def extract_all(self, root_node: Any) -> List[CodeBlock]:
        """TypeScript-specific implementation of extract_all.
        Extracts all supported code blocks with hierarchical structure.
        """
        self._blocks = []

        # First, extract all symbols from the entire file
        self._extract_all_symbols(root_node)

        # Then extract top-level blocks with their nested children
        # TypeScript-specific order and handling
        self._blocks.extend(self.extract_imports(root_node))
        self._blocks.extend(self.extract_exports(root_node))
        self._blocks.extend(
            self.extract_interfaces(root_node)
        )  # TypeScript has interfaces
        self._blocks.extend(self.extract_enums(root_node))  # TypeScript has enums
        self._blocks.extend(self.extract_variables(root_node))
        self._blocks.extend(self.extract_functions(root_node))
        self._blocks.extend(self.extract_classes(root_node))

        return self._blocks

    def _extract_top_level_variables(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level variable declarations from TypeScript module."""
        blocks = []

        # Look for direct children of the module that are variable declarations
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type in [
                    "variable_declaration",
                    "lexical_declaration",
                ]:
                    # Extract variables but skip function assignments (they'll be handled as functions)
                    if hasattr(child, "children"):
                        for grandchild in child.children:
                            if (
                                hasattr(grandchild, "type")
                                and grandchild.type == "variable_declarator"
                            ):
                                # Skip if this is a function assignment
                                if not self._is_function_assignment(grandchild):
                                    name = self._get_identifier_name(grandchild)
                                    if name:
                                        start_line, end_line, start_col, end_col = (
                                            self._get_node_position(child)
                                        )
                                        content = self._get_node_text(child)
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

        return blocks

    def extract_functions(self, node: Any) -> List[CodeBlock]:
        """Extract top-level function declarations with nested elements as children."""
        functions = self._extract_top_level_functions(node)
        for function in functions:
            function.children = self._extract_nested_elements(node, function)
        return functions

    def _extract_top_level_functions(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level function declarations from TypeScript module."""
        blocks = []

        # Look for direct children of the module that are function declarations
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type"):
                    if child.type == "function_declaration":
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
                    elif child.type in ["variable_declaration", "lexical_declaration"]:
                        # Check for function expressions assigned to variables
                        if hasattr(child, "children"):
                            for grandchild in child.children:
                                if (
                                    hasattr(grandchild, "type")
                                    and grandchild.type == "variable_declarator"
                                ):
                                    name = self._get_identifier_name(grandchild)
                                    if name and self._is_function_assignment(
                                        grandchild
                                    ):
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

    def _get_nested_identifier_name(self, node: Any) -> str:
        """Get identifier name from a nested TypeScript node."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type in [
                    "identifier",
                    "type_identifier",
                    "property_identifier",
                ]:
                    return self._get_node_text(child)
        return ""

    def _extract_nested_functions(self, parent_node: Any) -> List[CodeBlock]:
        """Extract function/method declarations nested within a TypeScript parent node."""
        nested_functions = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                # TypeScript function/method node types
                function_types = [
                    "method_definition",
                    "function_declaration",
                    "function_expression",
                    "arrow_function",
                ]

                if (
                    node.type in function_types and depth > 0
                ):  # Skip direct children, only nested
                    name = self._get_nested_identifier_name(node)
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

    def _extract_nested_variables(self, parent_node: Any) -> List[CodeBlock]:
        """Extract variable/property declarations nested within a TypeScript parent node."""
        nested_variables = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                # TypeScript variable/property node types
                variable_types = [
                    "public_field_definition",
                    "property_signature",
                    "variable_declarator",
                ]

                if (
                    node.type in variable_types and depth > 0
                ):  # Skip direct children, only nested
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)

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

    def _extract_nested_classes(self, parent_node: Any) -> List[CodeBlock]:
        """Extract class declarations nested within a TypeScript parent node."""
        nested_classes = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                if (
                    node.type == "class_declaration" and depth > 0
                ):  # Skip direct children, only nested
                    name = self._get_nested_identifier_name(node)
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
                        return  # Don't traverse deeper from this class

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_classes

    def _extract_nested_interfaces(self, parent_node: Any) -> List[CodeBlock]:
        """Extract interface declarations nested within a TypeScript parent node."""
        nested_interfaces = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                if (
                    node.type == "interface_declaration" and depth > 0
                ):  # Skip direct children, only nested
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)

                        nested_interfaces.append(
                            self._create_code_block(
                                BlockType.INTERFACE,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                node,
                            )
                        )
                        return  # Don't traverse deeper from this interface

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_interfaces

    def _extract_nested_enums(self, parent_node: Any) -> List[CodeBlock]:
        """Extract enum declarations nested within a TypeScript parent node."""
        nested_enums = []

        def traverse(node, depth=0):
            if hasattr(node, "type"):
                if (
                    node.type == "enum_declaration" and depth > 0
                ):  # Skip direct children, only nested
                    name = self._get_nested_identifier_name(node)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(node)
                        )
                        content = self._get_node_text(node)

                        nested_enums.append(
                            self._create_code_block(
                                BlockType.ENUM,
                                name,
                                content,
                                start_line,
                                end_line,
                                start_col,
                                end_col,
                                node,
                            )
                        )
                        return  # Don't traverse deeper from this enum

            if hasattr(node, "children"):
                for child in node.children:
                    traverse(child, depth + 1)

        if hasattr(parent_node, "children"):
            for child in parent_node.children:
                traverse(child, 0)

        return nested_enums

    def extract_classes(self, node: Any) -> List[CodeBlock]:
        """Extract top-level class declarations with nested elements as children."""
        classes = self._extract_top_level_classes(node)
        for class_block in classes:
            class_block.children = self._extract_nested_elements(node, class_block)
        return classes

    def _extract_top_level_classes(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level class declarations from TypeScript module."""
        blocks = []

        # Look for direct children of the module that are class declarations
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "class_declaration":
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

    def extract_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract top-level interface declarations with nested elements as children."""
        interfaces = self._extract_top_level_interfaces(node)
        for interface in interfaces:
            interface.children = self._extract_nested_elements(node, interface)
        return interfaces

    def _extract_top_level_interfaces(self, node: Any) -> List[CodeBlock]:
        """Extract only top-level interface declarations from TypeScript module."""
        blocks = []

        # Look for direct children of the module that are interface declarations
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "interface_declaration":
                    name = self._get_identifier_name(child)
                    if name:
                        start_line, end_line, start_col, end_col = (
                            self._get_node_position(child)
                        )
                        content = self._get_node_text(child)
                        blocks.append(
                            self._create_code_block(
                                BlockType.INTERFACE,
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

"""Python Extractor for Code Block Extraction

This module provides Python-specific extraction capabilities for identifying
and extracting code blocks from Python AST nodes using tree-sitter.
"""

from typing import Any, Callable, Dict, List, Optional, Set

from tree_sitter_language_pack import SupportedLanguage

from . import BaseExtractor, BlockType, CodeBlock


class PythonExtractor(BaseExtractor):
    """Python-specific extractor for code blocks."""

    # Define node types once as class constants
    FUNCTION_TYPES = {"function_definition"}
    CLASS_TYPES = {"class_definition"}
    # Variable detection patterns:
    # - "assignment": Direct assignment nodes (rare at top level)
    # - "expression_statement": Wrapper for top-level assignments like x = 5
    VARIABLE_TYPES = {"assignment", "expression_statement"}

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
        """
        Extract all identifier names from a node, handling various Python patterns.

        Detects these patterns:
        - Simple identifiers: myVar → ['myVar']
        - Tuple patterns: (a, b, c) → ['a', 'b', 'c']
        - List patterns: [first, second, third] → ['first', 'second', 'third']
        - Assignments: x = 5 → ['x']
        - Star expressions: *args, **kwargs → ['args', 'kwargs']
        - Nested patterns: (a, (b, c)) → ['a', 'b', 'c']
        - Class/function names: class User, def process → ['User'], ['process']

        Used as a generic fallback for complex nested structures.
        """
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
        """
        Extract names from assignment statements.

        Handles these Python assignment patterns:
        - Simple: x = 5 → ['x']
        - Multiple: a, b, c = 1, 2, 3 → ['a', 'b', 'c']
        - Chained: x = y = z = "value" → ['x', 'y', 'z']
        - Tuple unpacking: first, *rest = items → ['first', 'rest']
        - Type annotations: var: int = 42 → ['var']
        - Walrus operator: (var := expr) → ['var'] (handled separately)
        """
        names = []
        if node.type == "assignment":
            names.extend(self._extract_assignment_variables(node))
        elif node.type == "expression_statement":
            # Look for assignment nodes within expression statements
            for child in node.children:
                if child.type == "assignment":
                    names.extend(self._extract_assignment_variables(child))

        # Recursively look for named_expression (walrus operator) anywhere in the subtree
        names.extend(self._find_named_expressions(node))
        return names

    def _extract_assignment_variables(self, assignment_node: Any) -> List[str]:
        """
        Extract all variables from an assignment node, handling chained assignments.

        Handles these patterns:
        - Simple assignment: x = 5 → ['x']
        - Chained assignment: x = y = z = "value" → ['x', 'y', 'z']
        - Multiple assignment: a, b, c = 1, 2, 3 → ['a', 'b', 'c']
        - Mixed patterns: (x, y) = z = (1, 2) → ['x', 'y', 'z']

        The method recursively processes nested assignments to handle chaining.
        """
        names = []

        # Get the left side (the variable being assigned to)
        left_node = assignment_node.child_by_field_name("left")
        if left_node:
            if left_node.type == "identifier":
                names.append(self._get_node_text(left_node))
            elif left_node.type in ["pattern_list", "tuple_pattern", "list_pattern"]:
                names.extend(self._extract_pattern_names(left_node))

        # Check if the right side is another assignment (chained assignment)
        right_node = assignment_node.child_by_field_name("right")
        if right_node and right_node.type == "assignment":
            # Recursively extract variables from the chained assignment
            names.extend(self._extract_assignment_variables(right_node))

        return names

    def _find_named_expressions(self, node: Any) -> List[str]:
        """Find all named expressions (walrus operator) in a node subtree."""
        names = []

        def traverse(n):
            if n.type == "named_expression":
                # Get the variable name from the named expression
                target_node = n.child_by_field_name("name")
                if target_node and target_node.type == "identifier":
                    names.append(self._get_node_text(target_node))

            # Recursively check all children
            for child in getattr(n, "children", []) or []:
                traverse(child)

        traverse(node)
        return names

    def _find_all_walrus_operators(self, root_node: Any) -> List[CodeBlock]:
        """
        Find all walrus operators (named_expression) throughout the entire tree.

        Detects walrus operator patterns anywhere in the code:
        - In if statements: if (n := len(items)) > 0: → ['n']
        - In while loops: while (line := file.readline()): → ['line']
        - In comprehensions: [y for x in items if (y := process(x))] → ['y']
        - In expressions: result = func(x) if (x := get_value()) else None → ['x']

        This traverses the entire AST tree since walrus operators can appear anywhere.
        """
        blocks = []

        def traverse(node):
            if node.type == "named_expression":
                # Get the variable name from the named expression
                target_node = node.child_by_field_name("name")
                if target_node and target_node.type == "identifier":
                    name = self._get_node_text(target_node)
                    block = self._create_code_block(node, BlockType.VARIABLE, [name])
                    blocks.append(block)

            # Recursively check all children
            for child in getattr(node, "children", []) or []:
                traverse(child)

        traverse(root_node)
        return blocks

    def _extract_pattern_names(self, node: Any) -> List[str]:
        """
        Extract names from pattern nodes (tuple, list patterns).

        Detects these unpacking patterns:
        - Tuple patterns: (a, b, c) = (1, 2, 3) → ['a', 'b', 'c']
        - List patterns: [first, second, third] = items → ['first', 'second', 'third']
        - Nested patterns: (a, (b, c)) = (1, (2, 3)) → ['a', 'b', 'c']
        - Star patterns: (head, *tail) = items → ['head', 'tail']
        - Mixed patterns: [a, (b, c), d] = data → ['a', 'b', 'c', 'd']

        Recursively handles nested tuple/list structures.
        """
        names = []
        for child in node.children:
            if child.type == "identifier":
                names.append(self._get_node_text(child))
            elif child.type in ["tuple_pattern", "list_pattern"]:
                names.extend(self._extract_pattern_names(child))
        return names

    def _extract_import_name(self, node: Any) -> str:
        """
        Extract module name from import statement.

        Detects these import patterns:
        - Simple imports: import os → 'os'
        - Dotted imports: import os.path → 'os.path'
        - From imports: from typing import List → 'typing'
        - Relative imports: from .utils import helper → '.utils'
        - Package imports: from mypackage.submodule import func → 'mypackage.submodule'
        - Aliased imports: import numpy as np → 'numpy'

        Returns the module name being imported from.
        """
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
        """
        Extract import statements from Python code.

        Detects these import patterns:
        - Simple imports: import os, sys → ['os'], ['sys']
        - From imports: from typing import List, Dict → ['typing'] + ['List', 'Dict']
        - Aliased imports: import numpy as np → ['numpy'] + ['np']
        - Relative imports: from .utils import helper → ['.utils'] + ['helper']
        - Dynamic imports: importlib.import_module('module') → ['module']
        - Star imports: from module import * → ['module']
        - Multiple imports: import os, sys, json → ['os'], ['sys'], ['json']

        Creates separate blocks for the module and imported symbols.
        """

        def process_import(node):
            # Don't extract names for imports - just create the block
            return self._create_code_block(node, BlockType.IMPORT, [])

        import_types = {"import_statement", "import_from_statement"}
        blocks = self._generic_traversal(root_node, import_types, process_import)

        # Add dynamic imports
        blocks.extend(self._find_dynamic_imports(root_node))
        return blocks

    def extract_exports(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract export statements (Python __all__ declarations).

        Detects these export patterns:
        - __all__ lists: __all__ = ['func1', 'Class2', 'CONSTANT'] → ['__all__']
        - __all__ tuples: __all__ = ('func1', 'Class2') → ['__all__']
        - Dynamic __all__: __all__ += ['new_export'] → ['__all__']
        - Module exports: __all__ = dir() → ['__all__']

        Python doesn't have explicit exports like JS/TS, so this focuses on __all__.
        """
        return self._extract_top_level_exports(root_node)

    def extract_functions(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract function definitions with nested function extraction for large functions.

        Detects these function patterns:
        - Function definitions: def calculate_total(items): → ['calculate_total']
        - Async functions: async def fetch_data(): → ['fetch_data']
        - Generator functions: def generate_numbers(): yield x → ['generate_numbers']
        - Lambda functions: lambda x: x * 2 → ['<lambda>'] (if assigned)
        - Decorated functions: @property def name(self): → ['name']
        - Class methods: def method(self): → ['method']
        - Static methods: @staticmethod def utility(): → ['utility']

        For functions over 300 lines, nested functions are extracted separately.
        """

        def process_function(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            # Use the new nested function extraction logic
            return self._create_function_block_with_nested_extraction(
                node, BlockType.FUNCTION, names, self.FUNCTION_TYPES
            )

        return self._generic_traversal(root_node, self.FUNCTION_TYPES, process_function)

    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract class definitions with 300-line check for methods.

        Detects these class patterns:
        - Basic classes: class User: → ['User']
        - Inherited classes: class AdminUser(User): → ['AdminUser']
        - Multiple inheritance: class Child(Parent1, Parent2): → ['Child']
        - Generic classes: class Container(Generic[T]): → ['Container']
        - Abstract classes: class ABC(metaclass=ABCMeta): → ['ABC']
        - Dataclasses: @dataclass class Point: → ['Point']

        Also extracts class members:
        - Class variables: class_var = "value" → ['class_var'] (as variables)
        - Methods: def method(self): → ['method'] (as functions)
        - Properties: @property def name(self): → ['name'] (as functions)

        Methods over 300 lines have nested functions extracted separately.
        """

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
        """
        Extract variable assignments from Python code.

        Detects these top-level variable patterns:
        - Module variables: x = 5, name = "John"
        - Multiple assignments: a, b, c = 1, 2, 3
        - Chained assignments: x = y = z = "value"
        - Type annotations: var: int = 42, name: str
        - Annotation-only: var: int (without assignment)
        - Walrus operators: if (n := len(items)) > 0:

        Creates separate blocks for each variable, so 'a, b, c = 1, 2, 3'
        generates 3 separate variable blocks.
        """
        blocks = []

        def process_variable(node):
            """
            Process a single assignment node and create blocks for each variable.

            Examples of what this processes:
            - expression_statement containing: x = 5
            - expression_statement containing: a, b, c = 1, 2, 3
            - expression_statement containing: x = y = z = "same"

            Each variable gets its own block for better granularity.
            """
            names = self._extract_assignment_names(node)
            variable_blocks = []
            # Create separate blocks for each variable name
            # Example: 'a, b, c = 1, 2, 3' creates 3 blocks
            for name in names:
                block = self._create_code_block(node, BlockType.VARIABLE, [name])
                variable_blocks.append(block)
            return variable_blocks

        # Only look at direct children of root_node
        for child in root_node.children:
            if child.type in self.VARIABLE_TYPES:
                variable_blocks = process_variable(child)
                if variable_blocks:
                    blocks.extend(variable_blocks)

        # Also find all walrus operators throughout the tree
        # These can appear in if statements, loops, comprehensions, etc.
        # Example: if (n := len(items)) > 0: creates a variable block for 'n'
        walrus_blocks = self._find_all_walrus_operators(root_node)
        blocks.extend(walrus_blocks)

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
        """
        Find dynamic import calls like importlib.import_module().

        Detects these dynamic import patterns:
        - importlib.import_module('module_name') → ['module_name']
        - __import__('module_name') → ['module_name']
        - importlib.__import__('module_name') → ['module_name']
        - getattr(__import__('module'), 'attr') → ['module']

        These are runtime imports that can't be statically analyzed completely,
        but we extract the module names from string literals where possible.
        """
        blocks = []

        def traverse(node):
            if self._is_dynamic_import_call(node):
                import_name = self._extract_dynamic_import_name(node)
                if import_name:
                    block = self._create_code_block(node, BlockType.IMPORT, [])
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
        """
        Extract __all__ declarations from module level.

        Detects these __all__ patterns:
        - List format: __all__ = ['function1', 'Class2', 'CONSTANT'] → ['__all__']
        - Tuple format: __all__ = ('function1', 'Class2') → ['__all__']
        - Concatenation: __all__ = base_exports + ['new_item'] → ['__all__']
        - Modification: __all__.append('dynamic_export') → ['__all__']

        Only detects the __all__ variable itself, not the contents,
        since the contents are strings, not actual variable references.
        """
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
        """
        Extract imported symbols from import_from_statement.

        Detects these import symbol patterns:
        - Named imports: from module import func1, Class2 → ['func1', 'Class2']
        - Aliased imports: from module import func as f → ['f']
        - Mixed imports: from module import func, Class as C → ['func', 'C']
        - Star imports: from module import * → [] (can't determine symbols)
        - Parenthesized: from module import (func1, func2) → ['func1', 'func2']

        Returns the local names that will be available in the importing module.
        """
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
        """
        Extract enums (Python enum.Enum classes).

        Detects these enum patterns:
        - Basic enums: class Status(Enum): PENDING = 'pending' → ['Status']
        - Int enums: class Priority(IntEnum): LOW = 1 → ['Priority']
        - Auto enums: class Color(Enum): RED = auto() → ['Color']
        - Flag enums: class Permission(Flag): READ = 1 → ['Permission']
        - Functional API: Status = Enum('Status', 'PENDING APPROVED') → ['Status']

        Note: Enum members are NOT extracted as variables (correctly excluded).
        Only the enum class itself is detected as a type definition.
        """

        def process_enum(node):
            # Check if this class inherits from Enum
            superclasses = node.child_by_field_name("superclasses")
            if superclasses:
                superclass_text = self._get_node_text(superclasses)
                if "Enum" in superclass_text:
                    name_node = node.child_by_field_name("name")
                    names = [self._get_node_text(name_node)] if name_node else []

                    # Don't extract nested blocks for enums (enum members are not variables)
                    return self._create_code_block(node, BlockType.ENUM, names)
            return None

        return self._generic_traversal(root_node, {"class_definition"}, process_enum)

    def _extract_class_level_variables(self, class_node: Any) -> List[CodeBlock]:
        """
        Extract only class-level variables, not variables inside methods.

        Detects these class-level variable patterns:
        - Class variables: class MyClass: count = 0 → ['count']
        - Type annotations: name: str → ['name']
        - Constants: MAX_SIZE = 1000 → ['MAX_SIZE']
        - Descriptors: username = Property() → ['username']
        - Slots: __slots__ = ['x', 'y'] → ['__slots__']

        Excludes these (correctly):
        - Method local variables: def method(self): x = 1 (not detected)
        - Instance variables in __init__: self.x = 1 (not detected as class vars)
        - Variables in nested functions (not detected)

        Only processes direct assignments within the class body.
        """
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

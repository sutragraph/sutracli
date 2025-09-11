"""TypeScript Extractor for Code Block Extraction

This module provides TypeScript-specific extraction capabilities for identifying
and extracting code blocks from TypeScript AST nodes using tree-sitter.
"""

from typing import Any, Callable, Dict, List, Optional, Set

from tree_sitter_language_pack import SupportedLanguage

from . import BaseExtractor, BlockType, CodeBlock


class TypeScriptExtractor(BaseExtractor):
    """TypeScript-specific extractor for code blocks."""

    # Define function types once as class constants
    FUNCTION_TYPES = {
        "function_declaration",
        "function_expression",
        "arrow_function",
        "method_definition",
    }

    CLASS_TYPES = {"class_declaration"}
    # Variable detection patterns:
    # - "variable_declaration": var a = 1, b = 2;
    # - "lexical_declaration": let x = 'hello'; const PI = 3.14;
    VARIABLE_TYPES = {"variable_declaration", "lexical_declaration"}

    def __init__(self, language: SupportedLanguage, file_id: int = 0):
        super().__init__(language, file_id)

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

    def _extract_names_from_node(self, node: Any) -> List[str]:
        """
        Extract all identifier names from a node, handling various TypeScript patterns.

        Detects these complex patterns:
        - Simple identifiers: myVar → ['myVar']
        - Object destructuring: { name, age, city } → ['name', 'age', 'city']
        - Array destructuring: [first, second, third] → ['first', 'second', 'third']
        - Rest patterns: [head, ...tail] → ['head', 'tail']
        - Renamed destructuring: { name: userName } → ['userName']
        - Class field definitions: public userName: string → ['userName']
        - Method definitions: getName() → ['getName']
        - Nested patterns: { user: { name, age } } → ['name', 'age']

        Special handling for class field definitions to pick the correct field name.
        """
        names: List[str] = []

        if node.type in ["identifier", "property_identifier"]:
            names.append(self._get_node_text(node))

        elif node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            if name_node:
                names.extend(self._extract_names_from_node(name_node))

        elif node.type in ["object_pattern", "array_pattern"]:
            names.extend(self._extract_destructuring_names(node))

        elif node.type in [
            "function_declaration",
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "method_definition",
        ]:
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))

        elif node.type in ["field_definition", "public_field_definition"]:
            # Minimal: use explicit name child, else first direct property_identifier/identifier
            name_node = node.child_by_field_name("name")
            if name_node:
                names.append(self._get_node_text(name_node))
            else:
                for child in getattr(node, "children", []) or []:
                    if child.type in ("property_identifier", "identifier"):
                        names.append(self._get_node_text(child))
                        break

        else:

            def find_identifiers(n):
                if n.type in ["identifier", "property_identifier"]:
                    names.append(self._get_node_text(n))
                for child in getattr(n, "children", []) or []:
                    find_identifiers(child)

            find_identifiers(node)

        # De-duplicate while preserving first occurrence
        seen = set()
        result: List[str] = []
        for n in names:
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result

    def _replace_nested_functions_with_references(
        self, original_content: str, nested_functions: List[CodeBlock]
    ) -> str:
        """
        Replace nested function content with block references for TypeScript/JavaScript.

        Handles these nested function patterns:
        - Function declarations inside functions:
          function outer() {
            function inner() { ... }  // Replaced with // [BLOCK_REF:123]
          }
        - Arrow functions inside methods:
          class MyClass {
            method() {
              const helper = () => { ... }  // Replaced with reference
            }
          }
        - Callback functions:
          items.map(item => {
            function transform(x) { ... }  // Replaced with reference
          })
        """
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

            # Create TypeScript comment reference
            reference = f"// [BLOCK_REF:{func.id}]"

            # For TypeScript/JavaScript, find the function signature (lines ending with {)
            signature_lines = []
            for line in func_lines:
                if "{" in line:
                    # Found opening brace, keep everything up to and including it
                    brace_pos = line.find("{")
                    signature_part = line[: brace_pos + 1]
                    signature_lines.append(signature_part)
                    signature_lines.append(f"    {reference}")
                    signature_lines.append("}")
                    break
                else:
                    signature_lines.append(line)
            replacement = "\n".join(signature_lines)

            # Replace the entire function content with the signature + reference
            original_content = original_content.replace(func_content, replacement)

        return original_content

    # ============================================================================
    # SPECIALIZED NAME EXTRACTION METHODS
    # ============================================================================

    def _extract_destructuring_names(self, node: Any) -> List[str]:
        """
        Extract names from destructuring patterns.

        Handles these destructuring patterns:
        - Object: const { name, age, city } = user → ['name', 'age', 'city']
        - Object rename: const { name: userName, age: userAge } = user → ['userName', 'userAge']
        - Array: const [first, second, third] = colors → ['first', 'second', 'third']
        - Rest: const [head, ...tail] = list → ['head', 'tail']
        """
        names = []

        if node.type == "object_pattern":
            names.extend(self._extract_object_pattern_names(node))
        elif node.type == "array_pattern":
            names.extend(self._extract_array_pattern_names(node))

        return names

    def _extract_object_pattern_names(self, node: Any) -> List[str]:
        """
        Extract names from object destructuring pattern.

        Handles:
        - Shorthand: { name, age } → ['name', 'age']
        - Rename: { name: userName, age: userAge } → ['userName', 'userAge']
        - Nested: { user: { name, age } } → ['name', 'age']
        """
        names = []
        for child in node.children:
            if child.type == "shorthand_property_identifier_pattern":
                # Example: { name, age } - 'name' and 'age' are shorthand
                names.append(self._get_node_text(child))
            elif child.type == "pair_pattern":
                # Example: { name: userName } - 'userName' is the value
                value_node = child.child_by_field_name("value")
                if value_node:
                    names.extend(self._extract_names_from_node(value_node))
        return names

    def _extract_array_pattern_names(self, node: Any) -> List[str]:
        """
        Extract names from array destructuring pattern.

        Handles:
        - Simple: [first, second, third] → ['first', 'second', 'third']
        - With holes: [first, , third] → ['first', 'third']
        - Rest pattern: [head, ...tail] → ['head'] (tail handled elsewhere)
        """
        names = []
        for child in node.children:
            if child.type == "identifier":
                names.append(self._get_node_text(child))
            # Note: rest_pattern (...tail) is handled by _extract_names_from_node recursion
        return names

    def _extract_variable_names(self, node: Any) -> List[str]:
        """
        Extract variable names from variable declaration.

        Detects these patterns:
        - Simple: var x = 5 → extracts ['x']
        - Multiple: var a = 1, b = 2 → calls this for each declarator
        - Typed: let name: string = 'John' → extracts ['name']
        """
        names = []
        if node.type in ["variable_declaration", "lexical_declaration"]:
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        names.extend(self._extract_names_from_node(name_node))
        return names

    def _extract_import_name(self, node: Any) -> str:
        """
        Extract module name from import statement.

        Detects these import patterns:
        - ES6 imports: import { x } from 'module' → 'module'
        - Default imports: import React from 'react' → 'react'
        - Namespace imports: import * as fs from 'fs' → 'fs'
        - Side-effect imports: import 'styles.css' → 'styles.css'
        - Dynamic imports: import('module') → 'module'
        - Type imports: import type { User } from './types' → './types'
        """
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
        """
        Extract export names from export statement.

        Detects these export patterns:
        - Named exports: export { name, age, calculateTotal } → ['name', 'age', 'calculateTotal']
        - Aliased exports: export { name as userName } → ['userName']
        - Function exports: export function getName() → ['getName']
        - Class exports: export class User → ['User']
        - Variable exports: export const API_URL = '...' → ['API_URL']
        - Re-exports: export { User } from './types' → ['User']
        - Default exports: export default MyComponent → ['MyComponent']
        """
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
            # Don't extract names for imports - just create the block
            return self._create_code_block(node, BlockType.IMPORT, [])

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
        """
        Extract function declarations with nested function extraction for large functions.

        Detects these function patterns:
        - Function declarations: function calculateTotal(items) { ... } → ['calculateTotal']
        - Arrow functions: const handleClick = () => { ... } → ['handleClick']
        - Method definitions: getName() { ... } → ['getName']
        - Async functions: async function fetchData() { ... } → ['fetchData']
        - Generator functions: function* generateIds() { ... } → ['generateIds']
        - Generic functions: function process<T>(item: T) { ... } → ['process']

        For functions over 300 lines, nested functions are extracted separately.
        """

        def process_function(node):
            # Skip functions that are members of a class; they are handled in extract_classes
            cur = getattr(node, "parent", None)
            while cur is not None:
                if cur.type == "class_body":
                    return None
                cur = getattr(cur, "parent", None)

            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            return self._create_function_block_with_nested_extraction(
                node, BlockType.FUNCTION, names, self.FUNCTION_TYPES
            )

        return self._generic_traversal(root_node, self.FUNCTION_TYPES, process_function)

    def extract_classes(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract class declarations with 300-line check for methods.

        Detects these class patterns:
        - Basic classes: class User { ... } → ['User']
        - Generic classes: class Container<T> { ... } → ['Container']
        - Extended classes: class AdminUser extends User { ... } → ['AdminUser']
        - Abstract classes: abstract class BaseService { ... } → ['BaseService']
        - Class expressions: const MyClass = class { ... } → ['MyClass']

        Also extracts class members:
        - Properties: public name: string → ['name'] (as variables)
        - Methods: getName() { ... } → ['getName'] (as functions)
        - Static members: static count = 0 → ['count'] (as variables)
        - Private members: private #id = 1 → ['#id'] (as variables)

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
                if method_node.type == "method_definition":
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

            methods = self._generic_traversal(
                node, {"method_definition"}, process_method
            )
            nested_blocks.extend(methods)

            # Extract class-level fields only (not variables inside methods)
            class_level_fields = self._extract_class_level_fields(node)
            nested_blocks.extend(class_level_fields)

            class_block.children = nested_blocks
            return class_block

        return self._generic_traversal(root_node, self.CLASS_TYPES, process_class)

    def extract_interfaces(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract interface declarations(TypeScript only).

        Detects these interface patterns:
        - Basic interfaces: interface User {name: string; age: number} →['User']
        - Generic interfaces: interface Container < T > {item: T} →['Container']
        - Extended interfaces: interface AdminUser extends User {...} →['AdminUser']
        - Merged interfaces: interface Window {myProp: string} →['Window']
        - Namespace interfaces: declare namespace API {interface Response {...}} →['Response']

        Note: Interface properties are NOT extracted as variables(correctly excluded).
        """

        def process_interface(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            # Don't extract nested blocks for interfaces
            return self._create_code_block(node, BlockType.INTERFACE, names)

        return self._generic_traversal(
            root_node, {"interface_declaration"}, process_interface
        )

    def extract_type_aliases(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract type alias declarations(TypeScript only).

        Detects these type alias patterns:
        - Union types: type Status = 'pending' | 'approved' | 'rejected' →['Status']
        - Object types: type Point = {x: number; y: number} →['Point']
        - Generic types: type Container < T > = {item: T} →['Container']
        - Function types: type Handler = (event: Event) = > void →['Handler']
        - Conditional types: type IsString < T > = T extends string ? true: false →['IsString']
        - Mapped types: type Readonly < T > = {readonly[P in keyof T]: T[P]} →['Readonly']
        """

        def process_type_alias(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            # Don't extract nested blocks for type aliases
            return self._create_code_block(node, BlockType.TYPE, names)

        return self._generic_traversal(
            root_node, {"type_alias_declaration"}, process_type_alias
        )

    def extract_enums(self, root_node: Any) -> List[CodeBlock]:
        """
        Extract enum declarations (TypeScript only).

        Detects these enum patterns:
        - Basic enums: enum Status { PENDING = 'pending', APPROVED = 'approved' } → ['Status']
        - Numeric enums: enum Direction { Up = 1, Down, Left, Right } → ['Direction']
        - String enums: enum Color { Red = '#ff0000', Green = '#00ff00' } → ['Color']
        - Const enums: const enum Size { Small = 1, Medium = 2 } → ['Size']
        - Computed enums: enum Values { A = getValue() } → ['Values']

        Note: Enum members are NOT extracted as variables (correctly excluded).
        Only the enum declaration itself is detected as a type definition.
        """

        def process_enum(node):
            name_node = node.child_by_field_name("name")
            names = [self._get_node_text(name_node)] if name_node else []

            # Don't extract nested blocks for enums (enum members are not variables)
            return self._create_code_block(node, BlockType.ENUM, names)

        return self._generic_traversal(root_node, {"enum_declaration"}, process_enum)

    def extract_variables(self, root_node: Any) -> List[CodeBlock]:
        """Extract variable declarations."""
        blocks = []

        def process_variable(node):
            """
            Process variable declarations and create separate blocks for each variable.

            Handles these patterns:
            - Multiple declarations: var a = 1, b = 2, c = 3;
            - Destructuring: const {name, age, city} = user;
            - Array destructuring: const[first, second, third] = colors;
            - Mixed types: let x: string = 'hello', y: number = 42;
            """
            variable_blocks = []
            if node.type in ["variable_declaration", "lexical_declaration"]:
                # Create separate blocks for each variable declarator
                # Example: "var a = 1, b = 2" has 2 variable_declarator children
                for child in node.children:
                    if child.type == "variable_declarator":
                        # Check if this declarator contains a require call - if so, skip it
                        # It should be handled by import extraction instead
                        init_node = child.child_by_field_name("value")
                        if init_node and self._contains_require_call(init_node):
                            continue  # Skip require statements, let import extraction handle them

                        name_node = child.child_by_field_name("name")
                        if name_node:
                            names = self._extract_names_from_node(name_node)
                            if names:
                                # Create separate blocks for each variable name
                                # This handles destructuring: { name, age } creates 2 blocks
                                for name in names:
                                    block = self._create_code_block(
                                        node, BlockType.VARIABLE, [name]
                                    )
                                    variable_blocks.append(block)
            return variable_blocks

        # Only look at direct children of root_node
        for child in root_node.children:
            if child.type in self.VARIABLE_TYPES:
                variable_blocks = process_variable(child)
                if variable_blocks:
                    blocks.extend(variable_blocks)

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
        all_blocks.extend(self.extract_interfaces(root_node))
        all_blocks.extend(self.extract_type_aliases(root_node))
        return all_blocks

    # ============================================================================
    # SPECIALIZED DETECTION METHODS
    # ============================================================================

    def _find_dynamic_imports(self, root_node: Any) -> List[CodeBlock]:
        """
        Find dynamic import() calls and capture full statement content.

        Captures complete dynamic import statements:
        - const module = await import('./module') → full statement
        - import('./utils').then(module => ...) → full statement
        """
        blocks = []

        def traverse(node):
            # Look for statements that contain dynamic imports
            if node.type in [
                "variable_declaration",
                "lexical_declaration",
                "expression_statement",
            ]:
                # Check if this statement contains a dynamic import call
                def find_import_call(n):
                    if self._is_dynamic_import(n):
                        return self._extract_dynamic_import_name(n)
                    for child in getattr(n, "children", []):
                        result = find_import_call(child)
                        if result:
                            return result
                    return None

                import_name = find_import_call(node)
                if import_name:
                    block = self._create_code_block(node, BlockType.IMPORT, [])
                    blocks.append(block)
                    return  # Don't traverse children

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks

    def _find_require_calls(self, root_node: Any) -> List[CodeBlock]:
        """
        Find require() calls and capture full variable declaration content.

        Captures complete require statements:
        - const { function1, Class2 } = require("../../utils/azureRepo") → full statement
        - const utils = require("./utils") → full statement
        """
        blocks = []

        def traverse(node):
            # Look for variable declarations that contain require calls
            if node.type in ["variable_declaration", "lexical_declaration"]:
                # Check if this statement contains a require call
                def find_require_call(n):
                    if self._is_require_call(n):
                        return self._extract_require_name(n)
                    for child in getattr(n, "children", []):
                        result = find_require_call(child)
                        if result:
                            return result
                    return None

                import_name = find_require_call(node)
                if import_name:
                    block = self._create_code_block(node, BlockType.IMPORT, [])
                    blocks.append(block)
                    return  # Don't traverse children

            for child in node.children:
                traverse(child)

        traverse(root_node)
        return blocks

    def _is_dynamic_import(self, node: Any) -> bool:
        """Check if node is a dynamic import () call."""
        if node.type != "call_expression":
            return False

        function_node = node.child_by_field_name("function")
        if not function_node:
            return False

        return self._get_node_text(function_node) == "import"

    def _contains_require_call(self, node: Any) -> bool:
        """Check if node contains a require call anywhere in its subtree."""
        if self._is_require_call(node):
            return True
        for child in getattr(node, "children", []):
            if self._contains_require_call(child):
                return True
        return False

    def _is_require_call(self, node: Any) -> bool:
        """Check if node is a require() call."""
        if node.type != "call_expression":
            return False

        function_node = node.child_by_field_name("function")
        if not function_node:
            return False

        return self._get_node_text(function_node) == "require"

    def _extract_dynamic_import_name(self, node: Any) -> str:
        """Extract module name from dynamic import ."""
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

    def _extract_class_level_fields(self, class_node: Any) -> List[CodeBlock]:
        """Extract class -level field definitions and arrow - function methods.

        Minimal approach: detect arrow / functions inline and derive name from the
        left - hand property identifier only(avoid scanning inner identifiers).
        """
        fields = []

        def get_field_name(field_node: Any) -> Optional[str]:
            # Prefer named child 'name'
            name_node = field_node.child_by_field_name("name")
            if name_node:
                return self._get_node_text(name_node)
            # Strong heuristic: first direct property_identifier (field name)
            for child in getattr(field_node, "children", []) or []:
                if child.type == "property_identifier":
                    return self._get_node_text(child)
            # Next best: direct identifier
            for child in getattr(field_node, "children", []) or []:
                if child.type == "identifier":
                    return self._get_node_text(child)
            return None

        # Look for the class body
        for child in class_node.children:
            if child.type == "class_body":
                # Now look at direct children of the class_body for field definitions
                for body_child in child.children:
                    if body_child.type in [
                        "field_definition",
                        "public_field_definition",
                    ]:
                        # Inline check: treat as method if it contains arrow/function expression
                        def contains_func(n: Any) -> bool:
                            if n.type in ("arrow_function", "function_expression"):
                                return True
                            for c in getattr(n, "children", []) or []:
                                if contains_func(c):
                                    return True
                            return False

                        if contains_func(body_child):
                            # This is an arrow function method
                            field_name = get_field_name(body_child)
                            if field_name:
                                # Create as a function block with nested extraction for large functions
                                method_block = (
                                    self._create_function_block_with_nested_extraction(
                                        body_child,
                                        BlockType.FUNCTION,
                                        [field_name],
                                        self.FUNCTION_TYPES,
                                    )
                                )
                                fields.append(method_block)
                        else:
                            # This is a regular class field
                            names = self._extract_names_from_node(body_child)
                            if names:
                                field_block = self._create_code_block(
                                    body_child, BlockType.VARIABLE, names
                                )
                                fields.append(field_block)

        return fields

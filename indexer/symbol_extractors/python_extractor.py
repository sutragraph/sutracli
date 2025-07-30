"""
Simplified Python Symbol Extractor

Extracts symbols from Python AST nodes with minimal boilerplate.
"""

from typing import Any, List, Set
from . import BaseExtractor, Symbol, SymbolType


class PythonExtractor(BaseExtractor):
    """Simplified Python symbol extractor."""

    @property
    def language(self) -> str:
        """Return the language this extractor handles."""
        return "python"

    def _extract_definitions(self, ast_node: Any, symbols: List[Symbol]) -> None:
        """First pass: Extract only definitions and declarations."""
        self._extract_recursive(ast_node, symbols, extract_calls=False)

    def _extract_calls(
        self, ast_node: Any, symbols: List[Symbol], defined_names: Set[str]
    ) -> None:
        """Second pass: Extract function/method calls for defined symbols only."""
        self._extract_recursive(
            ast_node, symbols, extract_calls=True, defined_names=defined_names
        )

    def _get_keywords(self) -> Set[str]:
        """Python keywords, built-ins and common standard library names to filter out."""
        # Python keywords
        keywords = {
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "break",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield",
            "async",
            "await",
            "self",
        }

        # Built-in functions and types
        builtins = {
            "abs",
            "aiter",
            "all",
            "anext",
            "any",
            "ascii",
            "bin",
            "bool",
            "breakpoint",
            "bytearray",
            "bytes",
            "callable",
            "chr",
            "classmethod",
            "compile",
            "complex",
            "delattr",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "eval",
            "exec",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "globals",
            "hasattr",
            "hash",
            "help",
            "hex",
            "id",
            "input",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "locals",
            "map",
            "max",
            "memoryview",
            "min",
            "next",
            "object",
            "oct",
            "open",
            "ord",
            "pow",
            "print",
            "property",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "setattr",
            "slice",
            "sorted",
            "staticmethod",
            "str",
            "sum",
            "super",
            "tuple",
            "type",
            "vars",
            "zip",
        }

        # Built-in exceptions
        exceptions = {
            "ArithmeticError",
            "AssertionError",
            "AttributeError",
            "BaseException",
            "BlockingIOError",
            "BrokenPipeError",
            "BufferError",
            "BytesWarning",
            "ChildProcessError",
            "ConnectionAbortedError",
            "ConnectionError",
            "ConnectionRefusedError",
            "ConnectionResetError",
            "DeprecationWarning",
            "EOFError",
            "EnvironmentError",
            "Exception",
            "FileExistsError",
            "FileNotFoundError",
            "FloatingPointError",
            "GeneratorExit",
            "IOError",
            "ImportError",
            "ImportWarning",
            "IndentationError",
            "IndexError",
            "InterruptedError",
            "IsADirectoryError",
            "KeyError",
            "KeyboardInterrupt",
            "LookupError",
            "MemoryError",
            "ModuleNotFoundError",
            "NameError",
            "NotADirectoryError",
            "NotImplementedError",
            "OSError",
            "OverflowError",
            "PermissionError",
            "ProcessLookupError",
            "RecursionError",
            "ReferenceError",
            "RuntimeError",
            "StopAsyncIteration",
            "StopIteration",
            "SyntaxError",
            "SystemError",
            "SystemExit",
            "TabError",
            "TimeoutError",
            "TypeError",
            "UnboundLocalError",
            "UnicodeDecodeError",
            "UnicodeEncodeError",
            "UnicodeError",
            "UnicodeTranslateError",
            "UnicodeWarning",
            "UserWarning",
            "ValueError",
            "Warning",
            "ZeroDivisionError",
        }

        # Common standard library module attributes and types
        stdlib = {
            # os module
            "path",
            "environ",
            "getcwd",
            "chdir",
            "mkdir",
            "makedirs",
            "remove",
            "removedirs",
            "rename",
            "renames",
            "replace",
            "rmdir",
            "unlink",
            # sys module
            "argv",
            "exit",
            "modules",
            "path",
            "platform",
            "stderr",
            "stdin",
            "stdout",
            "version",
            "version_info",
            # datetime
            "date",
            "datetime",
            "time",
            "timedelta",
            "timezone",
            "tzinfo",
            # collections
            "defaultdict",
            "deque",
            "namedtuple",
            "Counter",
            "OrderedDict",
            # typing
            "Any",
            "Callable",
            "Dict",
            "List",
            "Optional",
            "Set",
            "Tuple",
            "Union",
            "TypeVar",
            "Generic",
            "Protocol",
            "Final",
            "Literal",
            "ClassVar",
            # contextlib
            "contextmanager",
            "asynccontextmanager",
            "suppress",
            "closing",
            # functools
            "partial",
            "partialmethod",
            "reduce",
            "lru_cache",
            "singledispatch",
            # itertools
            "chain",
            "combinations",
            "combinations_with_replacement",
            "compress",
            "count",
            "cycle",
            "dropwhile",
            "filterfalse",
            "groupby",
            "islice",
            "permutations",
            "product",
            "repeat",
            "starmap",
            "takewhile",
            "tee",
            # asyncio
            "create_task",
            "gather",
            "get_event_loop",
            "run",
            "sleep",
            "wait",
            "wait_for",
            "AbstractEventLoop",
            "Future",
            "Task",
            # json
            "loads",
            "dumps",
            "load",
            "dump",
            "JSONEncoder",
            "JSONDecoder",
            # re
            "match",
            "fullmatch",
            "search",
            "sub",
            "subn",
            "split",
            "findall",
            "finditer",
            "compile",
            "Pattern",
            "Match",
        }

        return keywords | builtins | exceptions | stdlib

    def _extract_recursive(
        self,
        node: Any,
        symbols: List[Symbol],
        extract_calls: bool = False,
        defined_names: Set[str] = None,
    ):
        """Recursively extract symbols."""
        if not hasattr(node, "type"):
            return

        node_type = node.type

        if extract_calls and defined_names is not None:
            # Second pass: Extract calls to defined symbols
            if node_type == "call":
                name = self._extract_call_name(node)
                if name and name in defined_names and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.FUNCTION))

            elif node_type == "attribute":
                name = self._extract_attribute_name(node)
                if name and name in defined_names and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.METHOD))
        else:
            # First pass: Extract definitions only
            if node_type in ["function_definition", "async_function_definition"]:
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.FUNCTION))

            elif node_type == "class_definition":
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(self._create_symbol(node, name, SymbolType.CLASS))

            elif node_type == "assignment":
                names = self._extract_assignment_names(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbol_type = (
                            SymbolType.CONSTANT
                            if name.isupper()
                            else SymbolType.VARIABLE
                        )
                        symbols.append(self._create_symbol(node, name, symbol_type))

            elif node_type in ["import_statement", "import_from_statement"]:
                names = self._extract_import_names(node)
                for name in names:
                    if self._is_valid_symbol(name):
                        symbols.append(
                            self._create_symbol(node, name, SymbolType.ALIAS)
                        )

            elif node_type == "parameter":
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(
                        self._create_symbol(node, name, SymbolType.PARAMETER)
                    )

            elif node_type == "decorator":
                name = self._find_identifier(node)
                if name and self._is_valid_symbol(name):
                    symbols.append(
                        self._create_symbol(node, name, SymbolType.DECORATOR)
                    )

        # Recurse into children
        if hasattr(node, "children"):
            for child in node.children:
                self._extract_recursive(child, symbols, extract_calls, defined_names)

    def _extract_assignment_names(self, node: Any) -> List[str]:
        """Extract variable names from assignment."""
        names = []
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type"):
                    if child.type == "identifier":
                        names.append(self._get_text(child))
                    elif child.type in ["pattern_list", "tuple_pattern"]:
                        names.extend(self._extract_pattern_names(child))
        return [name for name in names if name]

    def _extract_pattern_names(self, node: Any) -> List[str]:
        """Extract names from tuple/list patterns."""
        names = []
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    name = self._get_text(child)
                    if name:
                        names.append(name)
        return names

    def _extract_import_names(self, node: Any) -> List[str]:
        """Extract imported names and aliases."""
        names = []
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type"):
                    if child.type in ["dotted_name", "identifier"]:
                        text = self._get_text(child)
                        if text:
                            # For dotted names, take the last part
                            names.append(text.split(".")[-1])
                    elif child.type == "aliased_import":
                        # Find the alias (after 'as')
                        alias = self._find_alias(child)
                        if alias:
                            names.append(alias)
        return names

    def _find_alias(self, node: Any) -> str:
        """Find alias name after 'as' keyword."""
        if hasattr(node, "children"):
            found_as = False
            for child in node.children:
                if hasattr(child, "text") and child.text == b"as":
                    found_as = True
                elif found_as and hasattr(child, "type") and child.type == "identifier":
                    return self._get_text(child)
        return ""

    def _find_identifier(self, node: Any) -> str:
        """Find the first identifier in a node."""
        if not hasattr(node, "children"):
            return ""

        for child in node.children:
            if hasattr(child, "type") and child.type == "identifier":
                return self._get_text(child)
            # Recursively search in child nodes
            name = self._find_identifier(child)
            if name:
                return name
        return ""

    def _get_text(self, node: Any) -> str:
        """Get text content from a node."""
        if hasattr(node, "text") and node.text:
            try:
                return node.text.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                return ""
        return ""

    def _extract_call_name(self, node: Any) -> str:
        """Extract function name from a call node."""
        if hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "type") and child.type == "identifier":
                    return self._get_text(child)
                elif hasattr(child, "type") and child.type == "attribute":
                    # For method calls like obj.method(), check if the object is built-in
                    obj_name = self._get_attribute_object_name(child)

                    # If the object is a built-in, skip this call
                    if obj_name in self.keywords:
                        return ""

                    # Otherwise return the method name
                    return self._extract_attribute_name(child)
        return ""

    def _extract_attribute_name(self, node: Any) -> str:
        """Extract method name from attribute access."""
        if hasattr(node, "children"):
            # Look for the last identifier (method name)
            for child in reversed(node.children):
                if hasattr(child, "type") and child.type == "identifier":
                    return self._get_text(child)
        return ""

    def _get_attribute_object_name(self, node: Any) -> str:
        """Extract the object name from an attribute access."""
        if not hasattr(node, "children") or len(node.children) < 2:
            return ""

        # The first child is typically the object being accessed
        first_child = node.children[0]

        if hasattr(first_child, "type"):
            if first_child.type == "identifier":
                return self._get_text(first_child)
            elif first_child.type == "attribute":
                # For nested attribute access like a.b.c, return the immediate object (b)
                for child in first_child.children:
                    if hasattr(child, "type") and child.type == "identifier":
                        # Return the last identifier in the chain
                        return self._get_text(child)

        return ""

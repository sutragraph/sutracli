#!/usr/bin/env python3
"""Debug script to examine AST structure for class variables."""

import tempfile
from pathlib import Path
from ast_parser import ASTParser


def create_simple_class():
    """Create a simple class with class variables."""
    test_dir = tempfile.mkdtemp(prefix="ast_debug_")

    simple_class = """
class TestClass:
    CLASS_VAR = "hello"
    ANOTHER_VAR = 42
    
    def __init__(self):
        self.instance_var = "world"
"""

    file_path = Path(test_dir) / "simple.py"
    with open(file_path, "w") as f:
        f.write(simple_class)

    return test_dir, file_path


def debug_ast_structure():
    """Debug the AST structure to understand class variable placement."""
    test_dir, file_path = create_simple_class()

    try:
        # Parse the file
        parser = ASTParser()

        # Get the language and tree
        from tree_sitter_language_pack import get_language
        import tree_sitter

        language = get_language("python")
        ts_parser = tree_sitter.Parser()
        ts_parser.set_language(language)

        with open(file_path, "rb") as f:
            source_code = f.read()

        tree = ts_parser.parse(source_code)
        root_node = tree.root_node

        def print_ast_structure(node, depth=0):
            """Recursively print AST structure."""
            indent = "  " * depth
            node_text = node.text.decode("utf-8")[:50].replace("\n", "\\n")
            print(
                f"{indent}{node.type}: '{node_text}...' (lines {node.start_point[0]+1}-{node.end_point[0]+1})"
            )

            for child in node.children:
                print_ast_structure(child, depth + 1)

        print("AST Structure:")
        print("=" * 60)
        print_ast_structure(root_node)

        # Now let's see what our extractor finds
        print("\n" + "=" * 60)
        print("EXTRACTOR RESULTS:")
        print("=" * 60)

        results = parser.extract_from_directory(test_dir)
        for file_path, result in results.items():
            blocks = result.get("blocks", [])
            print(f"\nTotal blocks: {len(blocks)}")

            for i, block in enumerate(blocks):
                print(
                    f"Block {i+1}: {block.type.value} '{block.name}' (lines {block.start_line}-{block.end_line})"
                )
                if block.children:
                    for j, child in enumerate(block.children):
                        print(
                            f"  Child {j+1}: {child.type.value} '{child.name}' (lines {child.start_line}-{child.end_line})"
                        )

    finally:
        import shutil

        shutil.rmtree(test_dir)


if __name__ == "__main__":
    debug_ast_structure()

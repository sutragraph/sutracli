#!/usr/bin/env python3
"""Simple debug script to understand class variable extraction."""

import tempfile
from pathlib import Path
from ast_parser import ASTParser


def main():
    """Debug class variable extraction."""
    test_dir = tempfile.mkdtemp(prefix="simple_debug_")

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

    try:
        parser = ASTParser()
        results = parser.extract_from_directory(test_dir)

        print("SIMPLE CLASS EXTRACTION RESULTS:")
        print("=" * 50)

        for file_path, result in results.items():
            blocks = result.get("blocks", [])
            print(f"\nFile: {Path(file_path).name}")
            print(f"Total blocks: {len(blocks)}")

            for i, block in enumerate(blocks):
                print(
                    f"\nBlock {i+1}: {block.type.value} '{block.name}' (lines {block.start_line}-{block.end_line})"
                )
                print(f"  Content: '{block.content.strip()}'")
                if block.children:
                    print(f"  Children: {len(block.children)}")
                    for j, child in enumerate(block.children):
                        print(
                            f"    Child {j+1}: {child.type.value} '{child.name}' (lines {child.start_line}-{child.end_line})"
                        )
                        print(f"      Content: '{child.content.strip()}'")
                else:
                    print(f"  Children: 0")

    finally:
        import shutil

        shutil.rmtree(test_dir)


if __name__ == "__main__":
    main()

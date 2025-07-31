#!/usr/bin/env python3
"""Debug script to examine class block content in detail."""

import tempfile
import os
import json
from pathlib import Path
from ast_parser import ASTParser


def create_simple_test_class():
    """Create a simple test class to debug the issue."""

    # Create a temporary directory for test files
    test_dir = tempfile.mkdtemp(prefix="debug_class_")

    # Simple Python class
    simple_py_class = (
        """
class SimpleClass:
    def __init__(self):
        self.value = 0
    
    def small_method(self):
        return self.value
    
    def large_method(self):
        # This method will be over 300 lines
        result = 0
        
        def nested_func1():
            return 1
        
        def nested_func2():
            return 2
        
"""
        + "\n".join([f"        # Line {i}" for i in range(1, 300)])
        + """
        
        return result + nested_func1() + nested_func2()
"""
    )

    # Write test file
    file_path = Path(test_dir) / "simple_class.py"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(simple_py_class)

    return test_dir


def main():
    """Debug class content extraction."""
    print("Creating simple test class...")
    test_dir = create_simple_test_class()

    try:
        print(f"Test directory: {test_dir}")

        print("\nRunning AST parser...")
        parser = ASTParser()
        results = parser.extract_from_directory(test_dir)

        # Detailed analysis
        print("\n" + "=" * 80)
        print("DETAILED BLOCK CONTENT ANALYSIS")
        print("=" * 80)

        for file_path, result in results.items():
            filename = Path(file_path).name
            blocks = result.get("blocks", [])

            print(f"\n📁 {filename}")
            print(f"   Total blocks: {len(blocks)}")

            for i, block in enumerate(blocks):
                print(f"\n   Block {i+1}: {block.type.value} - {block.name}")
                print(f"   ID: {block.id}")
                print(f"   Lines: {block.start_line}-{block.end_line}")
                print(f"   Content length: {len(block.content)} chars")
                print(f"   Children: {len(block.children)}")

                # Show first 200 chars of content
                if block.content:
                    content_preview = block.content[:200].replace("\n", "\\n")
                    print(f"   Content preview: {content_preview}...")
                else:
                    print(f"   Content: EMPTY")

                # Show children details
                if block.children:
                    print(f"   Children details:")
                    for j, child in enumerate(block.children):
                        child_content_len = len(child.content)
                        print(
                            f"     {j+1}. {child.type.value} '{child.name}' - {child_content_len} chars"
                        )

                        # If child has a lot of content, show preview
                        if child_content_len > 100:
                            child_preview = child.content[:100].replace("\n", "\\n")
                            print(f"        Content preview: {child_preview}...")

        # Export detailed results to JSON for inspection
        output_file = "debug_class_results.json"

        # Convert blocks to serializable format
        serializable_results = {}
        for file_path, result in results.items():
            serializable_blocks = []
            for block in result["blocks"]:
                block_data = {
                    "id": block.id,
                    "type": block.type.value,
                    "name": block.name,
                    "start_line": block.start_line,
                    "end_line": block.end_line,
                    "content_length": len(block.content),
                    "content_preview": block.content[:500] if block.content else "",
                    "children_count": len(block.children),
                    "children": [],
                }

                for child in block.children:
                    child_data = {
                        "id": child.id,
                        "type": child.type.value,
                        "name": child.name,
                        "start_line": child.start_line,
                        "end_line": child.end_line,
                        "content_length": len(child.content),
                        "content_preview": child.content[:200] if child.content else "",
                    }
                    block_data["children"].append(child_data)

                serializable_blocks.append(block_data)

            serializable_results[file_path] = {
                "language": result["language"],
                "blocks": serializable_blocks,
            }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, indent=2)

        print(f"\n📄 Detailed results exported to: {output_file}")

    finally:
        # Clean up test directory
        import shutil

        shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    main()

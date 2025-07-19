#!/usr/bin/env python3
"""
Quick test script to demonstrate hierarchical parsing functionality.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def print_tree(blocks, indent=0):
    """Print blocks in a tree structure."""
    for i, block in enumerate(blocks):
        indent_str = "  " * indent
        connector = "├─" if i < len(blocks) - 1 else "└─"
        child_count = len(block.children) if hasattr(block, 'children') and block.children else 0
        child_info = f" ({child_count} children)" if child_count > 0 else ""

        print(f"{indent_str}{connector} {block.type.value}: {block.name}{child_info}")

        if hasattr(block, 'children') and block.children:
            print_tree(block.children, indent + 1)

def count_all_blocks(blocks):
    """Count total blocks including nested ones."""
    total = len(blocks)
    for block in blocks:
        if hasattr(block, 'children') and block.children:
            total += count_all_blocks(block.children)
    return total

def test_file(file_path):
    """Test hierarchical parsing on a file."""
    try:
        from ast_parser import ASTParser

        parser = ASTParser()

        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return

        result = parser.parse_and_extract(file_path)



        if result.get("error"):
            print(f"❌ Error: {result['error']}")
            return


        blocks = result["blocks"]
        language = result.get("language", "unknown")
        total_blocks = count_all_blocks(blocks)

        print(f"\n🔍 {language.upper()} FILE: {file_path}")
        print(f"📊 Top-level blocks: {len(blocks)}")
        print(f"📊 Total blocks: {total_blocks}")
        print(f"📊 Nested blocks: {total_blocks - len(blocks)}")

        print(f"\n🌳 Structure:")
        if blocks:
            # Show only first few blocks to keep output manageable
            display_blocks = blocks
            print_tree(display_blocks)

        else:
            print("  No blocks found")



    except ImportError:
        print(f"❌ Parser not available - install requirements")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main test function."""
    print("🚀 QUICK HIERARCHICAL PARSING TEST")
    print("=" * 50)

    test_files = [
        # "test_files/test_python.py",
        "test_files/test_typescript.ts"
    ]

    for file_path in test_files:
        test_file(file_path)

    print(f"\n" + "=" * 50)
    print("✅ Test completed!")


if __name__ == "__main__":
    main()

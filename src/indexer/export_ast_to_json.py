#!/usr/bin/env python3
"""
AST Extraction to JSON Export Script

This script extracts AST data from a directory and exports it to a JSON file.
It demonstrates how to use the ASTParser's JSON export functionality.

Usage:
    python export_ast_to_json.py <directory_path> [output_file] [--indent N]

Examples:
    python export_ast_to_json.py ./test_files
    python export_ast_to_json.py ./test_files results.json
    python export_ast_to_json.py ./test_files results.json --indent 4
"""

import argparse
import sys
from pathlib import Path

from indexer.ast_parser import ASTParser


def main():
    """Main function to handle command line arguments and run extraction."""
    parser = argparse.ArgumentParser(
        description="Extract AST data from a directory and export to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./test_files
  %(prog)s ./test_files results.json
  %(prog)s ./test_files results.json --indent 4
        """,
    )

    parser.add_argument("directory", help="Directory path to extract AST data from")

    parser.add_argument(
        "output_file",
        nargs="?",
        default="ast_extraction_results.json",
        help="Output JSON file path (default: ast_extraction_results.json)",
    )

    parser.add_argument(
        "--indent", type=int, default=2, help="JSON indentation level (default: 2)"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Validate directory path
    dir_path = Path(args.directory)
    if not dir_path.exists():
        print(f"Error: Directory '{dir_path}' does not exist")
        sys.exit(1)

    if not dir_path.is_dir():
        print(f"Error: '{dir_path}' is not a directory")
        sys.exit(1)

    ast_parser = ASTParser()

    if args.verbose:
        print(f"Starting AST extraction from: {dir_path}")
        print(f"Output file: {args.output_file}")
        print(f"JSON indent: {args.indent}")
        print("-" * 50)

    try:
        # Extract and export in one step
        success = ast_parser.extract_and_export_directory(
            dir_path, args.output_file, args.indent
        )

        if success:
            print(f"\n✅ Successfully exported AST extraction results!")
            print(f"📁 Source directory: {dir_path}")
            print(f"📄 Output file: {args.output_file}")

            # Show file size
            output_path = Path(args.output_file)
            if output_path.exists():
                file_size = output_path.stat().st_size
                if file_size < 1024:
                    size_str = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                print(f"📊 File size: {size_str}")
        else:
            print("\n❌ Failed to export AST extraction results")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


def demo_usage():
    """Demonstrate usage with the test files directory."""
    print("🚀 Demo: Extracting from test_files directory")
    print("-" * 50)

    ast_parser = ASTParser()

    # Check if test_files directory exists
    test_dir = Path("test_files")
    if not test_dir.exists():
        print("❌ test_files directory not found")
        print("Creating a simple demo...")

        # Create a simple demo file
        demo_dir = Path("demo_extraction")
        demo_dir.mkdir(exist_ok=True)

        demo_file = demo_dir / "sample.py"
        demo_file.write_text(
            '''
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")

class Calculator:
    """A simple calculator class."""

    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        return a * b

if __name__ == "__main__":
    hello_world()
    calc = Calculator()
    print(calc.add(2, 3))
'''
        )

        print(f"📁 Created demo directory: {demo_dir}")
        print(f"📄 Created demo file: {demo_file}")
        test_dir = demo_dir

    # Extract and export
    output_file = "demo_results.json"
    success = ast_parser.extract_and_export_directory(test_dir, output_file)

    if success:
        print(f"\n✅ Demo completed! Check {output_file}")
    else:
        print("\n❌ Demo failed")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, show help and run demo
        print(__doc__)
        print("\n" + "=" * 60)
        demo_usage()
    else:
        main()

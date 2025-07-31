#!/usr/bin/env python3
"""
Comprehensive test script for symbol extraction integration.

This script tests the integration between the AST parser, code block extractor,
and symbol extractor. It processes test files and displays extracted code blocks
along with the symbols found within each block.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ast_parser import ASTParser
from symbol_extractors import Extractor as SymbolExtractor
from extractors import BlockType


def print_separator(title: str = "", char: str = "=", length: int = 80):
    """Print a formatted separator line."""
    if title:
        title_len = len(title)
        padding = (length - title_len - 2) // 2
        print(f"{char * padding} {title} {char * padding}")
    else:
        print(char * length)


def print_code_block(content: str, language: str = ""):
    """Print code content in a formatted block."""
    lines = content.strip().split('\n')
    max_line_num_width = len(str(len(lines)))

    print(f"```{language}")
    for i, line in enumerate(lines, 1):
        line_num = str(i).rjust(max_line_num_width)
        print(f"{line_num} | {line}")
    print("```")


def format_symbol_list(symbols: List[str]) -> str:
    """Format a list of symbols for display."""
    if not symbols:
        return "No symbols found"
    return ", ".join(f"`{symbol}`" for symbol in sorted(symbols))


def test_file_extraction(file_path: Path, parser: ASTParser):
    """Test symbol extraction for a single file."""
    print_separator(f"Testing: {file_path.name}")

    # Parse and extract from the file
    result = parser.parse_and_extract(file_path)

    if result.get("error"):
        print(f"❌ Error: {result['error']}")
        return

    if not result.get("ast"):
        print("❌ Failed to parse file")
        return

    language = result.get("language", "unknown")
    blocks = result.get("blocks", [])

    print(f"📄 Language: {language}")
    print(f"📊 Total blocks extracted: {len(blocks)}")
    print()

    if not blocks:
        print("⚠️  No code blocks found")
        return

    # Group blocks by type
    blocks_by_type = {}
    for block in blocks:
        block_type = block.type.value
        if block_type not in blocks_by_type:
            blocks_by_type[block_type] = []
        blocks_by_type[block_type].append(block)

    # Display blocks grouped by type
    for block_type, type_blocks in blocks_by_type.items():
        print_separator(f"{block_type.upper()} BLOCKS ({len(type_blocks)})", "-", 60)

        for i, block in enumerate(type_blocks, 1):
            print(f"\n🔸 {block_type.title()} #{i}: `{block.name}`")
            print(f"   📍 Location: Lines {block.start_line}-{block.end_line}")
            print(f"   🏷️  Symbols: {format_symbol_list(block.symbols)}")

            # Show code content
            print(f"   📝 Code:")
            # Indent the code block
            code_lines = block.content.strip().split('\n')
            for line in code_lines[:10]:  # Show first 10 lines
                print(f"      {line}")

            if len(code_lines) > 10:
                print(f"      ... ({len(code_lines) - 10} more lines)")

            # Show children if any
            if block.children:
                print(f"   👶 Children: {len(block.children)} nested blocks")
                for child in block.children:
                    print(f"      - {child.type.value}: `{child.name}` (symbols: {format_symbol_list(child.symbols)})")

        print()


def test_symbol_extraction_details(file_path: Path, parser: ASTParser):
    """Test detailed symbol extraction showing all symbols in the file."""
    print_separator(f"DETAILED SYMBOL ANALYSIS: {file_path.name}")

    # Parse the file
    result = parser.parse_and_extract(file_path)

    if result.get("error") or not result.get("ast"):
        print(f"❌ Failed to analyze {file_path.name}")
        return

    # Get the symbol extractor from the parser
    symbol_extractor = parser._extractor.symbol_extractor
    if not symbol_extractor:
        print("❌ No symbol extractor available")
        return

    # Extract symbols directly
    ast_tree = result["ast"]
    language = result["language"]
    content = ast_tree.root_node.text.decode('utf-8')

    try:
        symbols = symbol_extractor.extract_symbols(ast_tree.root_node, content, language)

        print(f"📄 File: {file_path.name}")
        print(f"🔤 Language: {language}")
        print(f"🎯 Total symbols found: {len(symbols)}")
        print()

        if not symbols:
            print("⚠️  No symbols extracted")
            return

        # Group symbols by type
        symbols_by_type = {}
        for symbol in symbols:
            symbol_type = symbol.symbol_type.value
            if symbol_type not in symbols_by_type:
                symbols_by_type[symbol_type] = []
            symbols_by_type[symbol_type].append(symbol)

        # Display symbols by type
        for symbol_type, type_symbols in symbols_by_type.items():
            print_separator(f"{symbol_type.upper()} SYMBOLS ({len(type_symbols)})", "-", 50)

            for symbol in sorted(type_symbols, key=lambda s: (s.start_line, s.start_col)):
                print(f"🔹 `{symbol.name}`")
                print(f"   📍 Location: Line {symbol.start_line}:{symbol.start_col} - {symbol.end_line}:{symbol.end_col}")

                # Show the relevant code line
                content_lines = content.split('\n')
                if 1 <= symbol.start_line <= len(content_lines):
                    code_line = content_lines[symbol.start_line - 1].strip()
                    if len(code_line) > 80:
                        code_line = code_line[:77] + "..."
                    print(f"   📝 Code: {code_line}")

            print()

    except Exception as e:
        print(f"❌ Error extracting symbols: {e}")


def compare_extraction_methods(file_path: Path, parser: ASTParser):
    """Compare symbols found via code blocks vs direct extraction."""
    print_separator(f"COMPARISON: {file_path.name}")

    result = parser.parse_and_extract(file_path)

    if result.get("error") or not result.get("ast"):
        print(f"❌ Failed to analyze {file_path.name}")
        return

    # Get symbols from code blocks
    blocks = result.get("blocks", [])
    block_symbols = set()
    for block in blocks:
        block_symbols.update(block.symbols)
        # Include nested block symbols
        for child in block.children:
            block_symbols.update(child.symbols)

    # Get symbols from direct extraction
    symbol_extractor = parser._extractor.symbol_extractor
    if symbol_extractor:
        ast_tree = result["ast"]
        language = result["language"]
        content = ast_tree.root_node.text.decode('utf-8')

        try:
            direct_symbols = symbol_extractor.extract_symbols(ast_tree.root_node, content, language)
            direct_symbol_names = {symbol.name for symbol in direct_symbols}
        except Exception:
            direct_symbol_names = set()
    else:
        direct_symbol_names = set()

    print(f"📄 File: {file_path.name}")
    print(f"🏗️  Symbols from code blocks: {len(block_symbols)}")
    print(f"🎯 Symbols from direct extraction: {len(direct_symbol_names)}")
    print()

    # Show symbols found in both
    common_symbols = block_symbols & direct_symbol_names
    print(f"✅ Common symbols ({len(common_symbols)}):")
    if common_symbols:
        print(f"   {format_symbol_list(list(common_symbols))}")
    else:
        print("   None")
    print()

    # Show symbols only in blocks
    block_only = block_symbols - direct_symbol_names
    print(f"🏗️  Only in code blocks ({len(block_only)}):")
    if block_only:
        print(f"   {format_symbol_list(list(block_only))}")
    else:
        print("   None")
    print()

    # Show symbols only in direct extraction
    direct_only = direct_symbol_names - block_symbols
    print(f"🎯 Only in direct extraction ({len(direct_only)}):")
    if direct_only:
        print(f"   {format_symbol_list(list(direct_only))}")
    else:
        print("   None")
    print()


def main():
    """Main test function."""
    print_separator("SYMBOL EXTRACTION INTEGRATION TEST")
    print("🧪 Testing integration between AST parser and symbol extractors")
    print()

    # Initialize the symbol extractor
    print("🔧 Initializing symbol extractor...")
    symbol_extractor = SymbolExtractor()

    # Initialize the AST parser with symbol extractor
    print("🔧 Initializing AST parser with symbol extractor...")
    parser = ASTParser(symbol_extractor=symbol_extractor)

    # Get test files
    test_dir = Path(__file__).parent / "test_files"
    test_files = [
        test_dir / "test_python.py",
        test_dir / "test_typescript.ts",
        test_dir / "test_java.java",

    ]

    print(f"📁 Test directory: {test_dir}")
    print(f"📄 Test files: {[f.name for f in test_files]}")
    print()

    # Check if test files exist
    missing_files = [f for f in test_files if not f.exists()]
    if missing_files:
        print(f"❌ Missing test files: {[f.name for f in missing_files]}")
        return

    print("✅ All test files found")
    print()

    # Test supported languages
    print("🌐 Supported languages:")
    extraction_languages = parser.get_supported_extraction_languages()
    symbol_languages = symbol_extractor.get_supported_languages()
    print(f"   📊 Code block extraction: {extraction_languages}")
    print(f"   🎯 Symbol extraction: {symbol_languages}")
    print()

    # Run tests for each file
    for test_file in test_files:
        if test_file.exists():
            print()

            # Test 1: Basic extraction
            test_file_extraction(test_file, parser)
            print()

            # Test 2: Detailed symbol analysis
            test_symbol_extraction_details(test_file, parser)
            print()

            # Test 3: Comparison
            compare_extraction_methods(test_file, parser)
            print()

    print_separator("TEST COMPLETE")
    print("🎉 Symbol extraction integration test completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

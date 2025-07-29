#!/usr/bin/env python3
"""Test script for nested function extraction feature."""

import tempfile
import os
from pathlib import Path
from ast_parser import ASTParser


def create_large_typescript_function():
    """Create a TypeScript function with more than 300 lines for testing."""
    lines = [
        "function largeFunction() {",
        "    // This is a large function with nested functions",
        "    const variable1 = 'test';",
        "    const variable2 = 42;",
        "",
        "    function nestedFunction1() {",
        "        const a = 5;",
        "        const c = a;",
        "        return c * a;",
        "    }",
        "",
        "    function nestedFunction2() {",
        "        const x = 10;",
        "        const y = 20;",
        "        return x + y;",
        "    }",
        "",
    ]

    # Add enough lines to make it over 300 lines
    for i in range(280):
        lines.append(f"    // Line {i + 17}")

    lines.extend(
        [
            "",
            "    function nestedFunction3() {",
            "        return 'nested function 3';",
            "    }",
            "",
            "    return {",
            "        func1: nestedFunction1,",
            "        func2: nestedFunction2,",
            "        func3: nestedFunction3",
            "    };",
            "}",
        ]
    )

    return "\n".join(lines)


def create_large_python_function():
    """Create a Python function with more than 300 lines for testing."""
    lines = [
        "def large_function():",
        '    """This is a large function with nested functions."""',
        "    variable1 = 'test'",
        "    variable2 = 42",
        "",
        "    def nested_function1():",
        "        a = 5",
        "        c = a",
        "        return c * a",
        "",
        "    def nested_function2():",
        "        x = 10",
        "        y = 20",
        "        return x + y",
        "",
    ]

    # Add enough lines to make it over 300 lines
    for i in range(280):
        lines.append(f"    # Line {i + 15}")

    lines.extend(
        [
            "",
            "    def nested_function3():",
            "        return 'nested function 3'",
            "",
            "    return {",
            "        'func1': nested_function1,",
            "        'func2': nested_function2,",
            "        'func3': nested_function3",
            "    }",
        ]
    )

    return "\n".join(lines)


def create_small_function():
    """Create a small function that should not trigger nested extraction."""
    return """
function smallFunction() {
    function nestedFunction() {
        return 'should not be extracted';
    }
    
    return nestedFunction();
}
"""


def test_nested_extraction():
    """Test the nested function extraction feature."""
    parser = ASTParser()

    # Test with large TypeScript function
    print("Testing large TypeScript function...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write(create_large_typescript_function())
        ts_file = f.name

    try:
        result = parser.parse_and_extract(ts_file)
        if result.get("blocks"):
            for block in result["blocks"]:
                if block.type.value == "function" and "largeFunction" in block.name:
                    print(f"Found large function: {block.name}")
                    print(f"Line count: {block.end_line - block.start_line + 1}")
                    print(f"Has children: {len(block.children)}")

                    if block.children:
                        print("Nested functions found:")
                        for child in block.children:
                            print(f"  - {child.name} (ID: {child.id})")

                        # Check if content has block references
                        if "[BLOCK_REF:" in block.content:
                            print("✓ Block references found in content")
                        else:
                            print("✗ No block references found in content")
                    break
        else:
            print("No blocks extracted")
    finally:
        os.unlink(ts_file)

    print("\n" + "=" * 50 + "\n")

    # Test with large Python function
    print("Testing large Python function...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(create_large_python_function())
        py_file = f.name

    try:
        result = parser.parse_and_extract(py_file)
        if result.get("blocks"):
            for block in result["blocks"]:
                if block.type.value == "function" and "large_function" in block.name:
                    print(f"Found large function: {block.name}")
                    print(f"Line count: {block.end_line - block.start_line + 1}")
                    print(f"Has children: {len(block.children)}")

                    if block.children:
                        print("Nested functions found:")
                        for child in block.children:
                            print(f"  - {child.name} (ID: {child.id})")

                        # Check if content has block references
                        if "[BLOCK_REF:" in block.content:
                            print("✓ Block references found in content")
                        else:
                            print("✗ No block references found in content")
                    break
        else:
            print("No blocks extracted")
    finally:
        os.unlink(py_file)

    print("\n" + "=" * 50 + "\n")

    # Test with small function (should not trigger nested extraction)
    print("Testing small TypeScript function...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write(create_small_function())
        small_file = f.name

    try:
        result = parser.parse_and_extract(small_file)
        if result.get("blocks"):
            for block in result["blocks"]:
                if block.type.value == "function" and "smallFunction" in block.name:
                    print(f"Found small function: {block.name}")
                    print(f"Line count: {block.end_line - block.start_line + 1}")
                    print(f"Has children: {len(block.children)}")

                    if len(block.children) == 0:
                        print("✓ No nested extraction for small function")
                    else:
                        print("✗ Unexpected nested extraction for small function")

                    # Check if content has block references
                    if "[BLOCK_REF:" not in block.content:
                        print("✓ No block references in small function")
                    else:
                        print("✗ Unexpected block references in small function")
                    break
        else:
            print("No blocks extracted")
    finally:
        os.unlink(small_file)


if __name__ == "__main__":
    test_nested_extraction()

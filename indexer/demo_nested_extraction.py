#!/usr/bin/env python3
"""Demonstration of the nested function extraction feature."""

import tempfile
import os
from ast_parser import ASTParser


def demo_typescript_extraction():
    """Demonstrate nested function extraction for TypeScript."""

    # Create a large TypeScript function with nested functions
    typescript_code = (
        """
function processData() {
    const data = [];
    let counter = 0;
    
    function validateInput(input) {
        if (!input) return false;
        if (typeof input !== 'string') return false;
        return input.length > 0;
    }
    
    function transformData(item) {
        return {
            id: counter++,
            value: item.toUpperCase(),
            timestamp: Date.now()
        };
    }
    
    // Add many lines to make it over 300 lines
"""
        + "\n".join([f"    // Processing step {i}" for i in range(1, 280)])
        + """
    
    function saveToDatabase(processedData) {
        console.log('Saving to database:', processedData);
        return true;
    }
    
    // Main processing logic
    return {
        validate: validateInput,
        transform: transformData,
        save: saveToDatabase
    };
}
"""
    )

    print("=== TypeScript Nested Function Extraction Demo ===")
    print(f"Original function has {len(typescript_code.split(chr(10)))} lines")

    parser = ASTParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write(typescript_code)
        ts_file = f.name

    try:
        result = parser.parse_and_extract(ts_file)

        for block in result.get("blocks", []):
            if block.type.value == "function" and "processData" in block.name:
                print(f"\nExtracted function: {block.name}")
                print(f"Line count: {block.end_line - block.start_line + 1}")
                print(f"Nested functions extracted: {len(block.children)}")

                if block.children:
                    print("\nNested functions:")
                    for child in block.children:
                        print(f"  - {child.name} (ID: {child.id})")

                print(f"\nModified content preview:")
                lines = block.content.split("\n")
                for i, line in enumerate(lines[:20]):  # Show first 20 lines
                    if "[BLOCK_REF:" in line:
                        print(f"  {i+1:3d}: {line} ← BLOCK REFERENCE")
                    else:
                        print(f"  {i+1:3d}: {line}")

                if len(lines) > 20:
                    print(f"  ... ({len(lines) - 20} more lines)")
                break

    finally:
        os.unlink(ts_file)


def demo_python_extraction():
    """Demonstrate nested function extraction for Python."""

    # Create a large Python function with nested functions
    python_code = (
        """
def analyze_dataset():
    '''Analyze a large dataset with multiple processing steps.'''
    results = {}
    processed_count = 0
    
    def clean_data(raw_data):
        '''Clean and validate input data.'''
        if not raw_data:
            return []
        return [item.strip().lower() for item in raw_data if item.strip()]
    
    def calculate_statistics(data):
        '''Calculate basic statistics for the dataset.'''
        if not data:
            return {'count': 0, 'mean': 0, 'median': 0}
        
        count = len(data)
        mean = sum(data) / count
        sorted_data = sorted(data)
        median = sorted_data[count // 2]
        
        return {
            'count': count,
            'mean': mean,
            'median': median
        }
    
"""
        + "\n".join([f"    # Analysis step {i}" for i in range(1, 280)])
        + """
    
    def generate_report(stats):
        '''Generate a comprehensive report.'''
        report = f'''
        Dataset Analysis Report
        ======================
        Total items: {stats['count']}
        Average value: {stats['mean']:.2f}
        Median value: {stats['median']:.2f}
        '''
        return report.strip()
    
    # Main analysis logic
    return {
        'clean': clean_data,
        'stats': calculate_statistics,
        'report': generate_report
    }
"""
    )

    print("\n=== Python Nested Function Extraction Demo ===")
    print(f"Original function has {len(python_code.split(chr(10)))} lines")

    parser = ASTParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(python_code)
        py_file = f.name

    try:
        result = parser.parse_and_extract(py_file)

        for block in result.get("blocks", []):
            if block.type.value == "function" and "analyze_dataset" in block.name:
                print(f"\nExtracted function: {block.name}")
                print(f"Line count: {block.end_line - block.start_line + 1}")
                print(f"Nested functions extracted: {len(block.children)}")

                if block.children:
                    print("\nNested functions:")
                    for child in block.children:
                        print(f"  - {child.name} (ID: {child.id})")

                print(f"\nModified content preview:")
                lines = block.content.split("\n")
                for i, line in enumerate(lines[:25]):  # Show first 25 lines
                    if "[BLOCK_REF:" in line:
                        print(f"  {i+1:3d}: {line} ← BLOCK REFERENCE")
                    else:
                        print(f"  {i+1:3d}: {line}")

                if len(lines) > 25:
                    print(f"  ... ({len(lines) - 25} more lines)")
                break

    finally:
        os.unlink(py_file)


if __name__ == "__main__":
    demo_typescript_extraction()
    demo_python_extraction()

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("✓ Functions > 300 lines automatically extract nested functions")
    print("✓ Nested functions are replaced with [BLOCK_REF:ID] references")
    print("✓ Original nested functions are stored as children of the main block")
    print("✓ Works for both TypeScript and Python with appropriate syntax")
    print("✓ Small functions (≤ 300 lines) are left unchanged")

#!/usr/bin/env python3
"""
Example usage of the new indexer functionality with incremental parsing.

This example demonstrates how to use the indexer without exposing the AST parser
and how to perform incremental parsing for efficient updates.
"""

from pathlib import Path
from src.indexer import (
    extract_from_directory,
    export_to_json,
    extract_and_export_directory,
    incremental_parse,
    compute_file_hash,
    load_previous_results
)

def example_basic_usage():
    """Example of basic directory extraction and export."""
    print("=== Basic Usage Example ===")
    
    # Extract from a directory
    results = extract_from_directory("src/indexer/utils")
    print(f"Extracted data from {len(results)} files")
    
    # Export to JSON
    success = export_to_json(results, "output/basic_extraction.json")
    print(f"Export successful: {success}")
    
    # Or do both in one step
    success = extract_and_export_directory(
        "src/indexer/utils", 
        "output/combined_extraction.json"
    )
    print(f"Combined extraction and export successful: {success}")


def example_incremental_usage():
    """Example of incremental parsing for efficient updates."""
    print("\n=== Incremental Parsing Example ===")
    
    # First, create initial extraction
    print("1. Creating initial extraction...")
    extract_and_export_directory("src/indexer/utils", "output/initial.json")
    
    # Later, when some files might have changed
    print("2. Performing incremental update...")
    
    # List of files to check for changes
    files_to_check = [
        "src/indexer/utils/file_utils.py",
        "src/indexer/utils/json_serializer.py",
        "src/indexer/utils/__init__.py"
    ]
    
    # Files that were deleted (if any)
    deleted_files = []  # Example: ["src/indexer/utils/old_file.py"]
    
    # Perform incremental parsing
    updated_data = incremental_parse(
        file_paths=files_to_check,
        previous_json_file="output/initial.json",
        output_json_file="output/updated.json",
        deleted_paths=deleted_files
    )
    
    print(f"Incremental parsing returned data for {len(updated_data)} files")
    print("Files processed:")
    for file_path in updated_data.keys():
        print(f"  - {file_path}")


def example_utility_functions():
    """Example of using utility functions for custom workflows."""
    print("\n=== Utility Functions Example ===")

    # Example: Check if files have changed before processing
    files_to_check = [
        "src/indexer/__init__.py",
        "src/indexer/ast_parser.py"
    ]

    print("Checking file hashes...")
    for file_path in files_to_check:
        file_hash = compute_file_hash(file_path)
        if file_hash:
            print(f"  {file_path}: {file_hash[:16]}...")
        else:
            print(f"  {file_path}: Could not compute hash")

    # Example: Load and inspect previous results
    print("\nLoading previous results...")
    previous_data = load_previous_results("output/initial.json")
    print(f"Previous extraction contained {len(previous_data)} files")

    if previous_data:
        print("Sample file data keys:")
        sample_file = next(iter(previous_data.values()))
        print(f"  {list(sample_file.keys())}")


def example_workflow():
    """Example of a complete workflow with incremental updates."""
    print("\n=== Complete Workflow Example ===")

    # Step 1: Initial full extraction
    print("Step 1: Initial extraction of entire codebase...")
    extract_and_export_directory("src/indexer", "output/codebase_v1.json")

    # Step 2: Simulate file changes and incremental update
    print("Step 2: Incremental update after file changes...")

    # In a real scenario, you would get this list from:
    # - Git diff
    # - File system watchers
    # - Build system notifications
    # - etc.
    changed_files = [
        "src/indexer/__init__.py",
        "src/indexer/ast_parser.py"
    ]

    # Perform incremental update
    incremental_results = incremental_parse(
        file_paths=changed_files,
        previous_json_file="output/codebase_v1.json",
        output_json_file="output/codebase_v2.json",
        deleted_paths=None
    )

    print(f"Updated {len(incremental_results)} files in the codebase")

    # The output/codebase_v2.json now contains the complete updated codebase
    # while incremental_results contains only the data for changed files


if __name__ == "__main__":
    # Create output directory
    Path("output").mkdir(exist_ok=True)
    
    try:
        example_basic_usage()
        example_incremental_usage()
        example_utility_functions()
        example_workflow()
        print("\n✅ All examples completed successfully!")

    except (ImportError, ModuleNotFoundError, OSError, IOError) as e:
        print(f"\n❌ Error running examples: {e}")
        print("Note: This might be due to missing dependencies in the environment.")
        print("The code structure and API are correct.")

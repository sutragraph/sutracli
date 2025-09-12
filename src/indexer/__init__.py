"""
Code indexer for extracting AST data from source files.
Provides high-level functions for parsing, extracting, and exporting code data
without exposing the internal AST parser implementation.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from utils.file_utils import (
    get_extraction_file_path,
    get_language_from_extension,
    get_last_extraction_file_path,
    is_text_file,
    should_ignore_directory,
    should_ignore_file,
)
from utils.hash_utils import compute_directory_hashes, compute_file_hash
from utils.json_serializer import make_json_serializable

from .ast_parser import ASTParser
from .export_ast_to_json import main as export_ast_to_json


def extract_from_directory(dir_path: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
    """
    Parse all files in a directory and extract code blocks with hierarchical structure.
    Also extracts relationships between files based on import statements.

    Args:
        dir_path: Path to the directory

    Returns:
        Dictionary with file paths as keys and extraction results as values,
        each result following the same format as parse_and_extract with added relationships
    """
    parser = ASTParser()
    return parser.extract_from_directory(dir_path)


def export_to_json(
    extraction_results: Dict[str, Dict[str, Any]],
    output_file: Union[str, Path],
    indent: int = 2,
) -> bool:
    """
    Export extraction results to a JSON file.

    Args:
        extraction_results: Results from extract_from_directory method
        output_file: Path to the output JSON file
        indent: JSON indentation level (default: 2)

    Returns:
        True if export was successful, False otherwise
    """
    try:
        output_path = Path(output_file)

        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to JSON-serializable format
        serializable_data = make_json_serializable(extraction_results)

        # Add metadata
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_files": len(extraction_results),
                "extractor_version": "1.0.0",
            },
            "files": serializable_data,
        }

        # Write to JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=indent, ensure_ascii=False)

        print(f"📊 Total files exported: {len(extraction_results)}")
        return True

    except (OSError, IOError, PermissionError, ValueError, TypeError) as e:
        print(f"Error exporting to JSON: {e}")
        return False


def extract_and_export_directory(
    dir_path: Union[str, Path], output_file: Union[str, Path], indent: int = 2
) -> bool:
    """
    Extract from directory and directly export to JSON file.

    Args:
        dir_path: Path to the directory to extract from
        output_file: Path to the output JSON file
        indent: JSON indentation level (default: 2)

    Returns:
        True if extraction and export were successful, False otherwise
    """
    print(f"Extracting from directory: {dir_path}")
    results = extract_from_directory(dir_path)

    if not results:
        print("No results to export")
        return False

    return export_to_json(results, output_file, indent)


def load_previous_results(json_file: Union[str, Path]) -> Dict[str, Dict[str, Any]]:
    """
    Load previous extraction results from JSON file.

    Args:
        json_file: Path to the JSON file

    Returns:
        Dictionary of previous extraction results
    """
    try:
        json_path = Path(json_file)
        if not json_path.exists():
            return {}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("files", {})
    except (OSError, IOError, PermissionError, ValueError, KeyError) as e:
        print(f"Error loading previous results: {e}")
        return {}


def incremental_parse(
    file_paths: List[Path],
    previous_json_file: Path,
    output_json_file: Path,
    deleted_paths: Optional[List[Path]] = None,
    indent: int = 2,
) -> Dict[str, Dict[str, Any]]:
    """
    Perform incremental parsing by updating only changed files and maintaining previous results.

    This function:
    1. Loads previous extraction results
    2. Compares file hashes to detect changes
    3. Parses only changed/new files
    4. Removes deleted files from results
    5. Runs relationship extraction only for changed files (but can reference all files)
    6. Preserves existing relationships for unchanged files
    7. Saves complete updated results to JSON
    8. Returns only the data for input file paths

    Args:
        file_paths: List of file paths to check and potentially re-parse
        previous_json_file: Path to the previous extraction results JSON file
        output_json_file: Path to save the updated complete results
        deleted_paths: Optional list of file paths that have been deleted
        indent: JSON indentation level (default: 2)

    Returns:
        Dictionary containing extraction results for the input file paths only
    """
    print(f"Starting incremental parsing for {len(file_paths)} files...")

    # Load previous results
    previous_results = load_previous_results(previous_json_file)
    print(f"Loaded {len(previous_results)} files from previous results")

    # Start with previous results as base
    updated_results = previous_results.copy()

    # Remove deleted files
    if deleted_paths:
        deleted_paths_str = [str(Path(p)) for p in deleted_paths]
        for deleted_path in deleted_paths_str:
            if deleted_path in updated_results:
                del updated_results[deleted_path]
                print(f"Removed deleted file: {deleted_path}")

    # Track which files need parsing
    files_to_parse = []
    changed_files = []

    # Check each input file for changes
    for file_path in file_paths:
        file_path_str = str(Path(file_path))
        current_hash = compute_file_hash(file_path)

        if current_hash is None:
            print(f"Warning: Could not read file {file_path}")
            continue

        # Check if file is new or changed
        previous_data = previous_results.get(file_path_str, {})
        previous_hash = previous_data.get("content_hash")

        if previous_hash != current_hash:
            files_to_parse.append(file_path)
            changed_files.append(file_path_str)
            print(f"File changed: {file_path}")
        else:
            print(f"File unchanged: {file_path}")

    # Initialize parser once for efficiency
    parser = None

    # Parse changed/new files
    if files_to_parse:
        print(f"Parsing {len(files_to_parse)} changed files...")
        parser = ASTParser()

        for file_path in files_to_parse:
            # Skip ignored files
            if should_ignore_file(file_path):
                print(f"Skipping ignored file: {file_path}")
                continue

            result = parser.parse_and_extract(file_path)
            if result.get("ast") or result.get("error"):
                file_path_str = str(Path(file_path))
                updated_results[file_path_str] = result
                print(f"Updated: {file_path_str}")

    # Run relationship extraction only for changed files
    if changed_files or deleted_paths:
        print(
            f"🔄 Running relationship extraction for {len(changed_files)} changed files..."
        )
        print(f"📝 Changed files: {changed_files}")
        if parser is None:
            parser = ASTParser()

        # First, clear relationships for changed files to avoid stale data
        print("🧹 Clearing existing relationships for changed files...")
        for file_path_str in changed_files:
            if (
                file_path_str in updated_results
                and "relationships" in updated_results[file_path_str]
            ):
                old_rel_count = len(updated_results[file_path_str]["relationships"])
                del updated_results[file_path_str]["relationships"]
                print(f"   Cleared {old_rel_count} relationships from {file_path_str}")

        # Create a subset of results containing only changed files for relationship processing
        # But the relationship extractor needs access to all files to resolve imports correctly
        changed_results = {}
        for file_path_str in changed_files:
            if file_path_str in updated_results:
                changed_results[file_path_str] = updated_results[file_path_str]

        if changed_results:
            print(
                f"📊 Processing {len(changed_results)} changed files for relationships..."
            )

            # The relationship extractor needs all files to resolve imports, but we only want
            # to extract relationships FROM the changed files TO any other files
            # So we pass all files but only process relationships for changed files

            # Create ID to path mapping for all files (needed for import resolution)
            all_id_to_path = {}
            for file_path_str, result in updated_results.items():
                file_id = result.get("id")
                if file_id:
                    all_id_to_path[file_id] = file_path_str
            print(f"🗂️  Created ID mapping for {len(all_id_to_path)} total files")

            # Extract relationships from ALL files (needed for import resolution)
            print("🔍 Extracting relationships from ALL files for import resolution...")
            relationships = parser._relationship_extractor.extract_relationships(
                updated_results
            )
            print(f"📈 Total relationships extracted: {len(relationships)}")

            # Filter relationships to only include those FROM changed files
            print("🎯 Filtering relationships to only those FROM changed files...")
            changed_file_ids = set()
            for file_path_str in changed_files:
                if file_path_str in updated_results:
                    file_id = updated_results[file_path_str].get("id")
                    if file_id:
                        changed_file_ids.add(file_id)
                        print(f"   Changed file ID: {file_id} ({file_path_str})")

            # Only keep relationships that originate from changed files
            filtered_relationships = [
                rel for rel in relationships if rel.source_id in changed_file_ids
            ]
            print(
                f"✂️  Filtered relationships: {len(filtered_relationships)} (from {len(relationships)} total)"
            )

            # Log the filtered relationships
            for i, rel in enumerate(filtered_relationships):
                source_path = all_id_to_path.get(rel.source_id, "unknown")
                target_path = all_id_to_path.get(rel.target_id, "unknown")
                print(
                    f"   {i+1}. {source_path} -> {target_path} ({rel.import_content})"
                )

            # Add the filtered relationships back to the results
            print("💾 Adding filtered relationships back to results...")
            for relationship in filtered_relationships:
                source_file_id = relationship.source_id
                source_file_path = all_id_to_path.get(source_file_id)

                if source_file_path and source_file_path in updated_results:
                    # Initialize relationships list if it doesn't exist
                    if "relationships" not in updated_results[source_file_path]:
                        updated_results[source_file_path]["relationships"] = []

                    # Add the relationship
                    updated_results[source_file_path]["relationships"].append(
                        {
                            "source_id": source_file_id,
                            "target_id": relationship.target_id,
                            "import_content": relationship.import_content,
                        }
                    )
                    print(
                        f"   Added relationship: {source_file_path} -> {all_id_to_path.get(relationship.target_id, 'unknown')}"
                    )

            print("✅ Relationship processing complete!")

    # Save complete updated results
    export_success = export_to_json(updated_results, output_json_file, indent)
    if export_success:
        print(f"Saved complete results to: {output_json_file}")
    else:
        print("Failed to save complete results")

    # Return only the data for input file paths
    input_results = {}
    for file_path in file_paths:
        file_path_str = str(Path(file_path))
        if file_path_str in updated_results:
            input_results[file_path_str] = updated_results[file_path_str]

    print(
        f"Incremental parsing complete. Returning data for {len(input_results)} files."
    )
    return input_results


__all__ = [
    # Main extraction and export functions
    "extract_from_directory",
    "export_to_json",
    "extract_and_export_directory",
    "incremental_parse",
    # Utility functions
    "compute_file_hash",
    "compute_directory_hashes",
    "load_previous_results",
    # Legacy function
    "export_ast_to_json",
    "get_extraction_file_path",
    "get_last_extraction_file_path",
]

#!/usr/bin/env python3
"""
Relationship Display Script

This script parses directories and displays all relationships between files,
showing source/target file paths, IDs, and import statements.
"""

import sys
from pathlib import Path

from ast_parser import ASTParser


def show_relationships(directory_path: str):
    """Parse a directory and display all relationships in a readable format."""

    print(f"🔍 Parsing directory: {directory_path}")
    print("=" * 80)

    # Parse the directory
    parser = ASTParser()
    results = parser.extract_from_directory(directory_path)

    if not results:
        print("❌ No files found or failed to parse directory")
        return

    # Build a mapping from file ID to file path for easy lookup
    id_to_path = {}
    for file_path, result in results.items():
        file_id = result.get("id")
        if file_id:
            id_to_path[file_id] = file_path

    # Count statistics
    total_files = len(results)
    total_relationships = sum(
        len(result.get("relationships", [])) for result in results.values()
    )

    print(f"📁 Files parsed: {total_files}")
    print(f"🔗 Relationships found: {total_relationships}")
    print()

    # Display relationships for each file
    for file_path, result in results.items():
        file_id = result.get("id", "No ID")
        relationships = result.get("relationships", [])

        if not relationships:
            continue

        print(f"📄 Source File: {file_path}")
        print(f"   File ID: {file_id}")
        print(f"   Relationships: {len(relationships)}")
        print()

        for i, rel in enumerate(relationships, 1):
            source_id = rel.get("source_id", "Unknown")
            target_id = rel.get("target_id", "Unknown")
            import_content = rel.get("import_content", "")
            symbols = rel.get("symbols", [])

            # Get target file path
            target_path = id_to_path.get(target_id, "Unknown file")
            target_filename = (
                Path(target_path).name if target_path != "Unknown file" else "Unknown"
            )

            print(f"   {i}. Target: {target_filename}")
            print(f"      └─ Path: {target_path}")
            print(f"      └─ Target ID: {target_id}")
            print(f'      └─ Import: "{import_content}"')

            if symbols:
                symbols_str = ", ".join(symbols)
                print(f"      └─ Symbols: [{symbols_str}]")
            else:
                print(f"      └─ Symbols: [side-effect import]")
            print()

        print("-" * 60)
        print()


def show_detailed_summary(directory_path: str):
    """Show a detailed summary of all relationships."""

    parser = ASTParser()
    results = parser.extract_from_directory(directory_path)

    if not results:
        return

    # Build ID to path mapping
    id_to_path = {}
    for file_path, result in results.items():
        file_id = result.get("id")
        if file_id:
            id_to_path[file_id] = file_path

    print("📊 RELATIONSHIP SUMMARY")
    print("=" * 80)

    all_relationships = []
    for file_path, result in results.items():
        relationships = result.get("relationships", [])
        for rel in relationships:
            source_path = file_path
            target_path = id_to_path.get(rel.get("target_id"), "Unknown")
            all_relationships.append(
                {
                    "source": source_path,
                    "target": target_path,
                    "import": rel.get("import_content", ""),
                    "symbols": rel.get("symbols", []),
                }
            )

    print(f"Total relationships: {len(all_relationships)}")
    print()

    # Group by file extensions
    by_extension = {}
    for rel in all_relationships:
        source_ext = Path(rel["source"]).suffix or "no extension"
        target_ext = Path(rel["target"]).suffix or "no extension"
        key = f"{source_ext} → {target_ext}"

        if key not in by_extension:
            by_extension[key] = 0
        by_extension[key] += 1

    print("Relationships by file type:")
    for ext_pair, count in sorted(by_extension.items()):
        print(f"  {ext_pair}: {count}")
    print()

    # Show all relationships in table format
    print("All Relationships:")
    print(f"{'Source':<25} {'Target':<25} {'Symbols':<20} {'Import'}")
    print("-" * 100)

    for rel in all_relationships:
        source_name = Path(rel["source"]).name
        target_name = (
            Path(rel["target"]).name if rel["target"] != "Unknown" else "Unknown"
        )
        symbols_str = ", ".join(rel["symbols"][:3])  # Show first 3 symbols
        if len(rel["symbols"]) > 3:
            symbols_str += "..."
        import_short = (
            rel["import"][:30] + "..." if len(rel["import"]) > 30 else rel["import"]
        )

        print(f"{source_name:<25} {target_name:<25} {symbols_str:<20} {import_short}")


def test_both_directories():
    """Test both Python and TypeScript directories quickly."""

    test_dirs = [
        ("test_relationships/python", "Python"),
        ("test_relationships/typescript", "TypeScript"),
    ]

    print("🧪 QUICK TEST - BOTH DIRECTORIES")
    print("=" * 80)

    for directory, lang in test_dirs:
        if not Path(directory).exists():
            print(f"⚠️  {lang} test directory not found: {directory}")
            continue

        print(f"\n🔍 Testing {lang}: {directory}")
        print("-" * 40)

        try:
            parser = ASTParser()
            results = parser.extract_from_directory(directory)

            total_files = len(results)
            total_relationships = sum(
                len(result.get("relationships", [])) for result in results.values()
            )

            print(f"✅ Files parsed: {total_files}")
            print(f"✅ Relationships found: {total_relationships}")

            # Show a few example relationships
            relationship_count = 0
            for file_path, result in results.items():
                relationships = result.get("relationships", [])
                if relationships:  # Show max 3 examples
                    filename = Path(file_path).name
                    print(f"   📄 {filename}:")
                    for rel in relationships:  # Show max 2 per file
                        target_path = "Unknown"
                        for fp, res in results.items():
                            if res.get("id") == rel.get("target_id"):
                                target_path = Path(fp).name
                                break
                        symbols = rel.get("symbols", [])
                        symbols_str = (
                            f"[{', '.join(symbols)}]" if symbols else "[side-effect]"
                        )
                        print(f"      → {target_path}: {symbols_str}")
                        relationship_count += 1

        except Exception as e:
            print(f"❌ Error testing {lang}: {e}")

    print(f"\n🎉 Test completed! Use the script normally for detailed output.")


def main():
    """Main function to run the relationship display script."""

    if len(sys.argv) < 2 or (len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help"]):
        print(
            "Usage: python show_relationships.py <directory_path> [--summary] [--test]"
        )
        print("\nExamples:")
        print("  python show_relationships.py test_relationships/python")
        print("  python show_relationships.py test_relationships/typescript")
        print("  python show_relationships.py test_relationships/python --summary")
        print("  python show_relationships.py --test")
        sys.exit(1)

    # Handle test mode
    if "--test" in sys.argv:
        test_both_directories()
        return

    directory_path = sys.argv[1]
    show_summary = "--summary" in sys.argv

    if not Path(directory_path).exists():
        print(f"❌ Directory not found: {directory_path}")
        sys.exit(1)

    try:
        if show_summary:
            show_detailed_summary(directory_path)
        else:
            show_relationships(directory_path)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Main entry point for the tree-sitter code analyzer.

This module provides the command-line interface when running the analyzer
with `python -m analyzer`.
"""

import asyncio
import sys
from pathlib import Path

from .analyzer import Analyzer


async def main():
    """Command line interface for the analyzer."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Tree-sitter based code analyzer",
        prog="python -m analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m analyzer --file example.py
  python -m analyzer --directory ./test --save-results
  python -m analyzer --directory ./src --output analysis.json --show-stats
        """,
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", help="Analyze a single file")
    input_group.add_argument("--directory", help="Analyze a directory")

    # Output options
    parser.add_argument("--output", help="Output file path for JSON results")
    parser.add_argument(
        "--results-folder",
        default="results",
        help="Results folder for saved analysis (default: results)",
    )

    # Analysis options
    parser.add_argument(
        "--repo-id",
        default="cli_analysis",
        help="Repository ID for the analysis (default: cli_analysis)",
    )
    parser.add_argument(
        "--show-stats", action="store_true", help="Show analysis statistics"
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save results to results folder (only for directory analysis)",
    )

    args = parser.parse_args()

    # Create analyzer instance
    analyzer = Analyzer(args.repo_id)

    try:
        if args.file:
            # Single file analysis
            print(f"Analyzing file: {args.file}")
            result = await analyzer.analyze_file(args.file)

            if result:
                print(f"✓ Successfully analyzed: {args.file}")

                if args.output:
                    analyzer.results = {
                        "repo_id": args.repo_id,
                        "nodes": result.get("nodes", []),
                        "edges": result.get("edges", []),
                        "language_stats": {},
                        "analysis_stats": {
                            "total_files": 1,
                            "processed_files": 1,
                            "failed_files": 0,
                        },
                    }
                    analyzer.export_results(args.output)
                    print(f"✓ Results exported to: {args.output}")

                if args.show_stats:
                    nodes_count = len(result.get("nodes", []))
                    edges_count = len(result.get("edges", []))
                    language = result.get("language", "unknown")
                    print(f"\nFile Analysis Summary:")
                    print(f"  Language: {language}")
                    print(f"  Nodes: {nodes_count}")
                    print(f"  Edges: {edges_count}")
            else:
                print(f"✗ Failed to analyze file: {args.file}")
                sys.exit(1)

        elif args.directory:
            # Directory analysis
            print(f"Analyzing directory: {args.directory}")

            if args.save_results:
                # Use the convenient analyze_and_save method
                results_file = await analyzer.analyze_and_save(
                    args.directory, args.results_folder
                )
                print(f"✓ Analysis complete! Results saved to: {results_file}")
            else:
                # Regular analysis
                await analyzer.analyze_directory(args.directory)

                if args.output:
                    analyzer.export_results(args.output)
                    print(f"✓ Results exported to: {args.output}")

            # Show statistics if requested
            if args.show_stats:
                summary = analyzer.get_analysis_summary()
                print(f"\nDirectory Analysis Summary:")
                print(
                    f"  Files processed: {summary['processed_files']}/{summary['total_files']}"
                )
                print(f"  Success rate: {summary['success_rate']:.1%}")
                print(f"  Processing time: {summary['processing_time']:.2f}s")
                print(
                    f"  Languages: {', '.join(sorted(summary['languages_detected']))}"
                )
                print(f"  Total nodes: {summary['total_nodes']}")
                print(f"  Total edges: {summary['total_edges']}")

                # Show node type breakdown
                node_types = summary.get("node_types", {})
                if node_types:
                    print(f"  Node types:")
                    for node_type, count in sorted(node_types.items()):
                        print(f"    {node_type}: {count}")

    except KeyboardInterrupt:
        print("\n✗ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

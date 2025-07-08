#!/usr/bin/env python3
"""
Sutra Knowledge CLI - Full version with complete ML integration.

This tool provides a streamlined interface for:
1. Parsing and indexing repositories
2. Generating embeddings and knowledge graphs
3. Running the AI agent for coding assistance

Usage: Run this tool from any directory to index and interact with that repository.
"""

import sys
import os
from pathlib import Path
from typing import Optional
from argparse import ArgumentParser, Namespace

# Add src to path for imports (src is at project root, not in cli/)
sys.path.insert(0, str(Path(__file__).parent.parent))


# Set up configuration for installed vs development environment
def setup_environment():
    """Set up environment configuration based on installation type."""
    # Check if we're in an installed environment
    sutra_home = Path.home() / ".sutra"
    if sutra_home.exists() and (sutra_home / "config" / "system.json").exists():
        # We're in an installed environment - use system config
        os.environ["SUTRAKNOWLEDGE_CONFIG"] = str(sutra_home / "config" / "system.json")
    elif "SUTRAKNOWLEDGE_CONFIG" not in os.environ:
        # We're in development - use local config if available
        local_config = Path(__file__).parent.parent / "configs" / "local.json"
        if local_config.exists():
            os.environ["SUTRAKNOWLEDGE_CONFIG"] = str(local_config)


# Set up environment before importing other modules
setup_environment()

from src.cli.utils import setup_logging
from loguru import logger
from src.config.settings import get_config


class SutraKnowledgeCLI:
    """Main CLI class for Sutra Knowledge tool."""

    def __init__(self, directory: Optional[str] = None):
        """Initialize the CLI tool."""
        if directory:
            self.current_dir = Path(directory).resolve()
            if not self.current_dir.exists():
                print(f"ERROR: Directory '{directory}' does not exist")
                raise SystemExit(1)
            if not self.current_dir.is_dir():
                print(f"ERROR: '{directory}' is not a directory")
                raise SystemExit(1)
        else:
            self.current_dir = Path.cwd()

        self.repo_name = self.current_dir.name
        self.setup_environment()

    def setup_environment(self):
        """Setup environment and configuration."""
        import os

        # Set up logging with minimal output for CLI
        config = get_config()
        log_level = config.logging.level
        setup_logging(log_level)

        # Set up configuration
        if not os.getenv("SUTRAKNOWLEDGE_CONFIG"):
            config_path = self._find_config_file()

            if config_path:
                os.environ["SUTRAKNOWLEDGE_CONFIG"] = config_path
                logger.debug(f"Using configuration: {config_path}")
            else:
                print("ERROR: No configuration file found")
                print("   Looking for configs/system.json or configs/local.json")
                raise SystemExit(1)

    def _find_config_file(self) -> Optional[str]:
        """Find the appropriate configuration file."""
        import sys

        # Use known config structure - prioritize system.json
        system_config = Path(__file__).parent.parent / "configs" / "system.json"
        if system_config.exists():
            return str(system_config)

        # Fallback to local.json
        local_config = Path(__file__).parent.parent / "configs" / "local.json"
        if local_config.exists():
            return str(local_config)

        return None

    def display_welcome(self):
        """Display welcome message and tool information."""
        import os

        print("\n" + "=" * 80)
        print("SUTRA KNOWLEDGE - AI-Powered Repository Assistant")
        print("   Intelligent code analysis, indexing, and AI assistance")
        print("=" * 80)
        print(f"Current Directory: {self.current_dir}")
        print(f"Repository Name: {self.repo_name}")

        # Show configuration being used (debug info)
        config_file = os.getenv("SUTRAKNOWLEDGE_CONFIG", "Not set")
        if config_file != "Not set":
            config_name = Path(config_file).name
            print(f"Configuration: {config_name}")
        print()

    def check_if_indexed(self) -> bool:
        """Check if the current repository is already indexed."""
        try:
            from src.graph.sqlite_client import SQLiteConnection

            db = SQLiteConnection()
            return db.project_exists(self.repo_name)
        except Exception as e:
            logger.debug(f"Error checking if project exists: {e}")
            return False

    def prompt_for_indexing(self) -> bool:
        """Prompt user to proceed with indexing."""
        print("Repository Analysis Required")
        print(
            "   To provide intelligent assistance, I need to analyze and index this repository."
        )
        print("   This process will:")
        print("   * Parse all code files using tree-sitter")
        print("   * Generate semantic embeddings")
        print("   * Build a knowledge graph")
        print("   * Enable AI-powered code assistance")
        print()

        try:
            response = (
                input("Press Enter to proceed with indexing (or 'q' to quit): ")
                .strip()
                .lower()
            )
            return response != "q"
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            return False

    def run_parser(self) -> Optional[str]:
        """Run the parser on the current directory."""
        print("\nPHASE 1: Parsing Repository")
        print("-" * 40)
        print("Analyzing code structure and extracting AST information...")

        try:
            # Import parser command handler
            from src.cli.commands import handle_parse_command

            # Create args object for handle_parse_command
            args = Namespace(directory=str(self.current_dir), repo_id=self.repo_name)

            # Run the parser
            result_path = handle_parse_command(args)

            if result_path and Path(result_path).exists():
                print(f"SUCCESS: Parsing completed successfully!")
                print(f"Results saved to: {result_path}")
                return result_path
            else:
                print("ERROR: Parsing failed - no output file generated")
                return None

        except Exception as e:
            print(f"ERROR: Parsing failed with error: {e}")
            logger.error(f"Parser error: {e}")
            return None

    def run_embedding_and_graph_generation(self, parser_output_path: str) -> bool:
        """Generate embeddings and knowledge graph from parser output."""
        print("\nPHASE 2: Generating Embeddings & Knowledge Graph")
        print("-" * 40)
        print("\n✨ Creating semantic embeddings and building knowledge graph...\n")

        try:
            # Import graph converter
            from src.graph import TreeSitterToSQLiteConverter

            converter = TreeSitterToSQLiteConverter()
            result = converter.convert_json_to_graph(
                parser_output_path,
                project_name=self.repo_name,
                clear_existing=True,  # Clear any existing data for this project
                create_indexes=True,
            )

            if result and result.get("status") == "success":
                stats = result.get("database_stats", {})
                print(f"SUCCESS: Knowledge graph generated successfully!")
                print(
                    f"Processed: {stats.get('total_nodes', 0)} nodes, {stats.get('total_relationships', 0)} relationships"
                )
                print(f"Embeddings: Generated for semantic search")
                return True
            else:
                print("ERROR: Knowledge graph generation failed")
                return False

        except Exception as e:
            print(f"ERROR: Knowledge graph generation failed with error: {e}")
            logger.error(f"Graph generation error: {e}")
            return False

    def run_agent(self):
        """Run the AI agent for interactive assistance."""
        print("\nPHASE 3: Starting AI Agent")
        print("-" * 40)
        print("Initializing AI assistant with repository knowledge...")
        print()

        try:
            # Import agent command handler
            from src.cli.commands import handle_agent_command

            # Create args object for handle_agent_command
            args = Namespace(
                problem_query=None,  # Start in interactive mode
                project_id=None,  # Will auto-detect from repository
            )

            # Run the agent
            handle_agent_command(args)

        except Exception as e:
            print(f"ERROR: Agent failed with error: {e}")
            logger.error(f"Agent error: {e}")

    def run(self):
        """Main entry point for the CLI tool."""
        self.display_welcome()

        # Check if repository is already indexed
        is_indexed = self.check_if_indexed()

        if is_indexed:
            print("Repository Already Indexed")
            print("   This repository has been previously analyzed and indexed.")
            print("   Skipping parsing and embedding generation...")
            print()

            # Skip directly to agent
            self.run_agent()
            return

        # Repository not indexed - need to do full indexing
        if not self.prompt_for_indexing():
            return

        # Phase 1: Parse repository
        parser_output = self.run_parser()
        if not parser_output:
            print("\nERROR: Failed to parse repository. Cannot proceed.")
            sys.exit(1)

        # Phase 2: Generate embeddings and knowledge graph
        if not self.run_embedding_and_graph_generation(parser_output):
            print("\nERROR: Failed to generate knowledge graph. Cannot proceed.")
            sys.exit(1)

        # Phase 3: Run agent
        print("\nSUCCESS: Repository indexing completed successfully!")
        print("   Ready to provide AI-powered assistance.")
        print()

        self.run_agent()


def parse_arguments():
    """Parse command line arguments."""
    parser = ArgumentParser(
        description="Sutra Knowledge - AI-Powered Repository Assistant",
        epilog="Intelligent code analysis, indexing, and AI assistance",
    )

    parser.add_argument(
        "--directory",
        "-d",
        type=str,
        help="Directory to analyze (default: current directory)",
        metavar="PATH",
    )

    parser.add_argument(
        "--version", action="version", version="Sutra Knowledge CLI v1.0"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments first, before any setup
    args = parse_arguments()

    try:
        cli = SutraKnowledgeCLI(directory=args.directory)
        cli.run()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted. Goodbye!")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        # Only log if logger is available
        try:
            logger.error(f"CLI error: {e}")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

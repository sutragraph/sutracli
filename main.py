#!/usr/bin/env python3
"""Main entry point for the Sutra Knowledge application."""

import sys
import os
from pathlib import Path

# Set tokenizers parallelism before any imports to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add src to path for development/direct execution
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cli.parser import setup_argument_parser
from cli.utils import setup_logging
from cli.commands import (
    handle_single_command,
    handle_multi_command,
    handle_list_command,
    handle_clear_command,
    handle_stats_command,
    handle_agent_command,
    handle_parse_command,
    handle_search_command,
    handle_auth_command,
    handle_web_search_command,
    handle_web_scrap_command,
    handle_version_command,
    handle_cross_indexing_command,
)
from cli.utils import (
    process_multiple_projects,
    load_project_config,
    list_projects,
    clear_database_data,
    show_database_stats,
)

from loguru import logger


def main():
    """Main entry point for the CLI application."""
    parser = setup_argument_parser()
    args = parser.parse_args()

    if args.command is None:
        if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
            args = parser.parse_args(["single"] + sys.argv[1:])
        else:
            parser.print_help()
            return

    if hasattr(args, "log_level"):
        setup_logging(args.log_level)
        # Set debug mode flag if DEBUG level is specified
        if args.log_level == "DEBUG":
            from utils.debug_utils import set_debug_mode, set_auto_mode

            set_debug_mode(True)

            # Set auto mode flag if --auto is specified with DEBUG level
            if hasattr(args, "auto") and args.auto:
                set_auto_mode(True)

    try:
        if args.command == "single":
            handle_single_command(args)

        elif args.command == "multi":
            handle_multi_command(args, process_multiple_projects, load_project_config)

        elif args.command == "list":
            handle_list_command(args, list_projects)

        elif args.command == "clear":
            handle_clear_command(args, clear_database_data)

        elif args.command == "stats":
            handle_stats_command(args, show_database_stats)

        elif args.command == "agent":
            handle_agent_command(args)

        elif args.command == "parse":
            result_path = handle_parse_command(args)

        elif args.command == "search":
            handle_search_command(args)
        elif args.command == "auth":
            handle_auth_command(args)
        elif args.command == "web_search":
            handle_web_search_command(args)
        elif args.command == "web_scrap":
            handle_web_scrap_command(args)

        elif args.command == "version":
            handle_version_command(args)

        elif args.command == "cross-indexing":
            handle_cross_indexing_command(args)

        else:
            logger.error(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

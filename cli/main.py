#!/usr/bin/env python3
"""Main entry point for the Sutra Knowledge application."""


import os
import sys
from pathlib import Path

from loguru import logger

from src.utils.console import console

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["BAML_LOG"] = "OFF"

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


def main():
    """Main entry point for the CLI application."""

    from cli.arg_parser import setup_argument_parser
    from cli.commands import (
        handle_agent_command,
        handle_cross_indexing_command,
        handle_index_command,
        handle_list_command,
        handle_parse_command,
        handle_run_phase5_command,
        handle_search_command,
        handle_single_command,
        handle_version_command,
        handle_web_scrap_command,
        handle_web_search_command,
    )
    from src.utils.logging import setup_logging

    # Check if only --log-level is passed (for modern CLI)
    if len(sys.argv) == 1 or (len(sys.argv) == 3 and sys.argv[1] == "--log-level"):
        # Extract log level if provided
        log_level = "INFO"  # default
        if len(sys.argv) == 3 and sys.argv[1] == "--log-level":
            log_level = sys.argv[2].upper()

        # Run modern interactive CLI
        from cli.modern_cli import ModernSutraKit

        cli = ModernSutraKit(log_level=log_level)
        cli.run()
        return

    # Original command-line interface
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
            from src.utils.debug_utils import set_auto_mode, set_debug_mode

            set_debug_mode(True)

            # Set auto mode flag if --auto is specified with DEBUG level
            if hasattr(args, "auto") and args.auto:
                set_auto_mode(True)

    try:
        if args.command == "single":
            handle_single_command(args)

        elif args.command == "list":
            handle_list_command(args)

        elif args.command == "agent":
            handle_agent_command()

        elif args.command == "parse":
            handle_parse_command(args)

        elif args.command == "index":
            handle_index_command(args)

        elif args.command == "search":
            handle_search_command(args)

        elif args.command == "web_search":
            handle_web_search_command(args)
        elif args.command == "web_scrap":
            handle_web_scrap_command(args)
        elif args.command == "version":
            handle_version_command()
        elif args.command == "cross-indexing":
            handle_cross_indexing_command(args)
        elif args.command == "run-phase5":
            handle_run_phase5_command(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        console.error("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

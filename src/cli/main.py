#!/usr/bin/env python3
"""Main entry point for the Sutra Knowledge application."""

import os
import sys
from pathlib import Path

# Set tokenizers parallelism before any imports to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Set up environment configuration
def setup_environment():
    """Set up environment configuration based on installation type."""
    # Check if we're in an installed environment
    sutra_home = Path.home() / ".sutra"
    if sutra_home.exists() and (sutra_home / "config" / "system.json").exists():
        # We're in an installed environment - use system config
        os.environ["SUTRAKNOWLEDGE_CONFIG"] = str(sutra_home / "config" / "system.json")
    elif "SUTRAKNOWLEDGE_CONFIG" not in os.environ:
        # We're in development - use local config if available
        local_config = root_dir / "configs" / "local.json"
        if local_config.exists():
            os.environ["SUTRAKNOWLEDGE_CONFIG"] = str(local_config)

def setup_baml_environment():
    """Set up BAML environment variables from config at module level."""
    try:
        # Import here to avoid circular imports
        from config.settings import get_config

        # Use the config function to get loaded config
        config = get_config()

        # Environment variable mapping for each provider
        ENV_VAR_MAPPING = {
            "aws": {
                "AWS_ACCESS_KEY_ID": "access_key_id",
                "AWS_SECRET_ACCESS_KEY": "secret_access_key",
                "AWS_MODEL_ID": "model_id",
                "AWS_REGION": "region",
            },
            "openai": {"OPENAI_API_KEY": "api_key", "OPENAI_MODEL_ID": "model_id"},
            "anthropic": {
                "ANTHROPIC_API_KEY": "api_key",
                "ANTHROPIC_MODEL_ID": "model_id",
            },
            "gcp": {"GOOGLE_API_KEY": "api_key", "GOOGLE_MODEL_ID": "model_id"},
        }

        # Check if config has llm attribute
        if not hasattr(config, "llm") or not config.llm:
            return

        provider = config.llm.provider.lower()
        if provider not in ENV_VAR_MAPPING:
            return

        # Get provider-specific config
        provider_config = getattr(config.llm, provider, None)
        if not provider_config:
            return

        # Set environment variables
        env_mapping = ENV_VAR_MAPPING[provider]
        for env_var, config_key in env_mapping.items():
            # Only set if not already set and config value exists
            if env_var not in os.environ:
                value = getattr(provider_config, config_key, None)
                if value:
                    os.environ[env_var] = str(value)

        os.environ["BAML_LOG"] = "warn"

    except Exception as e:
        # Silent fail - don't break CLI if environment setup fails
        pass

# Set up environment before importing other modules
setup_environment()
setup_baml_environment()

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
    handle_index_command,
    handle_search_command,
    handle_auth_command,
    handle_web_search_command,
    handle_web_scrap_command,
    handle_version_command,
    handle_cross_indexing_command,
)
from cli.phase5_command import handle_run_phase5_command
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
        if len(sys.argv)> 1 and sys.argv[1].endswith(".json"):
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

        elif args.command == "index":
            handle_index_command(args)

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

        elif args.command == "run-phase5":
            handle_run_phase5_command()

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

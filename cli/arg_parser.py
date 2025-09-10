"""Argument parser setup for the CLI application."""

import argparse

from src.config.settings import config


def _add_single_parser(subparsers, default_log_level: str) -> None:
    """Add single file processing command parser."""
    single_parser = subparsers.add_parser("single", help="Process a single JSON file")
    single_parser.add_argument("input_file", help="Path to the tree-sitter JSON file")
    single_parser.add_argument(
        "--project-name",
        help="Name of the project/codebase (auto-derived from filename if not provided)",
    )
    single_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data in the database before import",
    )
    single_parser.add_argument(
        "--no-indexes", action="store_true", help="Skip creating database indexes"
    )
    single_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=default_log_level,
        help="Set the logging level",
    )


def _add_list_parser(subparsers, default_log_level: str) -> None:
    """Add list projects command parser."""
    list_parser = subparsers.add_parser("list", help="List projects in the database")
    list_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=default_log_level,
        help="Set the logging level",
    )


def _add_parse_parser(subparsers, default_log_level: str) -> None:
    """Add parse command parser for code analysis."""
    parse_parser = subparsers.add_parser(
        "parse", help="Parse and analyze code repository"
    )
    parse_parser.add_argument(
        "--directory",
        default=".",
        help="Directory to analyze (default: current directory)",
    )
    parse_parser.add_argument(
        "--repo-id",
        default="default_repo",
        help="Repository identifier (default: default_repo)",
    )
    parse_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=default_log_level,
        help="Set the logging level",
    )


def _add_search_parser(subparsers, default_log_level: str) -> None:
    """Add search command parser for semantic search."""
    search_parser = subparsers.add_parser(
        "search", help="Search for code chunks using semantic similarity"
    )
    search_parser.add_argument("query", help="Search query to find similar code chunks")
    search_parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Maximum number of chunks to return (default: 15)",
    )
    search_parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Similarity threshold (default: 0.1)",
    )
    search_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=default_log_level,
        help="Set the logging level",
    )


def _add_index_parser(subparsers, default_log_level: str) -> None:
    """Add index command parser for full project indexing."""
    index_parser = subparsers.add_parser(
        "index", help="Fully index a project at a specific path (parse + embeddings)"
    )
    index_parser.add_argument(
        "project_path",
        help="Path to the project directory to index",
    )
    index_parser.add_argument(
        "--project-name",
        help="Custom project name (default: directory name)",
    )
    index_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-indexing even if project already exists",
    )
    index_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=default_log_level,
        help="Set the logging level",
    )


def _add_web_search_parser(subparsers, default_log_level: str) -> None:
    """Add web search command parser."""
    web_search_parser = subparsers.add_parser(
        "web_search", help="Perform web search using Search Engine"
    )
    web_search_parser.add_argument("--query", required=True, help="Search query")
    web_search_parser.add_argument(
        "--time-filter",
        type=str,
        choices=["pd", "pw", "pm", "py"],
        help="Time filter for search results (pd=past day, pw=past week, pm=past month, py=past year)",
    )
    web_search_parser.add_argument(
        "--safe-search",
        type=str,
        choices=["off", "moderate", "strict"],
        default="moderate",
        help="Safe search filter level (default: moderate)",
    )
    web_search_parser.add_argument(
        "--search-type",
        type=str,
        choices=["search", "news", "images", "videos"],
        default="search",
        help="Type of search to perform (default: search)",
    )
    web_search_parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of results to return (default: 10)",
    )
    web_search_parser.add_argument(
        "--offset", type=int, default=0, help="Offset for pagination (default: 0)"
    )
    web_search_parser.add_argument(
        "--country",
        type=str,
        help="Country code for localized results (e.g., 'US', 'UK')",
    )
    web_search_parser.add_argument(
        "--search-lang",
        type=str,
        help="Language for search results (e.g., 'en', 'es', 'fr')",
    )
    web_search_parser.add_argument(
        "--ui-lang",
        type=str,
        help="Language for user interface (e.g., 'en', 'es', 'fr')",
    )
    web_search_parser.add_argument(
        "--no-spellcheck", action="store_true", help="Disable spellcheck for the query"
    )
    web_search_parser.add_argument(
        "--result-filter",
        type=str,
        nargs="+",
        help="Filter results by specific criteria (space-separated list)",
    )
    web_search_parser.add_argument(
        "--goggles-id", type=str, help="Goggles ID for custom search lens"
    )
    web_search_parser.add_argument(
        "--units",
        type=str,
        choices=["metric", "imperial"],
        default="metric",
        help="Units for measurements (default: metric)",
    )
    web_search_parser.add_argument(
        "--extra-snippets",
        action="store_true",
        help="Include extra snippets in results",
    )


def _add_web_scrap_parser(subparsers, default_log_level: str) -> None:
    """Add web scraper command parser."""
    web_scrap_parser = subparsers.add_parser(
        "web_scrap", help="Web scraping operations"
    )

    # URL argument (required)
    web_scrap_parser.add_argument("url", help="URL to scrape content from")

    # Output format options
    web_scrap_parser.add_argument(
        "--format",
        choices=["text", "html", "markdown"],
        default="text",
        help="Output format: text, html, or markdown (default: text)",
    )


def _add_cross_index_parser(subparsers, default_log_level: str) -> None:
    """Add cross-indexing command parser."""
    cross_index_parser = subparsers.add_parser(
        "cross-indexing", help="Analyze project for cross-service connections"
    )
    cross_index_parser.add_argument(
        "--directory",
        "-d",
        default=".",
        help="Directory to analyze (default: current directory)",
    )
    cross_index_parser.add_argument(
        "--project-name",
        help="Custom project name (default: directory name)",
    )
    cross_index_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )
    cross_index_parser.add_argument(
        "--auto",
        action="store_true",
        help="Skip confirmation prompts when used with --log-level DEBUG",
    )


def _add_phase5_parser(subparsers, default_log_level: str) -> None:
    """Add run-phase5 command parser."""
    phase5_parser = subparsers.add_parser(
        "run-phase5",
        help="Run Phase 5 (Connection Matching) of cross-indexing directly",
    )
    phase5_parser.add_argument(
        "--directory",
        "-d",
        default=".",
        help="Directory to analyze (default: current directory)",
    )
    phase5_parser.add_argument(
        "--project-name",
        help="Custom project name (default: directory name)",
    )
    phase5_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )


def _add_version_parser(subparsers, default_log_level: str) -> None:
    """Add version command parser."""
    version_parser = subparsers.add_parser("version", help="Show version information")


def _add_common_log_level_argument(parser, default_log_level: str) -> None:
    """Add common log level argument to a parser."""
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=default_log_level,
        help="Set the logging level",
    )


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the main argument parser with all subcommands."""
    default_log_level = config.logging.level
    parser = argparse.ArgumentParser(
        description="Convert tree-sitter JSON to SQLite with embeddings for semantic search"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add all subcommand parsers
    _add_single_parser(subparsers, default_log_level)
    _add_list_parser(subparsers, default_log_level)
    _add_parse_parser(subparsers, default_log_level)
    _add_search_parser(subparsers, default_log_level)
    _add_index_parser(subparsers, default_log_level)
    _add_web_search_parser(subparsers, default_log_level)
    _add_web_scrap_parser(subparsers, default_log_level)
    _add_cross_index_parser(subparsers, default_log_level)
    _add_phase5_parser(subparsers, default_log_level)
    _add_version_parser(subparsers, default_log_level)

    return parser

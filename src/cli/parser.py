"""Argument parser setup for the CLI application."""

import argparse


def setup_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert tree-sitter JSON to SQLite with embeddings for semantic search"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Single file processing command
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
        default="INFO",
        help="Set the logging level",
    )

    # Multi-project processing command
    multi_parser = subparsers.add_parser(
        "multi", help="Process multiple projects from config file"
    )
    multi_parser.add_argument(
        "config_file", help="Path to the project configuration JSON file"
    )
    multi_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # List projects command
    list_parser = subparsers.add_parser("list", help="List projects in the database")
    list_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear data from the database")
    clear_parser.add_argument(
        "--project",
        help="Clear only a specific project (if not provided, clears all data)",
    )
    clear_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )
    clear_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats", help="Show database and embedding statistics"
    )
    stats_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # Agent analysis command (intelligent agent-based analysis)
    agent_parser = subparsers.add_parser(
        "agent",
        help="Enter interactive Sutra Agent mode for coding assistance",
    )
    agent_parser.add_argument(
        "problem_query",
        nargs="?",  # Make it optional
        help="Optional initial problem description (if not provided, will enter interactive mode)",
    )
    agent_parser.add_argument(
        "--project-id", type=int, help="Limit analysis to specific project ID"
    )
    agent_parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum analysis iterations (default: 5)",
    )
    agent_parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.8,
        help="Confidence threshold to stop analysis early (default: 0.8)",
    )
    agent_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )

    # Parse command for code analysis
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
        default="INFO",
        help="Set the logging level",
    )

    # Search command for semantic search
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
        default="INFO",
        help="Set the logging level"
        )
    # Auth command for authentication management
    auth_parser = subparsers.add_parser(
        "auth", help="Authentication management for LLM providers"
    )
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Authentication commands")

    # Auth login command
    login_parser = auth_subparsers.add_parser("login", help="Authenticate with SuperLLM")
    login_parser.add_argument(
        "--provider", default="superllm", help="Provider name (default: superllm)"
    )
    login_parser.add_argument(
        "--token", help="Firebase token (if not provided, will prompt)"
    )
    login_parser.add_argument(
        "--api-endpoint", default="http://localhost:8000", help="SuperLLM API endpoint"
    )
    login_parser.add_argument(
        "--web-url", default="http://localhost:3000", help="SuperLLM web interface URL"
    )
    login_parser.add_argument(
        "--auto-open", action="store_true", help="Automatically open web interface"
    )

    # Auth status command
    status_parser = auth_subparsers.add_parser("status", help="Check authentication status")
    status_parser.add_argument(
        "--provider", help="Specific provider to check (default: all)"
    )

    # Auth logout command
    logout_parser = auth_subparsers.add_parser("logout", help="Remove authentication token")
    logout_parser.add_argument(
        "--provider", default="superllm", help="Provider to logout from"
    )
    logout_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

    # Auth test command
    test_parser = auth_subparsers.add_parser("test", help="Test authentication")
    test_parser.add_argument(
        "--provider", default="superllm", help="Provider to test"
    )
    test_parser.add_argument(
        "--api-endpoint", help="Override API endpoint for testing"
    )

    # Auth clear command
    clear_auth_parser = auth_subparsers.add_parser("clear", help="Clear all authentication tokens")
    clear_auth_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation prompt"
    )

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

    # Web scraper parser configuration
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

    return parser

"""Command handlers for the CLI application."""

import sys
import webbrowser
from pathlib import Path
from loguru import logger
import requests
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from graph import TreeSitterToSQLiteConverter
from services.agent_service import AgentService
from services.auth.token_manager import get_token_manager
from config import config
from embeddings.vector_db import VectorDatabase
from services.agent.tool_action_executor.utils.code_processing_utils import (
    add_line_numbers_to_code,
)
from services.agent.tool_action_executor.tools.web_search_action import (
    WebSearch,
    TimeFilter,
    SafeSearch,
    SearchType,
)
from services.agent.tool_action_executor.tools.web_scrap_action import WebScraper


def handle_single_command(args) -> None:
    """Process a single tree-sitter JSON file."""
    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"Input file not found: {args.input_file}")
        sys.exit(1)

    with TreeSitterToSQLiteConverter() as converter:
        print("Starting conversion to SQLite...")
        result = converter.convert_json_to_graph(
            args.input_file,
            project_name=args.project_name or None,
            clear_existing=args.clear,
            create_indexes=not args.no_indexes,
        )

        if result["status"] == "success":
            print("✅ Conversion completed successfully!")
            print(
                f"Processed {result['nodes_processed']} nodes and {result['relationships_processed']} relationships"
            )
            print(
                "🔍 Chunked embeddings generated automatically for all nodes (optimized for 95+ accuracy semantic search)"
            )

            stats = result["database_stats"]
            print(
                f"Database now contains {stats['total_nodes']} nodes and {stats['total_relationships']} relationships"
            )
        else:
            logger.error("❌ Conversion failed")
            logger.error(f"Error: {result['error']}")
            sys.exit(1)


def handle_multi_command(
    args, process_multiple_projects_func, load_project_config_func
) -> None:
    """Process multiple projects defined in config."""
    if not Path(args.config_file).exists():
        logger.error(f"Configuration file not found: {args.config_file}")
        sys.exit(1)

    config_data = load_project_config_func(args.config_file)
    result = process_multiple_projects_func(config_data)

    if result["status"] == "completed":
        print("🎉 Multi-project processing completed!")
        print(
            f"Processed {result['projects_processed']}/{result['total_projects']} projects successfully"
        )
        print(
            f"Total: {result['total_nodes_processed']} nodes, {result['total_relationships_processed']} relationships"
        )
        print(
            "🔍 Chunked embeddings generated for all nodes with maximum information retention"
        )

        stats = result["final_database_stats"]
        print(
            f"Final database: {stats['total_nodes']} nodes, {stats['total_relationships']} relationships"
        )
    else:
        logger.error("❌ Multi-project processing failed")
        sys.exit(1)


def handle_list_command(args, list_projects_func) -> None:
    """Handle list projects command."""
    list_projects_func()


def handle_clear_command(args, clear_database_data_func) -> None:
    """Handle clear database command."""
    result = clear_database_data_func(project_name=args.project, force=args.force)

    if result["status"] == "success":
        if result.get("project_name"):
            print(
                f"✅ Successfully cleared project '{result['project_name']}' ({result['nodes_deleted']} nodes)"
            )
        else:
            print(
                f"✅ Successfully cleared entire database ({result['nodes_deleted']} nodes, {result.get('relationships_deleted', 0)} relationships)"
            )
    elif result["status"] == "no_data":
        logger.warning(f"No data found for project '{result['project_name']}'")
    elif result["status"] == "cancelled":
        print("Clear operation cancelled")
    else:
        logger.error("Clear operation failed")
        sys.exit(1)


def handle_stats_command(args, show_database_stats_func) -> None:
    """Handle database statistics command."""
    show_database_stats_func()


def _process_agent_updates(updates_generator) -> None:
    """Process agent updates and print them in formatted output."""
    for update in updates_generator:
        update_type = update.get("type", "unknown")
        if update_type == "thinking":
            content = update.get("content", "Thinking...")
            print(f"🤔 Thinking...")
            if content and content.strip():
                print(f"   {content}")
            print("-" * 40)

        if update_type == "task_complete":
            completion = update.get("completion", {})
            result_text = completion.get("result", "Task completed")
            print(f"🎉 Task Completed 🎉 ")
            print(f"   Result: {result_text}")
            print("-" * 40)

        if update_type == "tool_use":
            tool_name = update.get("tool_name", "unknown")

            if tool_name == "terminal":
                command = update.get("command", "")
                print(f'💻 Terminal command executed: "{command}"')
                print("-" * 40)

            elif tool_name == "write_to_file":
                file_path = update.get("applied_changes_to_files", "")
                print(f"📝 File edited: {file_path}")
                print("-" * 40)

            elif tool_name == "apply_diff":
                file_path = update.get("successful_files", "")
                if file_path:
                    print(f"📝 Git diff applied to {file_path}")
                    print("-" * 40)

            elif tool_name == "database":
                query = update.get("query", "")
                query_name = update.get("query_name", "")
                results = update.get("result", "")
                print(f'🔍 Database search "{query} - {query_name}" | {results}')
                print("-" * 40)

            elif tool_name == "semantic_search":
                query = update.get("query", "")
                results = update.get("result", "")
                print(f'🔍 Semantic search "{query}" | {results}')
                print("-" * 40)

            elif tool_name == "list_files":
                directory = update.get("directory", "")
                files_count = update.get("count", 0)
                print(f"📁 Listed {files_count} files in {directory}")
                print("-" * 40)

            elif tool_name == "search_keyword":
                keyword = update.get("keyword", "")
                matches_found = update.get("matches_found")
                print(f'🔍 Keyword search "{keyword}" | Found {matches_found}')
                print("-" * 40)

        elif update_type == "too_error":
            error = update.get("error", "")
            print(f"❌ {error}")
            print("-" * 40)

        else:
            pass


def handle_agent_command(args) -> None:
    """Handle agent command for autonomous problem solving."""
    print(f"\n🤖 SUTRA AGENT - AI-Powered Repository Assistant")
    print("   Your intelligent companion for coding, debugging, and knowledge sharing")
    print("=" * 80)

    try:
        agent = AgentService()

        if args.problem_query:
            print(f"📝 Initial Problem: {args.problem_query}")
            print("🚀 Starting analysis...")
            print("-" * 40)
            _process_agent_updates(
                agent.solve_problem(
                    problem_query=args.problem_query,
                    project_id=getattr(args, "project_id", None),
                ),
            )
            print("\n✅ INITIAL REQUEST COMPLETED")
        else:
            print("🚀 Welcome to Sutra Agent!")
            print(
                "   I'm here to help you with coding, debugging, and knowledge sharing."
            )

        print("\n💬 How can I help you? Type your questions or requests below.")
        print("   Type 'exit' or 'quit' to end the session.")
        print("=" * 80)

        while True:
            try:
# Create history and completer for enhanced input
                history = InMemoryHistory()
                completer = WordCompleter(['exit', 'quit', 'bye', 'goodbye', 'help'])
                
                # Create key bindings
                bindings = KeyBindings()
                
                @bindings.add('c-c')
                def _(event):
                    """Handle Ctrl+C"""
                    raise KeyboardInterrupt
                
                # Enhanced prompt with multiline support and navigation
                user_input = prompt(
                    "\n👤 You: ",
                    multiline=True,
                    history=history,
                    completer=completer,
                    complete_while_typing=True,
                    key_bindings=bindings,
                    mouse_support=True,
                    bottom_toolbar="Press [Meta+Enter] or [Escape followed by Enter] to submit multiline input. Use arrow keys to navigate.",
                ).strip()
                print("-" * 40)

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    print("\n👋 Goodbye! Session ended.")
                    break

                if args.problem_query:
                    _process_agent_updates(
                        agent.continue_conversation(
                            query=user_input,
                            project_id=getattr(args, "project_id", None),
                        ),
                    )
                else:
                    _process_agent_updates(
                        agent.solve_problem(
                            problem_query=user_input,
                            project_id=getattr(args, "project_id", None),
                        ),
                    )
                    args.problem_query = user_input

                print("\n✅ Response completed. What would you like to do next?")

            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted. Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Session ended. Goodbye!")
                break

    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


def handle_parse_command(args) -> str:
    """Handle parse command for code analysis."""
    import asyncio
    import time
    import sys
    from pathlib import Path

    # Import analyzer using relative import from the parser package
    from parser.analyzer.analyzer import Analyzer

    directory_path = args.directory
    repo_id = args.repo_id

    # Create output directory
    output_dir = Path(config.storage.parser_results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create analyzer instance - no need for start_node_id with deterministic IDs
        analyzer = Analyzer(repo_id)

        # Generate output filename with timestamp
        dir_name = Path(directory_path).name
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{dir_name}_analysis_{timestamp}.json"

        # Analyze the directory
        asyncio.run(analyzer.analyze_directory(directory_path))

        # Export results to JSON
        analyzer.export_results(str(output_file))

        return str(output_file)

    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}")
        sys.exit(1)


def handle_search_command(args) -> None:
    """Handle semantic search command."""
    try:
        print(f"🔍 Searching for: '{args.query}'")
        print(f"📊 Limit: {args.limit}, Threshold: {args.threshold}")
        print("📁 Searching through file nodes with embeddings...")
        print("-" * 40)

        # Initialize vector database
        vector_db = VectorDatabase()

        # Perform search
        chunks = vector_db.search_chunks_with_code(
            query_text=args.query,
            limit=args.limit,
            threshold=args.threshold,
            max_display_lines=None,  # Show full chunks without truncation
        )

        if not chunks:
            print("❌ No similar code chunks found.")
            print("💡 Try:")
            print("   - Lowering the similarity threshold (--threshold)")
            print("   - Using different search terms")
            print(
                "   - Checking if file embeddings have been generated for your codebase"
            )
            return

        print(f"✅ Found {len(chunks)} similar file chunks:\n")

        for i, chunk in enumerate(chunks, 1):
            similarity_percent = chunk["similarity"] * 100

            # Header with chunk info
            print(f"{'='*60}")
            print(f"CHUNK {i}/{len(chunks)} - Similarity: {similarity_percent:.1f}%")
            print(f"{'='*60}")

            # Metadata
            print(f"📁 File: {chunk['file_path']}")
            print(f"🏷️  Node: {chunk['node_name']} ({chunk['node_type']})")
            print(f"📍 Project: {chunk['project_name']} ({chunk['language']})")

            # Line information
            if chunk["chunk_start_line"] and chunk["chunk_end_line"]:
                line_count = chunk["chunk_end_line"] - chunk["chunk_start_line"] + 1
                print(
                    f"📏 Lines: {chunk['chunk_start_line']}-{chunk['chunk_end_line']} ({line_count} lines)"
                )
            else:
                print(f"📏 Lines: Full file content")

            print(f"🔢 Chunk: {chunk['chunk_index']}")
            print("-" * 40)

            # Code content
            if chunk["chunk_code"]:
                print("💻 Code:")
                print("-" * 40)
                # Use the existing add_line_numbers_to_code function
                start_line = chunk["chunk_start_line"] or 1
                numbered_code = add_line_numbers_to_code(
                    chunk["chunk_code"], start_line
                )
                print(numbered_code)
                print("-" * 40)
            else:
                print("💻 Code: (No code content available)")

            print("-" * 40)

        print(f"🎯 Search completed. Found {len(chunks)} relevant file chunks.")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        print(f"❌ Search failed: {e}")
        sys.exit(1)


def handle_incremental_parse_command(args) -> str:
    """Handle incremental parse command for code updates."""
    # Set the incremental flag to true
    args.incremental = True

    # Call the regular parse command with the incremental flag set
    return handle_parse_command(args)

def handle_auth_command(args) -> None:
    """Handle authentication commands."""
    if not hasattr(args, "auth_command") or args.auth_command is None:
        print(
            "❌ No auth subcommand specified. Use 'sutra auth --help' for available commands."
        )
        sys.exit(1)

    if args.auth_command == "login":
        _handle_auth_login(args)
    elif args.auth_command == "status":
        _handle_auth_status(args)
    elif args.auth_command == "logout":
        _handle_auth_logout(args)
    elif args.auth_command == "test":
        _handle_auth_test(args)
    elif args.auth_command == "clear":
        _handle_auth_clear(args)
    else:
        print(f"❌ Unknown auth command: {args.auth_command}")
        sys.exit(1)


def _handle_auth_login(args) -> None:
    """Handle auth login command."""
    provider = args.provider
    token = args.token
    api_endpoint = args.api_endpoint
    web_url = args.web_url
    auto_open = args.auto_open

    print(f"🔐 Authenticating with {provider.upper()}")
    print("=" * 50)

    # Open web interface if requested
    if auto_open:
        print(f"🌐 Opening SuperLLM web interface: {web_url}")
        try:
            webbrowser.open(web_url)
        except Exception as e:
            print(f"⚠️  Could not open browser: {e}")
            print(f"   Please manually open: {web_url}")
    else:
        print(f"📱 Please open the SuperLLM web interface: {web_url}")

    print("\n📋 Steps to get your token:")
    print("   1. Sign in or create an account")
    print("   2. Copy the Firebase authentication token")
    print("   3. Paste it below")

    # Get token from user if not provided
    if not token:
        print("-" * 40)
        token = input("🔑 Enter your Firebase token: ").strip()

    if not token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)

    # Validate token by making a test API call
    print("\n🔍 Validating token...")

    if _validate_token(token, api_endpoint):
        # Store the token
        token_manager = get_token_manager()
        metadata = {
            "api_endpoint": api_endpoint,
            "web_url": web_url,
            "validated_at": None,  # Will be set by token manager
        }

        token_manager.store_token(provider, token, metadata)

        print("✅ Token validated and stored successfully!")
        print(f"   Provider: {provider}")
        print(f"   API Endpoint: {api_endpoint}")
        print("\n🎉 You can now use SutraKnowledge with SuperLLM!")
        print("   Set your provider to 'superllm' in the configuration.")

    else:
        print("❌ Token validation failed.")
        print("   Please check:")
        print("   • Token is correct and not expired")
        print("   • SuperLLM server is running")
        print(f"   • API endpoint is correct: {api_endpoint}")
        sys.exit(1)


def _handle_auth_status(args) -> None:
    """Handle auth status command."""
    provider = args.provider
    token_manager = get_token_manager()
    providers = token_manager.list_providers()

    if not providers:
        print("🔓 No authentication tokens stored.")
        return

    print("🔐 Authentication Status")
    print("=" * 50)

    for prov_name, info in providers.items():
        if provider and prov_name != provider:
            continue

        print(f"\n📡 Provider: {prov_name}")
        print(
            f"   Status: {'✅ Authenticated' if info['has_token'] else '❌ No token'}"
        )

        if info["stored_at"]:
            print(f"   Stored: {info['stored_at']}")

        if info["metadata"]:
            metadata = info["metadata"]
            if "api_endpoint" in metadata:
                print(f"   Endpoint: {metadata['api_endpoint']}")
            if "web_url" in metadata:
                print(f"   Web URL: {metadata['web_url']}")


def _handle_auth_logout(args) -> None:
    """Handle auth logout command."""
    provider = args.provider
    force = args.force

    if not force:
        response = input(
            f"Are you sure you want to remove the authentication token for {provider}? (y/N): "
        )
        if response.lower() not in ["y", "yes"]:
            print("Logout cancelled.")
            return

    token_manager = get_token_manager()

    if token_manager.remove_token(provider):
        print(f"✅ Logged out from {provider}")
    else:
        print(f"⚠️  No token found for {provider}")


def _handle_auth_test(args) -> None:
    """Handle auth test command."""
    provider = args.provider
    api_endpoint = args.api_endpoint

    token_manager = get_token_manager()
    token = token_manager.get_token(provider)

    if not token:
        print(f"❌ No token found for {provider}")
        print(f"   Run 'sutra auth login --provider {provider}' first")
        return

    # Get API endpoint
    if not api_endpoint:
        providers = token_manager.list_providers()
        if provider in providers and "api_endpoint" in providers[provider]["metadata"]:
            api_endpoint = providers[provider]["metadata"]["api_endpoint"]
        else:
            api_endpoint = "http://localhost:8000"  # Default

    print(f"🧪 Testing authentication with {provider}")
    print(f"   Endpoint: {api_endpoint}")

    if _validate_token(token, api_endpoint):
        print("✅ Authentication test successful!")
    else:
        print("❌ Authentication test failed!")
        print("   Token may be expired or invalid.")
        print(f"   Try: sutra auth login --provider {provider}")


def _handle_auth_clear(args) -> None:
    """Handle auth clear command."""
    force = args.force

    if not force:
        response = input(
            "Are you sure you want to clear ALL authentication tokens? (y/N): "
        )
        if response.lower() not in ["y", "yes"]:
            print("Clear operation cancelled.")
            return

    token_manager = get_token_manager()
    token_manager.clear_all_tokens()
    print("✅ All authentication tokens cleared")


def _validate_token(token: str, api_endpoint: str) -> bool:
    """
    Validate a Firebase token by making a test API call.

    Args:
        token: Firebase token to validate
        api_endpoint: SuperLLM API endpoint

    Returns:
        True if token is valid, False otherwise
    """
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Try to get models list (lightweight endpoint)
        response = requests.get(
            f"{api_endpoint}/api/v1/models", headers=headers, timeout=10
        )

        return response.status_code == 200

    except requests.exceptions.ConnectionError:
        print(f"⚠️  Could not connect to {api_endpoint}")
        print("   Make sure SuperLLM server is running")
        return False
    except requests.exceptions.Timeout:
        print("⚠️  Request timed out")
        return False
    except Exception as e:
        logger.debug(f"Token validation error: {e}")
        return False


def handle_web_search_command(args) -> None:
    """Handle web search command."""

    print(f"🔎 Searching for: '{args.query}'")
    print("🌐 Fetching results from web...")

    time_filter = TimeFilter(args.time_filter) if args.time_filter else None
    safe_search = (
        SafeSearch(args.safe_search) if args.safe_search else SafeSearch.MODERATE
    )
    search_type = SearchType(args.search_type) if args.search_type else SearchType.WEB
    try:
        response = WebSearch.search(
            query=args.query,
            time_filter=time_filter,
            safe_search=safe_search,
            search_type=search_type,
            count=args.count,
            offset=args.offset,
            country=args.country,
            search_lang=args.search_lang,
            ui_lang=args.ui_lang,
            spellcheck=not args.no_spellcheck,
            result_filter=args.result_filter,
            goggles_id=args.goggles_id,
            units=args.units,
            extra_snippets=args.extra_snippets,
        )
        if response:
            print(f"Found {len(response.results)} results for '{response.query}'")
            for i, result in enumerate(response.results, 1):
                print(f"{i}. {result.title}")
                print(f"   {result.url}")
                print(f"   {result.description}\n")
    except Exception as e:
        print(f"❌ Error fetching search results: {str(e)}")


def handle_web_scrap_command(args) -> None:
    """Handle web scraping command."""

    print(f"🌐 Scraping content from: '{args.url}'")
    print(f"📄 Output format: {args.format}")

    try:
        if args.format == "html":
            print("🔍 Extracting HTML content...")
            content = WebScraper.fetch_html_content(args.url)
        elif args.format == "markdown":
            print("🔍 Extracting HTML content...")
            html_content = WebScraper.fetch_html_content(args.url)
            if html_content:
                print("📝 Converting to markdown...")
                content = WebScraper.html_to_markdown(html_content)
            else:
                content = None
        else:  # text format (default)
            print("🔍 Extracting text content...")
            content = WebScraper.fetch_text_content(args.url)

        if content:
            print(f"✅ Successfully scraped {len(content)} characters")
            print("-" * 50)
            print(content)
        else:
            print("❌ Failed to scrape content from the URL")

    except Exception as e:
        print(f"❌ Error scraping content: {str(e)}")
    finally:
        # Close the session when done
        WebScraper.close_session()

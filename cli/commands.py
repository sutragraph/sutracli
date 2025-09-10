"""Command handlers for the CLI application."""

import uuid
import sys
from pathlib import Path
from loguru import logger

from src.agents_new import Agent

from src.graph import SQLiteConnection, ASTToSqliteConverter
from src.services.project_manager import ProjectManager
from src.services.cross_indexing.core.cross_index_system import CrossIndexSystem
from src.services.agent_service_new import AgentService
from src.config import config

from src.utils.console import console
from rich.panel import Panel

from src.embeddings import get_vector_store
from src.tools.utils.code_processing_utils import (
    add_line_numbers_to_code,
)
from src.tools.tool_web_search.action import (
    WebSearch,
    TimeFilter,
    SafeSearch,
    SearchType,
)
from src.tools.tool_web_scrap.action import WebScraper


def get_version_from_init():
    """Get version from sutrakit/__init__.py file."""
    try:
        import re
        from pathlib import Path

        # Try to read version from sutrakit/__init__.py directly to avoid circular imports
        init_file = Path(__file__).parent.parent / "sutrakit" / "__init__.py"
        if init_file.exists():
            with open(init_file, "r") as f:
                content = f.read()
                version_match = re.search(
                    r'__version__\s*=\s*["\']([^"\']+)["\']', content
                )
                if version_match:
                    return version_match.group(1)
    except Exception:
        pass
    return "0.1.5"


def handle_single_command(args) -> None:
    """Process a single tree-sitter JSON file."""
    pass


def handle_list_command(args) -> None:
    """Handle list projects command."""
    connection = SQLiteConnection()
    projects = connection.list_all_projects()

    if not projects:
        console.info("No projects found in the database.")
        return

    console.info(f"Found {len(projects)} project(s):")
    console.print()

    for idx, project in enumerate(projects, 1):
        # Create a panel for each project
        content = f"""[key]ID:[/key] {project.id}
[key]Path:[/key] [path]{project.path}[/path]
[key]Description:[/key] {project.description}
[key]Created:[/key] {project.created_at}
[key]Updated:[/key] {project.updated_at}
[key]Cross-Indexed:[/key] {'✅ Yes' if project.cross_indexing_done else '❌ No'}"""

        panel = Panel(
            content,
            title=f"[bold]{idx}. {project.name}[/bold]",
            border_style="panel_border",
            title_align="left"
        )
        console.print(panel)


def handle_agent_command(agent_name: Agent, project_path: Path):
    """Handle agent command for autonomous problem solving."""
    print(f"\n🤖 SUTRA AGENT - AI-Powered Repository Assistant")
    print("   Your intelligent companion for coding, debugging, and knowledge sharing")
    print("=" * 80)

    try:
        agent = AgentService(agent_name=agent_name, project_path=project_path)

        return agent.run()

    except KeyboardInterrupt:
        print("\n❌ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


def handle_parse_command(args) -> str:
    """Handle parse command for code analysis."""
    return ""


def handle_index_command(args) -> None:
    """Handle full project indexing command."""
    from pathlib import Path
    from src.services.project_manager import ProjectManager
    from src.graph.sqlite_client import SQLiteConnection

    try:
        # Validate project path
        project_path = Path(args.project_path).absolute()
        if not project_path.exists():
            print(f"❌ Project path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            print(f"❌ Project path is not a directory: {project_path}")
            return

        # Initialize required components
        db_connection = SQLiteConnection()
        project_manager = ProjectManager(db_connection)

        # Determine project name
        project_name = args.project_name
        if not project_name:
            project_name = project_manager.determine_project_name(project_path)

        print(f"📁 Indexing project '{project_name}' at: {project_path}")

        # Check if project already exists and handle force flag
        if db_connection.project_exists(project_name):
            if not args.force:
                print(f"⚠️  Project '{project_name}' already exists in database.")
                return
            else:
                print(f"🔄 Force re-indexing existing project '{project_name}'")
                # Clear existing project data before re-indexing
                try:
                    delete_result = project_manager.delete_project(project_name)
                    if delete_result["success"]:
                        print(f"   ✅ Cleared existing project data")
                    else:
                        print(
                            f"   ⚠️  Warning: Could not clear existing data: {delete_result['error']}"
                        )
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not clear existing data: {e}")

        # Perform the indexing
        result = project_manager.index_project_at_path(str(project_path), project_name)

        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ Failed to index project: {result['error']}")

    except Exception as e:
        logger.error(f"Error during project indexing: {e}")
        print(f"❌ Unexpected error: {e}")


def handle_search_command(args) -> None:
    """Handle semantic search command."""
    try:
        print(f"🔍 Searching for: '{args.query}'")
        print(f"📊 Limit: {args.limit}, Threshold: {args.threshold}")
        print("📁 Searching through file nodes with embeddings...")
        print("-" * 40)

        # Initialize vector store
        vector_store = get_vector_store()

        # Perform search
        chunks = vector_store.search_similar_chunks(
            query_text=args.query,
            limit=args.limit,
            threshold=args.threshold,
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
            print(f"{'=' * 60}")
            print(f"CHUNK {i}/{len(chunks)} - Similarity: {similarity_percent:.1f}%")
            print(f"{'=' * 60}")

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


def handle_cross_indexing_command(args) -> None:
    """Handle cross-indexing command for analyzing inter-service connections."""
    try:
        print("🔗 SUTRA CROSS-INDEX - Inter-Service Connection Analysis")
        print("=" * 80)

        # Validate project path
        project_path = Path(args.directory).absolute()
        if not project_path.exists():
            print(f"❌ Project path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            print(f"❌ Project path is not a directory: {project_path}")
            return

        print(f"📁 Analyzing project at: {project_path}")

        # Initialize required components
        project_manager = ProjectManager()
        from src.graph.graph_operations import GraphOperations

        graph_ops = GraphOperations()
        # Get or create project first to determine project name
        project_name = (
            args.project_name
            if args.project_name
            else project_manager.determine_project_name(project_path)
        )

        if graph_ops.is_cross_indexing_done(project_name):
            print(f"✅ Cross-indexing already completed for project '{project_name}'")
            print("📊 Skipping analysis - project already fully analyzed")
            return

        # Initialize cross-index system with project name for incremental indexing
        print(
            f"🔄 Initializing cross-indexing system with incremental indexing for project: {project_name}"
        )
        cross_index_system = CrossIndexSystem(
            project_manager, project_name=project_name
        )

        # Check if we should skip cross-indexing (if already completed)
        if (
            hasattr(cross_index_system, "_skip_cross_indexing")
            and cross_index_system._skip_cross_indexing
        ):
            return

        print(f"✅ Cross-indexing system initialized with up-to-date database")
        project_id = project_manager.get_or_create_project_id(
            project_name, project_path
        )

        print(f"✅ Project: {project_name} (ID: {project_id})")
        print("-" * 40)

        session_id = str(uuid.uuid4())[:8]
        print(f"📝 Started analysis session: {session_id}")

        print("🤖 Starting Cross-Index Analysis...")
        print("-" * 40)

        # Use cross-indexing service for analysis with streaming updates
        cross_index_service = cross_index_system.cross_index_service

        for update in cross_index_service.analyze_project_connections(
            str(project_path), project_id
        ):
            update_type = update.get("type", "unknown")

            if update_type == "cross_index_failure":
                error = update.get("error", "Analysis failed")
                print(f"❌ Cross-indexing failed: {error}")
                break

            elif update_type == "user_cancelled":
                print(f"❌ User cancelled the operation")
                break

            elif update_type == "cross_index_error":
                error = update.get("error", "Critical error")
                print(f"❌ Critical error: {error}")
                break

        print("\n🎉 Cross-Index Analysis Completed!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error during cross-indexing: {e}")
        print(f"❌ Unexpected error: {e}")


def handle_run_phase5_command(args) -> None:
    """Handle run-phase5 command to directly run Phase 5 connection matching."""
    try:
        print("🔗 SUTRA PHASE 5 - Connection Matching Analysis")
        print("=" * 80)

        # Validate project path
        project_path = Path(args.directory).absolute()
        if not project_path.exists():
            print(f"❌ Project path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            print(f"❌ Project path is not a directory: {project_path}")
            return

        print(f"📁 Analyzing project at: {project_path}")

        # Initialize required components
        project_manager = ProjectManager()
        from src.graph.graph_operations import GraphOperations

        graph_ops = GraphOperations()

        # Get or create project first to determine project name
        project_name = (
            args.project_name
            if args.project_name
            else project_manager.determine_project_name(project_path)
        )

        project_id = project_manager.get_or_create_project_id(
            project_name, project_path
        )

        print(f"✅ Project: {project_name} (ID: {project_id})")
        print("-" * 40)

        # Check if cross-indexing data exists
        # Instead of checking for a specific flag, check if we have connections data
        available_tech_types = graph_ops.get_available_technology_types()
        if not available_tech_types:
            # Try to check if there are any connections at all
            sample_connections = graph_ops.fetch_connections_by_technology("Unknown")
            if (
                not sample_connections["incoming"]
                and not sample_connections["outgoing"]
            ):
                print("❌ No cross-indexing data found for this project")
                print("💡 Please run full cross-indexing analysis first using:")
                print(f"   python3 main.py cross-indexing --directory '{project_path}'")
                return

        # Initialize cross-index system
        from src.services.cross_indexing.core.cross_index_system import CrossIndexSystem

        cross_index_system = CrossIndexSystem(
            project_manager, project_name=project_name
        )
        cross_index_service = cross_index_system.cross_index_service

        print("🔍 Starting Phase 5: Connection Matching Analysis...")
        print("-" * 40)

        try:
            # Execute only Phase 5 - Connection Matching
            phase5_result = cross_index_service._execute_phase_5({}, project_id)

            if phase5_result.get("success"):
                matching_result = phase5_result.get("matching_result", {})
                matches = matching_result.get("matches", [])

                print(f"🎉 Phase 5 completed successfully!")
                print(f"📊 Connection Matching Results:")
                print(f"   🔗 Total matches found: {len(matches)}")

                if matches:
                    print(
                        f"   💾 Stored {len(matches)} connection mappings in database"
                    )

                    # Display some sample matches
                    sample_count = min(5, len(matches))
                    if sample_count > 0:
                        print(
                            f"\n📋 Sample matches (showing {sample_count} of {len(matches)}):"
                        )
                        for i, match in enumerate(matches[:sample_count]):
                            confidence = match.get("match_confidence", "unknown")
                            reason = match.get("match_reason", "No reason provided")
                            print(f"   {i + 1}. Confidence: {confidence}")
                            print(f"      Reason: {reason}")
                            print()
                else:
                    print("   ℹ️  No connection matches found")

                storage_result = phase5_result.get("storage_result", {})
                if storage_result.get("success"):
                    print("✅ Results stored in database successfully")

            else:
                error = phase5_result.get("error", "Unknown error")
                print(f"❌ Phase 5 failed: {error}")

        except Exception as phase_error:
            logger.error(f"Phase 5 execution error: {phase_error}")
            print(f"❌ Phase 5 execution failed: {phase_error}")

        print("\n🎉 Phase 5 Analysis Completed!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error during Phase 5 execution: {e}")
        print(f"❌ Unexpected error: {e}")


def handle_version_command(args) -> None:
    """Handle version command to show version information."""
    try:
        # Get version from __init__.py
        version = get_version_from_init()

        print(f"\n📦 Sutra Knowledge CLI Version: {version}")
        print("🔧 AI-Powered Repository Assistant")
        print("📚 Intelligent code analysis, indexing, and assistance")

        # Show Python version
        import sys

        print(f"🐍 Python Version: {sys.version.split()[0]}")

        # Show current directory
        from pathlib import Path

        print(f"📁 Current Directory: {Path.cwd()}")

        # Show configuration info
        import os

        config_file = os.getenv("SUTRAKNOWLEDGE_CONFIG", "Not set")
        if config_file != "Not set":
            config_name = Path(config_file).name
            print(f"⚙️  Configuration: {config_name}")

        print()

    except Exception as e:
        print(f"❌ Error getting version information: {str(e)}")
        sys.exit(1)

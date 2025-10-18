"""Command handlers for the CLI application."""

import sys
import uuid
from pathlib import Path

from loguru import logger
from rich.panel import Panel
from rich.text import Text

from src.agents_new import Agent
from src.embeddings import get_vector_store
from src.graph import SQLiteConnection
from src.services.agent_service_new import AgentService
from src.services.project_manager import ProjectManager
from src.tools.tool_web_scrap.action import WebScraper
from src.tools.tool_web_search.action import (
    SafeSearch,
    SearchType,
    TimeFilter,
    WebSearch,
)
from src.tools.utils.code_processing_utils import add_line_numbers_to_code
from src.utils.console import console
from src.utils.version_checker import VersionChecker


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
[key]Cross-Indexed:[/key] {"✅ Yes" if project.cross_indexing_done else "❌ No"}"""

        panel = Panel(
            content,
            title=f"[bold]{idx}. {project.name}[/bold]",
            border_style="panel_border",
            title_align="left",
        )
        console.print(panel)


def handle_agent_command(agent_name: Agent, project_path: Path):
    """Handle agent command for autonomous problem solving."""
    console.print(f"\n🤖 SUTRA AGENT - AI-Powered Repository Assistant")
    console.print(
        "   Your intelligent companion for coding, debugging, and knowledge sharing"
    )
    console.print("=" * 80)

    try:
        agent = AgentService(agent_name=agent_name, project_path=project_path)

        return agent.run()

    except KeyboardInterrupt:
        console.print("\n❌ Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


def handle_parse_command(args) -> str:
    """Handle parse command for code analysis."""
    return ""


def handle_index_command(args) -> None:
    """Handle full project indexing command."""
    from pathlib import Path

    from src.graph.sqlite_client import SQLiteConnection
    from src.services.project_manager import ProjectManager

    try:
        # Validate project path
        project_path = Path(args.project_path).absolute()
        if not project_path.exists():
            console.print(f"❌ Project path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            console.print(f"❌ Project path is not a directory: {project_path}")
            return

        # Initialize required components
        db_connection = SQLiteConnection()
        project_manager = ProjectManager(db_connection)

        # Determine project name
        project_name = args.project_name
        if not project_name:
            project_name = project_manager.determine_project_name(project_path)

        console.print(f"📁 Indexing project '{project_name}' at: {project_path}")

        # Check if project already exists and handle force flag
        if db_connection.project_exists(project_name):
            if not args.force:
                console.print(
                    f"⚠️  Project '{project_name}' already exists in database."
                )
                return
            else:
                console.print(f"🔄 Force re-indexing existing project '{project_name}'")
                # Clear existing project data before re-indexing
                try:
                    delete_result = project_manager.delete_project(project_name)
                    if delete_result["success"]:
                        console.print(f"   ✅ Cleared existing project data")
                    else:
                        console.print(
                            f"   ⚠️  Warning: Could not clear existing data: {delete_result['error']}"
                        )
                except Exception as e:
                    console.print(f"   ⚠️  Warning: Could not clear existing data: {e}")

        # Perform the indexing
        result = project_manager.index_project_at_path(str(project_path), project_name)

        if result["success"]:
            console.print(f"✅ {result['message']}")
        else:
            console.print(f"❌ Failed to index project: {result['error']}")

    except Exception as e:
        logger.error(f"Error during project indexing: {e}")
        console.print(f"❌ Unexpected error: {e}")


def handle_search_command(args) -> None:
    """Handle semantic search command."""
    try:
        console.print(f"🔍 Searching for: '{args.query}'")
        console.print(f"📊 Limit: {args.limit}, Threshold: {args.threshold}")
        console.print("📁 Searching through file nodes with embeddings...")
        console.print("-" * 40)

        # Initialize vector store
        vector_store = get_vector_store()

        # Perform search
        chunks = vector_store.search_similar_chunks(
            query_text=args.query,
            limit=args.limit,
            threshold=args.threshold,
        )

        if not chunks:
            console.print("❌ No similar code chunks found.")
            console.print("💡 Try:")
            console.print("   - Lowering the similarity threshold (--threshold)")
            console.print("   - Using different search terms")
            console.print(
                "   - Checking if file embeddings have been generated for your codebase"
            )
            return

        console.print(f"✅ Found {len(chunks)} similar file chunks:\n")

        for i, chunk in enumerate(chunks, 1):
            similarity_percent = chunk["similarity"] * 100

            # Header with chunk info
            console.print(f"{'=' * 60}")
            console.print(
                f"CHUNK {i}/{len(chunks)} - Similarity: {similarity_percent:.1f}%"
            )
            console.print(f"{'=' * 60}")

            # Metadata
            console.print(f"📁 File: {chunk['file_path']}")
            console.print(f"🏷️  Node: {chunk['node_name']} ({chunk['node_type']})")
            console.print(f"📍 Project: {chunk['project_name']} ({chunk['language']})")

            # Line information
            if chunk["chunk_start_line"] and chunk["chunk_end_line"]:
                line_count = chunk["chunk_end_line"] - chunk["chunk_start_line"] + 1
                console.print(
                    f"📏 Lines: {chunk['chunk_start_line']}-{chunk['chunk_end_line']} ({line_count} lines)"
                )
            else:
                console.print(f"📏 Lines: Full file content")

            console.print(f"🔢 Chunk: {chunk['chunk_index']}")
            console.print("-" * 40)

            # Code content
            if chunk["chunk_code"]:
                console.print("💻 Code:")
                console.print("-" * 40)
                # Use the existing add_line_numbers_to_code function
                start_line = chunk["chunk_start_line"] or 1
                numbered_code = add_line_numbers_to_code(
                    chunk["chunk_code"], start_line
                )
                console.print(numbered_code)
                console.print("-" * 40)
            else:
                console.print("💻 Code: (No code content available)")

            console.print("-" * 40)

        console.print(f"🎯 Search completed. Found {len(chunks)} relevant file chunks.")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        console.print(f"❌ Search failed: {e}")
        sys.exit(1)


def handle_incremental_parse_command(args) -> str:
    """Handle incremental parse command for code updates."""
    # Set the incremental flag to true
    args.incremental = True

    # Call the regular parse command with the incremental flag set
    return handle_parse_command(args)


def handle_web_search_command(args) -> None:
    """Handle web search command."""

    console.print(f"🔎 Searching for: '{args.query}'")
    console.print("🌐 Fetching results from web...")

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
            console.print(
                f"Found {len(response.results)} results for '{response.query}'"
            )
            for i, result in enumerate(response.results, 1):
                console.print(f"{i}. {result.title}")
                console.print(f"   {result.url}")
                console.print(f"   {result.description}\n")
    except Exception as e:
        console.print(f"❌ Error fetching search results: {str(e)}")


def handle_web_scrap_command(args) -> None:
    """Handle web scraping command."""

    console.print(f"🌐 Scraping content from: '{args.url}'")
    console.print(f"📄 Output format: {args.format}")

    try:
        if args.format == "html":
            console.print("🔍 Extracting HTML content...")
            content = WebScraper.fetch_html_content(args.url)
        elif args.format == "markdown":
            console.print("🔍 Extracting HTML content...")
            html_content = WebScraper.fetch_html_content(args.url)
            if html_content:
                console.print("📝 Converting to markdown...")
                content = WebScraper.html_to_markdown(html_content)
            else:
                content = None
        else:  # text format (default)
            console.print("🔍 Extracting text content...")
            content = WebScraper.fetch_text_content(args.url)

        if content:
            console.print(f"✅ Successfully scraped {len(content)} characters")
            console.print("-" * 50)
            console.print(content)
        else:
            console.print("❌ Failed to scrape content from the URL")

    except Exception as e:
        console.print(f"❌ Error scraping content: {str(e)}")
    finally:
        # Close the session when done
        WebScraper.close_session()


def handle_cross_indexing_command(args) -> None:
    """Handle cross-indexing command for analyzing inter-service connections."""
    try:
        console.print("🔗 SUTRA CROSS-INDEX - Inter-Service Connection Analysis")
        console.print("=" * 80)

        # Validate project path
        project_path = Path(args.directory).absolute()
        if not project_path.exists():
            console.print(f"❌ Project path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            console.print(f"❌ Project path is not a directory: {project_path}")
            return

        console.print(f"📁 Analyzing project at: {project_path}")

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
            console.print(
                f"✅ Cross-indexing already completed for project '{project_name}'"
            )
            console.print("📊 Skipping analysis - project already fully analyzed")
            return

        # Initialize cross-index system with project name for incremental indexing
        console.print(
            f"🔄 Initializing cross-indexing system with incremental indexing for project: {project_name}"
        )
        from src.services.cross_indexing.core.cross_index_system import CrossIndexSystem

        cross_index_system = CrossIndexSystem(
            project_manager, project_name=project_name
        )

        # Check if we should skip cross-indexing (if already completed)
        if (
            hasattr(cross_index_system, "_skip_cross_indexing")
            and cross_index_system._skip_cross_indexing
        ):
            return

        console.print(f"✅ Cross-indexing system initialized with up-to-date database")
        project_id = project_manager.get_or_create_project_id(
            project_name, project_path
        )

        console.print(f"✅ Project: {project_name} (ID: {project_id})")
        console.print("-" * 40)

        session_id = str(uuid.uuid4())[:8]
        console.print(f"📝 Started analysis session: {session_id}")

        console.print("🤖 Starting Cross-Index Analysis...")
        console.print("-" * 40)

        # Use cross-indexing service for analysis with streaming updates
        cross_index_service = cross_index_system.cross_index_service

        for update in cross_index_service.analyze_project_connections(
            str(project_path), project_id
        ):
            update_type = update.get("type", "unknown")

            if update_type == "cross_index_failure":
                error = update.get("error", "Analysis failed")
                console.print(f"❌ Cross-indexing failed: {error}")
                break

            elif update_type == "user_cancelled":
                console.print(f"❌ User cancelled the operation")
                break

            elif update_type == "cross_index_error":
                error = update.get("error", "Critical error")
                console.print(f"❌ Critical error: {error}")
                break

        console.print("\n🎉 Cross-Index Analysis Completed!")
        console.print("=" * 80)

    except Exception as e:
        logger.error(f"Error during cross-indexing: {e}")
        console.print(f"❌ Unexpected error: {e}")


def handle_run_phase5_command(args) -> None:
    """Handle run-phase5 command to directly run Phase 5 connection matching."""
    try:
        console.print("🔗 SUTRA PHASE 5 - Connection Matching Analysis")
        console.print("=" * 80)

        # Validate project path
        project_path = Path(args.directory).absolute()
        if not project_path.exists():
            console.print(f"❌ Project path does not exist: {project_path}")
            return

        if not project_path.is_dir():
            console.print(f"❌ Project path is not a directory: {project_path}")
            return

        console.print(f"📁 Analyzing project at: {project_path}")

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

        console.print(f"✅ Project: {project_name} (ID: {project_id})")
        console.print("-" * 40)

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
                console.print("❌ No cross-indexing data found for this project")
                console.print("💡 Please run full cross-indexing analysis first using:")
                console.print(
                    f"   python3 main.py cross-indexing --directory '{project_path}'"
                )
                return

        # Initialize cross-index system
        from src.services.cross_indexing.core.cross_index_system import CrossIndexSystem

        cross_index_system = CrossIndexSystem(
            project_manager, project_name=project_name
        )
        cross_index_service = cross_index_system.cross_index_service

        console.print("🔍 Starting Phase 5: Connection Matching Analysis...")
        console.print("-" * 40)

        try:
            # Execute only Phase 5 - Connection Matching
            phase5_result = cross_index_service._execute_phase_5({}, project_id)

            if phase5_result.get("success"):
                matching_result = phase5_result.get("matching_result", {})
                matches = matching_result.get("matches", [])

                console.print(f"🎉 Phase 5 completed successfully!")
                console.print(f"📊 Connection Matching Results:")
                console.print(f"   🔗 Total matches found: {len(matches)}")

                if matches:
                    console.print(
                        f"   💾 Stored {len(matches)} connection mappings in database"
                    )

                    # Display some sample matches
                    sample_count = min(5, len(matches))
                    if sample_count > 0:
                        console.print(
                            f"\n📋 Sample matches (showing {sample_count} of {len(matches)}):"
                        )
                        for i, match in enumerate(matches[:sample_count]):
                            confidence = match.get("match_confidence", "unknown")
                            reason = match.get("match_reason", "No reason provided")
                            console.print(f"   {i + 1}. Confidence: {confidence}")
                            console.print(f"      Reason: {reason}")
                            console.print()
                else:
                    console.print("   ℹ️  No connection matches found")

                storage_result = phase5_result.get("storage_result", {})
                if storage_result.get("success"):
                    console.print("✅ Results stored in database successfully")

            else:
                error = phase5_result.get("error", "Unknown error")
                console.print(f"❌ Phase 5 failed: {error}")

        except Exception as phase_error:
            logger.error(f"Phase 5 execution error: {phase_error}")
            console.print(f"❌ Phase 5 execution failed: {phase_error}")

        console.print("\n🎉 Phase 5 Analysis Completed!")
        console.print("=" * 80)

    except Exception as e:
        logger.error(f"Error during Phase 5 execution: {e}")
        console.print(f"❌ Unexpected error: {e}")


def handle_version_command() -> None:
    current, latest = (
        VersionChecker.get_current_version(),
        VersionChecker.get_latest_version(),
    )
    status = (
        VersionChecker.compare_versions(current, latest)
        if current and latest
        else "unknown"
    )

    version_text = Text()
    version_text.append("📚 SutraCLI Version\n\n", style="bold blue")
    version_text.append(f"Current: v{current}\n", style="bold yellow")
    if latest and status == "outdated":
        version_text.append(f"Latest:  v{latest}\n", style="bold green")
        version_text.append("A new version is available!\n", style="bold red")
        version_text.append("Update with: ", style="dim")
        version_text.append("pip install --upgrade sutrakit\n", style="cyan")
    elif latest and status == "latest":
        version_text.append("You are up to date!\n", style="bold green")
    elif not latest:
        version_text.append(
            "Could not check for updates (network issue)\n", style="dim"
        )

    version_text.append("\n🔧 AI-Powered Repository Assistant\n", style="bold")
    version_text.append("📚 Intelligent code analysis, indexing, and assistance\n")
    version_text.append(f"🐍 Python Version: {sys.version.split()[0]}\n", style="dim")
    version_text.append(f"📁 Current Directory: {Path.cwd()}\n", style="dim")

    panel = Panel.fit(
        version_text,
        title="SutraKit Version Info",
        border_style="bright_blue",
        padding=(1, 2),
    )
    console.print(panel)

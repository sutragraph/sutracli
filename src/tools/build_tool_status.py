from typing import Any, Dict, Optional
from loguru import logger
from utils.console import console
from baml_client.types import Agent, ImpactLevel, FileOperation


def build_tool_status(tool_name: str, event: Dict[str, Any], agent: Agent) -> str:
    """Helper to build tool status dictionary."""
    logger.debug(f"building tool status for {tool_name} with event: {event}")
    match tool_name:
        case "database":
            return _build_database_status(event)
        case "semantic_search":
            return _build_semantic_search_status(event)
        case "list_files":
            return _build_list_files_status(event)
        case "keyword_search":
            return _build_keyword_search_status(event)
        case "attempt_completion":
            return _build_completion_status(event, agent)
        case _:
            return f"Unknown tool name '{tool_name}'"


def _build_database_status(event: Dict[str, Any]) -> str:
    """Helper to build database status dictionary."""
    query_name = event.get("query_name")
    query = event.get("query")
    count = event.get("count") or event.get("total_events")
    error = event.get("error")
    data = event.get("data", "")

    # Minimal format console output
    status_parts = []

    if query_name:
        status_parts.append(f"[value]{query_name}[/value]")

    if count is not None:
        if count > 0:
            status_parts.append(f"[success]{count} events found[/success]")
        else:
            status_parts.append(f"[warning]{count} events found[/warning]")

    if error:
        status_parts.append(f"[error]Error[/error]")
    elif data:
        status_parts.append(f"[info]Results available[/info]")

    console.print(f"🗄️  [bold]Database Tool[/bold] → {' → '.join(status_parts)}")

    if data:
        logger.debug(f"Database results: {str(data)[:200]}...")

    # Build status string for return
    status_parts = ["Tool: database"]
    if query_name:
        status_parts.append(f"Query Name: {query_name}")
    if query:
        if isinstance(query, dict):
            query_copy = query.copy()
            query_copy.pop("project_id", None)
            status_parts.append(f"Query: {query_copy}")
        else:
            status_parts.append(f"Query: '{query}'")
    if count is not None:
        status_parts.append(f"Events: {count} found")
    if error:
        status_parts.append(f"ERROR: {error}")

    status_parts.extend([
        "Results:",
        str(data),
        "",
        "NOTE: Store relevant search results in sutra memory if you are not making "
        "changes in current iteration or want this code for later use, as search "
        "results will not persist to next iteration."
    ])

    return "\n".join(status_parts).rstrip()


def _build_semantic_search_status(event: Dict[str, Any]) -> str:
    """Build status for semantic search tool."""
    query = event.get("query")
    count = event.get("count") or event.get("total_nodes")
    batch_info = event.get("batch_info", {})
    error = event.get("error")
    data = event.get("data")

    # Minimal format console output
    status_parts = []

    if count is not None:
        if batch_info and (delivered := batch_info.get("delivered_count", 0)) > 0:
            remaining = batch_info.get("remaining_count", 0)
            start_node = count - remaining - delivered + 1
            end_node = count - remaining
            status_parts.append(f"[success]{count} nodes (showing {start_node}-{end_node})[/success]")
        else:
            if count > 0:
                status_parts.append(f"[success]{count} nodes found[/success]")
            else:
                status_parts.append(f"[warning]{count} nodes found[/warning]")

    if error:
        status_parts.append(f"[error]Error[/error]")
    elif data:
        status_parts.append(f"[info]Results available[/info]")

    console.print(f"🧠 [bold]Semantic Search[/bold] → {' → '.join(status_parts)}")

    if data:
        logger.debug(f"Semantic search results: {str(data)[:200]}...")

    # Build status string for return
    status_parts = ["Tool: semantic_search"]

    if query and query != "fetch_next_code":
        status_parts.append(f"Query: '{query}'")

    if count is not None:
        if batch_info and (delivered := batch_info.get("delivered_count", 0)) > 0:
            remaining = batch_info.get("remaining_count", 0)
            start_node = count - remaining - delivered + 1
            end_node = count - remaining
            status_parts.append(
                f"Found {count} nodes from semantic search. "
                f"Showing nodes {start_node}-{end_node} of {count}"
            )
        else:
            status_parts.append(f"Found {count} nodes from semantic search")

    if error:
        status_parts.append(f"ERROR: {error}")

    if data:
        status_parts.extend([
            "Results:",
            str(data)
        ])

    status_parts.extend([
        "",
        "NOTE: Store relevant search results in sutra memory if you are not making "
        "changes in current iteration or want this code for later use, as search "
        "results will not persist to next iteration."
    ])

    return "\n".join(status_parts).rstrip()


def _build_list_files_status(event: Dict[str, Any]) -> str:
    """Build status for list_files tool."""
    directory = event.get("directory")
    count = event.get("count")
    error = event.get("error")
    data = event.get("data")

    # Minimal format console output
    status_parts = []

    if count is not None:
        if count > 0:
            status_parts.append(f"[success]{count} files found[/success]")
        else:
            status_parts.append(f"[warning]{count} files found[/warning]")

    if error:
        status_parts.append(f"[error]Error[/error]")
    elif data:
        status_parts.append(f"[info]Results available[/info]")

    console.print(f"📁 [bold]List Files[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: list_files"]

    if directory:
        status_parts.append(f"Directory: {directory}")
    if count is not None:
        status_parts.append(f"Files: {count} found")
    if error:
        status_parts.append(f"ERROR: {error}")
    if data:
        status_parts.extend([
            "Results:",
            str(data)
        ])

    return "\n".join(status_parts).rstrip()


def _build_keyword_search_status(event: Dict[str, Any]) -> str:
    """Build status for keyword_search tool."""
    keyword = event.get("keyword")
    file_paths = event.get("file_paths")
    matches_found = event.get("matches_found")
    error = event.get("error")
    data = event.get("data")

    # Minimal format console output
    status_parts = []

    if keyword:
        status_parts.append(f"[value]'{keyword}'[/value]")

    if matches_found is not None:
        if matches_found:
            status_parts.append(f"[success]Matches found[/success]")
        else:
            status_parts.append(f"[warning]No matches[/warning]")

    if error:
        status_parts.append(f"[error]Error[/error]")
    elif data:
        status_parts.append(f"[info]Results available[/info]")

    console.print(f"🔍 [bold]Keyword Search[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: keyword_search"]

    if keyword:
        status_parts.append(f"Keyword: '{keyword}'")
    if file_paths:
        if isinstance(file_paths, list) and file_paths:
            paths_str = ", ".join(file_paths)
            status_parts.append(f"Searched in: {paths_str}")
        elif isinstance(file_paths, str):
            status_parts.append(f"Searched in: {file_paths}")
    if matches_found is not None:
        matches_status = "Found" if matches_found else "Not Found"
        status_parts.append(f"Matches Status: '{matches_status}'")
    if error:
        status_parts.append(f"ERROR: {error}")
    if data:
        status_parts.extend([
            "Results:",
            str(data)
        ])

    return "\n".join(status_parts).rstrip()


def _build_completion_status(event: Dict[str, Any], agent: Agent) -> str:
    """Build status for completion tool based on agent_name."""
    error = event.get("error")
    agent_name = event.get("agent_name")

    if error:
        # Error case
        console.print(f"❌ [bold red]Completion Error:[/bold red] {error}")
        return f"Tool: attempt_completion\nERROR: {error}"

    # Use agent_name to determine completion type
    if agent_name == Agent.ROADMAP:
        return _build_roadmap_completion_status(event)
    else:
        return _build_simple_completion_status(event)


def _build_simple_completion_status(event: Dict[str, Any]) -> str:
    """Build status for simple completion."""
    result = event.get("data", {}).get("result", "Task completed")

    console.print(f"✅ [bold green]Completion:[/bold green] {result}")

    status_parts = [
        "Tool: attempt_completion",
        f"Result: {result}"
    ]

    return "\n".join(status_parts)


def _build_roadmap_completion_status(event: Dict[str, Any]) -> str:
    """Build status for roadmap completion with enhanced display showing all BAML structure details."""
    data = event.get("data", {})
    summary = data.get("summary", "")
    projects = data.get("projects", [])
    projects_count = len(projects)

    # Enhanced roadmap completion display - COMPREHENSIVE DETAIL PRINTING
    console.print(f"🗺️  [bold blue]Roadmap Summary:[/bold blue] {summary}")
    console.print(f"📊 [bold cyan]Total Projects:[/bold cyan] {projects_count}")
    console.print()

    # Display every single detail from each project
    for i, project in enumerate(projects, 1):
        # Extract ALL project fields
        project_name = project.get("project_name", f"Project {i}")
        project_path = project.get("project_path", "")
        impact_level = project.get("impact_level", "Unknown")
        reasoning = project.get("reasoning", "")
        changes = project.get("changes", [])
        impl_notes = project.get("implementation_notes", "")

        # Color code impact level
        impact_color = {
            ImpactLevel.High: "red",
            ImpactLevel.Medium: "yellow",
            ImpactLevel.Low: "green",
            ImpactLevel.NoImpact: "dim"
        }.get(impact_level, "white")

        # PROJECT HEADER - Show all project fields
        console.print(f"━━━ PROJECT {i}: [bold]{project_name}[/bold] ━━━")
        console.print(f"    📁 Path: [dim]{project_path or 'Not specified'}[/dim]")
        console.print(f"    📊 Impact Level: [{impact_color}]{impact_level}[/{impact_color}]")
        console.print(f"    📝 Reasoning: [italic]{reasoning or 'No reasoning provided'}[/italic]")
        console.print(f"    📋 Total File Changes: {len(changes)}")

        if impl_notes:
            console.print(f"    💡 Implementation Notes: [dim]{impl_notes}[/dim]")
        else:
            console.print(f"    💡 Implementation Notes: [dim]None provided[/dim]")

        # FILE CHANGES - Show every detail for each file
        if changes:
            console.print(f"    📄 File Changes:")
            for j, change in enumerate(changes, 1):
                file_path = change.get("file_path", "Unknown file")
                operation = change.get("operation", "Unknown operation")
                instructions = change.get("instructions", [])

                # Color code operation
                operation_color = {
                    FileOperation.Create: "green",
                    FileOperation.Modify: "yellow",
                    FileOperation.Delete: "red"
                }.get(operation, "white")

                console.print(f"        {j}. [{operation_color}]{operation.upper()}[/{operation_color}] → {file_path}")
                console.print(f"           📝 Instructions: {len(instructions)} change(s)")

                # CHANGE INSTRUCTIONS - Show every field for each instruction
                for k, instruction in enumerate(instructions, 1):
                    description = instruction.get("description", "")
                    current_state = instruction.get("current_state", "")
                    target_state = instruction.get("target_state", "")
                    start_line = instruction.get("start_line")
                    end_line = instruction.get("end_line")
                    additional_notes = instruction.get("additional_notes", "")

                    console.print(
                        f"             {k}. [bold cyan]Change Description:[/bold cyan] {description or 'No description'}")

                    # Line numbers
                    if start_line is not None:
                        line_info = f"Line {start_line}"
                        if end_line is not None and end_line != start_line:
                            line_info += f" to {end_line}"
                        console.print(f"                📍 Location: {line_info}")
                    else:
                        console.print(f"                📍 Location: Not specified")

                    # Current state
                    if current_state:
                        console.print(f"                🔴 Current: {current_state}")
                    else:
                        console.print(f"                🔴 Current: Not specified")

                    # Target state
                    if target_state:
                        console.print(f"                🟢 Target: {target_state}")
                    else:
                        console.print(f"                🟢 Target: Not specified")

                    # Additional notes
                    if additional_notes:
                        console.print(f"                💡 Notes: {additional_notes}")
                    else:
                        console.print(f"                💡 Notes: None")

                    console.print()  # Space between instructions
        else:
            console.print(f"    📄 File Changes: [dim]No changes specified[/dim]")

        console.print()  # Space between projects

    # Build comprehensive status string for return
    status_parts = [
        "Tool: attempt_completion",
        f"Summary: {summary}",
        f"Projects analyzed: {projects_count}",
        "\nDetailed Projects:"
    ]

    for i, project in enumerate(projects, 1):
        project_name = project.get("project_name", f"Project {i}")
        project_path = project.get("project_path", "")
        impact_level = project.get("impact_level", "Unknown")
        reasoning = project.get("reasoning", "")
        changes = project.get("changes", [])

        status_parts.extend([
            f"\n  {i}. {project_name} ({project_path})",
            f"     Impact: {impact_level}",
            f"     Reasoning: {reasoning}",
            f"     Files to change: {len(changes)}"
        ])

        for j, change in enumerate(changes, 1):
            file_path = change.get("file_path", "")
            operation = change.get("operation", "")
            instructions = change.get("instructions", [])

            status_parts.append(f"       {j}. {operation} {file_path} ({len(instructions)} instructions)")

    return "\n".join(status_parts)

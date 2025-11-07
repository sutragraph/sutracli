from os import error
from typing import Any, Dict

from loguru import logger
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from baml_client.types import Agent
from utils.console import console


def build_tool_status(
    tool_name: str, event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Helper to build tool status dictionary."""
    match tool_name:
        case "database":
            return _build_database_status(event, agent, tool_params)
        case "semantic_search":
            return _build_semantic_search_status(event, agent, tool_params)
        case "list_files":
            return _build_list_files_status(event, agent, tool_params)
        case "search_keyword":
            return _build_search_keyword_status(event, agent, tool_params)
        case "edit_file":
            return _build_edit_file_status(event, agent, tool_params)
        case "diagnostics":
            return _build_diagnostics_status(event, agent, tool_params)
        case "attempt_completion":
            return _build_completion_status(event, agent, tool_params)
        case "terminal":
            return _build_terminal_status(event, agent, tool_params)
        case _:
            return f"Unknown tool name '{tool_name}' with parameters {tool_params}"


def _build_database_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Helper to build database status dictionary."""
    query_name = event.get("query_name")
    query = event.get("query")
    count = event.get("count") or event.get("total_events") or event.get("total_nodes")
    error = event.get("error")
    data = event.get("data", "")

    # Minimal format console output
    status_parts = []

    if query_name:
        status_parts.append(f"[value]{query_name}[/value]")

    if error:
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")
    elif count is not None:
        if count > 0:
            status_parts.append(f"[success]{count} results found[/success]")
        else:
            status_parts.append(f"[warning]No results found[/warning]")

    console.print(f"🗄️  [bold]Database Tool[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: database"]
    status_parts.append(f"Parameters used: {tool_params}")

    if error:
        status_parts.append(f"ERROR: {error}")

    if data:
        status_parts.extend(["Results:", str(data)])

    status_parts.append("")

    # Add agent-specific notes
    if agent == Agent.CrossIndexing:
        status_parts.append("")
    else:
        status_parts.append(
            "NOTE: Store relevant search results in sutra memory if you are not making changes in current iteration or fetching more chunks or using new query or want this code for later use, as search results will not persist to next iteration."
        )

    return "\n".join(status_parts).rstrip()


def _build_semantic_search_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
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
            status_parts.append(
                f"[success]{count} nodes (showing {start_node}-{end_node})[/success]"
            )
        else:
            if count > 0:
                status_parts.append(f"[success]{count} nodes found[/success]")
            else:
                status_parts.append(f"[warning]{count} nodes found[/warning]")

    if error:
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")

    console.print(f"🧠 [bold]Semantic Search[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: semantic_search"]
    status_parts.append(f"Parameters used: {tool_params}")

    if query and query != "fetch_next_chunk":
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
        status_parts.extend(["Results:", str(data)])

    status_parts.append("")

    # Add agent-specific notes
    if agent == Agent.CrossIndexing:
        status_parts.append("")
    else:
        status_parts.append(
            "NOTE: Store relevant search results in sutra memory if you are not making changes in current iteration or fetching more chunks or using new query or want this code for later use, as search results will not persist to next iteration."
        )

    return "\n".join(status_parts).rstrip()


def _build_list_files_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
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
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")

    console.print(f"📁 [bold]List Files[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: list_files"]
    status_parts.append(f"Parameters used:\n {tool_params}")

    if directory:
        status_parts.append(f"Directory: {directory}")
    if count is not None:
        status_parts.append(f"Files: {count} found")
    if error:
        status_parts.append(f"ERROR: {error}")
    if data:
        status_parts.extend(["Results:", str(data)])

    # Add agent-specific notes for list_files
    if agent == Agent.CrossIndexing:
        status_parts.append(
            "NOTE: Store relevant file/folder information in Sutra memory's history section for connection analysis, as directory listings will not persist in next iterations.",
        )

    return "\n".join(status_parts).rstrip()


def _build_search_keyword_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Build status for search_keyword tool."""
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
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")

    console.print(f"🔍 [bold]Keyword Search[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: search_keyword"]
    status_parts.append(f"Parameters used:\n {tool_params}")

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
        status_parts.extend(["Results:", str(data)])

    # Add agent-specific notes for search_keyword
    if agent == Agent.CrossIndexing:
        status_parts.append("")
    else:
        status_parts.append(
            "NOTE: Store relevant search results in sutra memory if you are not making changes in current iteration or fetching more chunks or using new query or want this code for later use, as search results will not persist to next iteration."
        )

    return "\n".join(status_parts).rstrip()


def _build_edit_file_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Build status for edit_file tool."""
    error = event.get("error")
    data = event.get("data", {})

    status_parts = []

    if error:
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")

    if data:
        original_path = data.get("original_path")
        diff = data.get("diff")

        if original_path:
            status_parts.append(f"[value]File Edited: {original_path}[/value]")

    status_parts = ["Tool: edit_file"]
    status_parts.append(f"Parameters used:\n {tool_params}")

    if data:
        original_path = data.get("original_path")
        new_text = data.get("new_text")
        old_text = data.get("old_text")
        diff = data.get("diff")

        if original_path:
            status_parts.append(f"File Edited Successfully: {original_path}")
        # if diff:
        #     status_parts.append("Diff:")
        #     status_parts.append(diff)

    if error:
        status_parts.append(f"ERROR: {error}")

    return "\n".join(status_parts).rstrip()


def _build_diagnostics_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Build status for diagnostics tool."""
    error = event.get("error")
    data = event.get("data", {})

    status_parts = []

    if error:
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")

    if data:
        file_path = data.get("file_path")
        count = data.get("count", 0)

        if file_path:
            status_parts.append(f"[value]Diagnostics for: {file_path}[/value]")
        status_parts.append(f"[value]Issues Found: {count}[/value]")

    status_parts = ["Tool: diagnostics"]
    status_parts.append(f"Parameters used:\n {tool_params}")

    if data:
        file_path = data.get("file_path")
        diagnostics = data.get("diagnostics", [])
        count = data.get("count", 0)

        if file_path:
            status_parts.append(f"File Analyzed: {file_path}")
        status_parts.append(f"Issues Found: {count}")
        if diagnostics:
            status_parts.append("Diagnostics:")
            for diag in diagnostics:
                status_parts.append(f"{diag}")

    if error:
        status_parts.append(f"ERROR: {error}")

    return "\n".join(status_parts).rstrip()


def _build_terminal_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Build status for terminal tool."""
    command = event.get("command")
    status = event.get("status")
    output = event.get("output")
    error = event.get("error")
    session_id = event.get("session_id")
    cwd = event.get("cwd")
    exit_code = event.get("exit_code")
    is_long_running = event.get("is_long_running", False)
    action = event.get("action", "execute")

    # Minimal format console output
    status_parts = []

    if command:
        status_parts.append(f"[value]'{command}'[/value]")

    if status == "success":
        if is_long_running:
            status_parts.append(f"[success]Started[/success]")
        else:
            status_parts.append(f"[success]Success[/success]")
    elif status == "error":
        status_parts.append(f"[error]Error[/error]")
    else:
        status_parts.append(f"[warning]{status}[/warning]")

    if error:
        status_parts.append(f"[error]Error:[/error]")
        status_parts.append(f"{error}")

    console.print(f"💻 [bold]Terminal[/bold] → {' → '.join(status_parts)}")

    # Build status string for return
    status_parts = ["Tool: terminal"]
    status_parts.append(f"Parameters used: {tool_params}")

    # if action:
    #     status_parts.append(f"Action: {action}")

    # if command:
    #     status_parts.append(f"Command: {command}")

    # if session_id:
    #     status_parts.append(f"Session ID: {session_id}")

    if cwd:
        status_parts.append(f"Working Directory: {cwd}")

    # if status:
    #     if is_long_running and status == "success":
    #         status_parts.append(f"Status: Process started successfully")
    #     else:
    #         status_parts.append(f"Status: {status}")

    if exit_code is not None:
        status_parts.append(f"Exit Code: {exit_code}")

    if error:
        status_parts.append(f"ERROR: {error}")

    if output:
        status_parts.extend(["Results:", output])

    return "\n".join(status_parts).rstrip()


def _build_completion_status(
    event: Dict[str, Any], agent: Agent, tool_params: Dict[str, Any]
) -> str:
    """Build status for completion tool based on agent_name."""
    error = event.get("error")
    is_simple = event.get("simple", False)

    if error:
        # Error case
        console.print(f"❌ [bold red]Completion Error:[/bold red] {error}")
        return f"Tool: attempt_completion\nERROR: {error}"

    # Use agent to determine completion type
    if agent == Agent.Roadmap and not is_simple:
        return _build_roadmap_completion_status(event)
    if agent == Agent.Developer:
        return _build_developer_completion_status(event)
    if agent == Agent.QAEngineer:
        return _build_qaengineer_completion_status(event)
    else:
        return _build_simple_completion_status(event)


def _build_simple_completion_status(event: Dict[str, Any]) -> str:
    """Build status for simple completion."""

    result = event.get("data", {}).get("result", "Task completed")

    # Create header
    header = Text("RESULT", style="bold cyan")

    # Create content
    content = Text(result, style="white")

    # Create panel
    completion_panel = Panel(
        content,
        title=header,
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )

    console.print(completion_panel)

    status_parts = ["Tool: attempt_completion", f"Result: {result}"]

    return "\n".join(status_parts)


def _build_roadmap_completion_status(event: Dict[str, Any]) -> str:
    """Build status for roadmap completion with detailed panel display."""

    data = event.get("data", {})
    summary = data.get("summary", "")
    projects = data.get("projects", []) or []

    # Main summary header
    console.print("[bold blue]Implementation Roadmap Generated[/bold blue]")
    if summary:
        console.print(f"[dim]{summary}[/dim]")
    console.print(f"[cyan]{len(projects)} projects ready for implementation[/cyan]")
    console.print()

    # Display each project in a beautiful panel
    for i, project in enumerate(projects, 1):
        project_name = project.get("project_name", f"Project {i}")
        project_path = project.get("project_path", "")
        impact_level = project.get("impact_level", "Unknown")
        reasoning = project.get("reasoning", "")
        changes = project.get("changes", [])
        implementation_plan = project.get("implementation_plan", [])

        # Impact level styling
        impact_colors = {
            "High": "red",
            "Medium": "yellow",
            "Low": "blue",
            "None": "dim",
        }
        impact_color = impact_colors.get(impact_level, "white")

        # Create project header
        project_header = Text()
        project_header.append(f"PROJECT {i}/{len(projects)}", style="bold cyan")
        project_header.append(f"\nPath: {project_path}", style="dim")
        project_header.append(f"\nImpact: ", style="dim")
        project_header.append(f"{impact_level}", style=f"bold {impact_color}")

        # Build content sections using Rich Text
        content_elements = []

        # Reasoning section
        if reasoning:
            reasoning_text = Text()
            reasoning_text.append("Reasoning: ", style="bold")
            reasoning_text.append(reasoning)
            content_elements.append(reasoning_text)
            content_elements.append(Text())

        # Implementation notes
        if len(implementation_plan):
            impl_text = Text()
            impl_text.append("Implementation Plan: ", style="bold")
            for idx, item in enumerate(implementation_plan, 1):
                impl_text.append(f"\n   {idx}. {item}")
            content_elements.append(impl_text)
            content_elements.append(Text())

        # File changes summary
        if changes:
            file_header = Text()
            file_header.append("File Changes: ", style="bold")
            file_header.append(f"{len(changes)} files", style="cyan")
            content_elements.append(file_header)
            content_elements.append(Text())

            for j, change in enumerate(changes, 1):
                file_path = change.get("file_path", "Unknown")
                operation = change.get("operation", "Unknown")
                instructions = change.get("instructions", [])

                # File operation line
                file_line = Text()
                file_line.append(f"   {j}. ", style="bold")
                file_line.append(f"{operation.upper()}", style="bold")
                file_line.append(f" → {file_path}")
                content_elements.append(file_line)

                # Show detailed instructions for each file
                if instructions:
                    for k, instruction in enumerate(instructions, 1):
                        description = instruction.get(
                            "description", "No description provided"
                        )
                        guidance = instruction.get("guidance", "")
                        integration_notes = instruction.get("integration_notes", "")

                        # Description
                        desc_text = Text()
                        desc_text.append("     • ", style="bold")
                        desc_text.append(description)
                        content_elements.append(desc_text)

                        # Guidance
                        if guidance:
                            guidance_text = Text("     ")
                            guidance_text.append("Guidance: ", style="bold")
                            guidance_text.append(guidance)
                            content_elements.append(guidance_text)

                        # Integration notes
                        if integration_notes:
                            integration_text = Text("     ")
                            integration_text.append("Integration Notes: ", style="bold")
                            integration_text.append(integration_notes)
                            content_elements.append(integration_text)

                        # Add spacing between instructions if there are multiple
                        if k < len(instructions):
                            content_elements.append(Text())
                else:
                    no_instr_text = Text(
                        "     No detailed instructions provided", style="dim"
                    )
                    content_elements.append(no_instr_text)
        else:
            no_changes_text = Text()
            no_changes_text.append("File Changes: ", style="bold")
            no_changes_text.append("No changes needed", style="dim")
            content_elements.append(no_changes_text)

        # Contracts summary
        contracts = project.get("integration_contracts", [])
        if contracts:
            content_elements.append(Text())  # Add spacing
            contract_header = Text()
            contract_header.append("Integration Contracts: ", style="bold")
            contract_header.append(f"{len(contracts)} contracts", style="magenta")
            content_elements.append(contract_header)
            content_elements.append(Text())

            for j, contract in enumerate(contracts, 1):
                contract_id = contract.get("contract_id", "Unknown")
                description = contract.get("description", "")
                related_projects = contract.get("related_projects", [])
                specifications = contract.get("specifications", "")

                # Contract header line
                contract_line = Text()
                contract_line.append(f"   {j}. ", style="bold")
                contract_line.append("CONTRACT", style="bold magenta")
                contract_line.append(f" → {contract_id}")
                content_elements.append(contract_line)

                # Description
                if description:
                    desc_text = Text("     ")
                    desc_text.append("Description: ", style="bold")
                    desc_text.append(description)
                    content_elements.append(desc_text)

                # Related projects
                if related_projects:
                    projects_text = Text("     ")
                    projects_text.append("Related Projects: ", style="bold")
                    projects_text.append(", ".join(related_projects))
                    content_elements.append(projects_text)

                # Specifications
                if specifications:
                    spec_text = Text("     ")
                    spec_text.append("Specifications: ", style="bold")
                    spec_text.append(specifications)
                    content_elements.append(spec_text)

                # Add spacing between contracts if there are multiple
                if j < len(contracts):
                    content_elements.append(Text())

        # Create panel content using Group for multiple Text elements
        panel_content = Group(*content_elements)

        # Create the project panel
        project_panel = Panel(
            panel_content,
            title=project_header,
            title_align="left",
            border_style=impact_color,
            padding=(1, 2),
        )

        console.print(project_panel)
        console.print()

    # Build comprehensive status string for return
    status_parts = [
        "Tool: attempt_completion",
        f"Summary: {summary}",
    ]
    logger.debug("Roadmap completion status built successfully.")
    return "\n".join(status_parts)


# class DeveloperCompletionParams {
#   give_up bool @description("True if abandoning the task due to blockers or missing information; false if successfully completing the request")
#   result string @description("A short summary of the changes you have made to the files or clarification on giving up")
# }


def _build_developer_completion_status(event: Dict[str, Any]) -> str:
    """Build status for developer completion with panel display."""
    data = event.get("data", {})
    result = data.get("result", "")
    give_up = data.get("give_up", False)

    # Determine status styling based on give_up flag
    if give_up:
        status_icon = "⚠️"
        status_title = "TASK ABANDONED"
        status_style = "bold yellow"
        border_style = "yellow"
        status_text = f"[yellow]Reason: {result}[/yellow]"
    else:
        status_icon = "✅"
        status_title = "TASK COMPLETE"
        status_style = "bold green"
        border_style = "green"
        status_text = f"[green]{result}[/green]"

    # Create header
    header = Text(status_title, style=status_style)

    # Create content
    content = Text(status_text)

    # Create panel
    completion_panel = Panel(
        content,
        title=header,
        title_align="left",
        border_style=border_style,
        padding=(1, 2),
    )

    console.print(status_icon, completion_panel)

    # Build status string for return
    status_parts = ["Tool: attempt_completion"]
    status_parts.append(f"Result: {result}")

    return "\n".join(status_parts)


def _build_qaengineer_completion_status(event: Dict[str, Any]) -> str:
    """Build status for QA engineer completion with detailed panel display."""
    data = event.get("data", {})
    result = data.get("result", "")
    failed_tests = data.get("failed_tests", [])

    # Determine status based on failed tests
    if failed_tests:
        status_icon = "❌"
        status_title = "TESTS FAILED"
        status_style = "bold red"
        border_style = "red"
        failed_count = len(failed_tests)
        status_subtitle = (
            f"[red]{failed_count} test{'s' if failed_count != 1 else ''} failed[/red]"
        )
    else:
        status_icon = "✅"
        status_title = "TESTS PASSED"
        status_style = "bold green"
        border_style = "green"
        status_subtitle = "[green]All tests completed successfully[/green]"

    # Main status header
    console.print(status_icon, f"[bold]{status_title}[/bold]")
    console.print(status_subtitle)
    console.print()

    # Test summary
    if result:
        console.print(f"[dim]{result}[/dim]")
        console.print()

    # Display failed tests details if any
    if failed_tests:
        console.print(f"[bold red]Failed Test Details:[/bold red]")
        console.print()

        for i, failed_test in enumerate(failed_tests, 1):
            test_name = failed_test.get("test_name", f"Test {i}")
            test_details = failed_test.get("test_details", "No details provided")

            # Create test header
            test_header = Text()
            test_header.append(f"FAILED TEST {i}/{len(failed_tests)}", style="bold red")
            test_header.append(f"\nTest: {test_name}", style="dim")

            # Create test details content
            content_elements = []

            # Test details
            details_text = Text()
            details_text.append("Details: ", style="bold")
            details_text.append(test_details)
            content_elements.append(details_text)

            # Create panel for this failed test
            panel_content = Group(*content_elements)

            test_panel = Panel(
                panel_content,
                title=test_header,
                title_align="left",
                border_style="red",
                padding=(1, 2),
            )

            console.print(test_panel)
            console.print()

    # Build status string for return
    status_parts = ["Tool: attempt_completion"]
    status_parts.append(f"Result: {result}")

    if failed_tests:
        status_parts.append(f"Failed Tests: {len(failed_tests)}")
        for i, failed_test in enumerate(failed_tests, 1):
            test_name = failed_test.get("test_name", f"Test {i}")
            test_details = failed_test.get("test_details", "No details provided")
            status_parts.append(f"  Test {i}: {test_name}")
            status_parts.append(f"    Details: {test_details}")

    return "\n".join(status_parts)

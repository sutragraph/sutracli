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
        case "attempt_completion":
            return _build_completion_status(event, agent, tool_params)
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
    if agent == Agent.ROADMAP and not is_simple:
        return _build_roadmap_completion_status(event)
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
                        current_state = instruction.get("current_state", "")
                        target_state = instruction.get("target_state", "")
                        start_line = instruction.get("start_line")
                        end_line = instruction.get("end_line")
                        additional_notes = instruction.get("additional_notes", "")

                        # Description
                        desc_text = Text()
                        desc_text.append("     • ", style="bold")
                        desc_text.append(description)
                        content_elements.append(desc_text)

                        # Line number information
                        if start_line is not None:
                            line_text = Text("     ")
                            if end_line is not None and end_line != start_line:
                                line_text.append("Lines: ", style="bold")
                                line_text.append(f"{start_line}-{end_line}")
                            else:
                                line_text.append("Line: ", style="bold")
                                line_text.append(str(start_line))
                            content_elements.append(line_text)

                        # Current state
                        if current_state:
                            current_text = Text("     ")
                            current_text.append("Current: ", style="bold")
                            current_text.append(current_state)
                            content_elements.append(current_text)

                        # Target state
                        if target_state:
                            target_text = Text("     ")
                            target_text.append("Target: ", style="bold")
                            target_text.append(target_state)
                            content_elements.append(target_text)

                        # Additional notes
                        if additional_notes:
                            notes_text = Text("     ")
                            notes_text.append("Notes: ", style="bold")
                            notes_text.append(additional_notes)
                            content_elements.append(notes_text)

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
        contracts = project.get("contracts", [])
        if contracts:
            content_elements.append(Text())  # Add spacing
            contract_header = Text()
            contract_header.append("Integration Contracts: ", style="bold")
            contract_header.append(f"{len(contracts)} contracts", style="magenta")
            content_elements.append(contract_header)
            content_elements.append(Text())

            for j, contract in enumerate(contracts, 1):
                contract_id = contract.get("contract_id", "Unknown")
                contract_type = contract.get("contract_type", "Unknown")
                contract_name = contract.get("name", "Unnamed Contract")
                description = contract.get("description", "")
                role = contract.get("role", "")
                interface = contract.get("interface", {})
                authentication_required = contract.get("authentication_required", False)

                # Contract header line
                contract_line = Text()
                contract_line.append(f"   {j}. ", style="bold")
                contract_line.append(f"{contract_type.upper()}", style="bold magenta")
                contract_line.append(f" → {contract_name}")
                content_elements.append(contract_line)

                # Contract ID and Role
                id_text = Text("     ")
                id_text.append("ID: ", style="bold")
                id_text.append(contract_id, style="magenta")
                if role:
                    id_text.append(" | Role: ", style="bold")
                    if role == "provider":
                        role_color = "green"
                        role_label = "PROVIDER"
                    elif role == "consumer":
                        role_color = "blue"
                        role_label = "CONSUMER"
                    elif role == "both":
                        role_color = "yellow"
                        role_label = "BOTH (Proxy/Intermediary)"
                    else:
                        role_color = "white"
                        role_label = role.upper()
                    id_text.append(role_label, style=f"bold {role_color}")
                content_elements.append(id_text)

                # Description
                if description:
                    desc_text = Text("     ")
                    desc_text.append("Description: ", style="bold")
                    desc_text.append(description)
                    content_elements.append(desc_text)

                # Interface details
                if interface:
                    interface_text = Text("     ")
                    interface_text.append("Interface: ", style="bold")
                    interface_parts = []
                    for key, value in interface.items():
                        interface_parts.append(f"{key}={value}")
                    interface_text.append(", ".join(interface_parts))
                    content_elements.append(interface_text)

                # Authentication
                if authentication_required:
                    auth_text = Text("     ")
                    auth_text.append("Authentication: ", style="bold")
                    auth_text.append("Required", style="red")
                    content_elements.append(auth_text)

                # Input/Output formats (simplified for display)
                input_format = contract.get("input_format", [])
                if input_format:
                    input_text = Text("     ")
                    input_text.append("Input: ", style="bold")
                    input_fields = []
                    for field in input_format:
                        field_name = field.get("name", "")
                        field_type = field.get("type", "")
                        required = field.get("required", False)
                        req_marker = "*" if required else ""
                        input_fields.append(f"{field_name}: {field_type}{req_marker}")
                    input_text.append(", ".join(input_fields))  #
                    content_elements.append(input_text)

                output_format = contract.get("output_format", [])
                if output_format:
                    output_text = Text("     ")
                    output_text.append("Output: ", style="bold")
                    output_fields = []
                    for field in output_format:
                        field_name = field.get("name", "")
                        field_type = field.get("type", "")
                        output_fields.append(f"{field_name}: {field_type}")
                    output_text.append(", ".join(output_fields))
                    content_elements.append(output_text)

                # Error codes
                error_codes = contract.get("error_codes", [])
                if error_codes:
                    error_text = Text("     ")
                    error_text.append("Error Codes: ", style="bold")
                    error_text.append(", ".join(error_codes))
                    content_elements.append(error_text)

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

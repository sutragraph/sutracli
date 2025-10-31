"""Utility functions for roadmap processing."""

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger

from src.agent_management.types.agent import AgentData


def convert_roadmap_to_prompts(data: Dict[str, Any]) -> list:
    """Convert roadmap data to project prompts format.

    Args:
        data: The roadmap data containing projects and summary

    Returns:
        List of project prompts with 'prompt' and 'project_path' keys
    """
    logger.debug("Converting roadmap data to project prompts...")
    projects = data.get("projects", [])

    # Ensure projects is a list and not None
    if projects is None:
        projects = []

    project_prompts = []

    for project in projects:
        project_name = project.get("project_name", "")
        project_path = project.get("project_path", "")
        impact_level = project.get("impact_level", "Medium")
        reasoning = project.get("reasoning", "")
        changes = project.get("changes", [])
        contracts = project.get("integration_contracts", [])
        implementation_plan = project.get("implementation_plan", [])

        # Build the prompt string
        prompt_parts = []

        # Add header
        prompt_parts.append(f"# Project Modification Request: {project_name}")
        prompt_parts.append(f"Project Path: {project_path}")
        prompt_parts.append(f"Impact Level: {impact_level}")
        prompt_parts.append("")

        # Add reasoning
        if reasoning:
            prompt_parts.append("## Reasoning")
            prompt_parts.append(str(reasoning))
            prompt_parts.append("")

        # Add file changes
        if changes:
            prompt_parts.append("## File Changes Required")
            prompt_parts.append("")

            for i, file_change in enumerate(changes, 1):
                file_path = file_change.get("file_path", "")
                operation = file_change.get("operation", "modify")
                instructions = file_change.get("instructions", [])

                prompt_parts.append(f"### {i}. File: {file_path}")
                prompt_parts.append(f"Operation: {operation}")
                prompt_parts.append("")

                if instructions:
                    prompt_parts.append("Instructions:")
                    for j, instruction in enumerate(instructions, 1):
                        description = instruction.get("description", "")
                        guidance = instruction.get("guidance", "")
                        integration_notes = instruction.get("integration_notes", "")

                        prompt_parts.append(f"{j}. Change: {str(description)}")

                        if guidance:
                            prompt_parts.append(f"   Guidance: {str(guidance)}")

                        if integration_notes:
                            prompt_parts.append(
                                f"   Integration Notes: {str(integration_notes)}"
                            )

                        prompt_parts.append("")

                prompt_parts.append("")

        # Add contracts
        if contracts:
            prompt_parts.append("## Integration Contracts")
            prompt_parts.append("")
            prompt_parts.append(
                "The following contracts define the interfaces this project must implement or consume:"
            )
            prompt_parts.append("")

            for i, contract in enumerate(contracts, 1):
                contract_id = contract.get("contract_id", "")
                description = contract.get("description", "")
                related_projects = contract.get("related_projects", [])
                specifications = contract.get("specifications", "")

                prompt_parts.append(f"### {i}. Integration Contract")
                prompt_parts.append(f"Contract ID: {contract_id}")

                if description:
                    prompt_parts.append(f"Description: {str(description)}")

                if related_projects:
                    prompt_parts.append(
                        f"Related Projects: {', '.join(related_projects)}"
                    )

                if specifications:
                    prompt_parts.append(f"Specifications: {str(specifications)}")

                prompt_parts.append("")

        # Add implementation notes
        if len(implementation_plan):
            prompt_parts.append("## Implementation Plan")
            prompt_parts.append("")
            for item in implementation_plan:
                prompt_parts.append(f"- {item}")
            prompt_parts.append("")

        # Add final instructions
        prompt_parts.append("## Instructions")
        prompt_parts.append(
            "Please implement the changes described above according to the specifications."
        )
        prompt_parts.append(
            "Ensure that all modifications maintain code quality and follow best practices."
        )
        prompt_parts.append(
            "For contracts marked as 'provider', implement the interface. For contracts marked as 'consumer', integrate with the existing interface."
        )

        # Add the important consistency instruction
        prompt_parts.append("")
        prompt_parts.append(
            "Important: Maintain strict naming consistency - use the exact same function names, API endpoints, contract identifiers, variable names, and method signatures as specified in the original query and requirements above."
        )

        # Join all parts into a single prompt - ensure all items are strings
        def flatten_to_strings(items):
            """Recursively flatten any nested structures to strings."""
            result = []
            for item in items:
                if isinstance(item, list):
                    # Recursively flatten nested lists
                    result.extend(flatten_to_strings(item))
                elif isinstance(item, (dict, tuple)):
                    # Convert complex types to string representation
                    result.append(str(item))
                else:
                    # Convert to string if it's not already
                    result.append(str(item))
            return result

        string_parts = flatten_to_strings(prompt_parts)
        full_prompt = "\n".join(string_parts)

        logger.debug(f"Generated prompt for project {project_name}:\n{full_prompt}")
        # Create project prompt entry
        project_prompts.append(
            {
                "prompt": full_prompt,
                "project_path": project_path,
            }
        )

    return project_prompts


def verify_roadmap_file_paths(roadmap_result: Any) -> Dict[str, Any]:
    """Verify that file paths for modify and delete operations exist.

    Args:
        roadmap_result: RoadmapCompletionParams object with roadmap data

    Returns:
        Dict with 'valid' (bool), 'feedback' (str) if validation fails, and 'non_existing_paths' list
    """
    try:
        if not roadmap_result:
            logger.warning("No roadmap result available to verify")
            return {"valid": True}

        roadmap_data = roadmap_result.model_dump()
        projects = roadmap_data.get("projects", [])
        non_existing_paths = []

        for project in projects:
            project_path = project.get("project_path", "")
            changes = project.get("changes", [])

            # Determine project root directory
            if os.path.isabs(project_path) and os.path.exists(project_path):
                project_root = project_path
            else:
                # Try relative to current working directory
                clean_path = (
                    project_path[1:] if project_path.startswith("/") else project_path
                )
                potential_root = Path.cwd() / clean_path
                project_root = str(potential_root) if potential_root.exists() else None

            for change in changes:
                operation = change.get("operation", "")
                file_path = change.get("file_path", "")

                # Convert operation to string if it's an enum
                operation_str = str(operation).lower()
                if hasattr(operation, "value"):
                    operation_str = operation.value.lower()

                # Only check modify and delete operations
                if operation_str in ["modify", "delete"]:
                    if project_root:
                        full_file_path = os.path.join(project_root, file_path)
                    else:
                        full_file_path = file_path

                    # Check if file exists
                    if not os.path.exists(full_file_path):
                        non_existing_paths.append(
                            {
                                "project": project.get("project_name", "Unknown"),
                                "project_path": project_path,
                                "file_path": file_path,
                                "operation": operation,
                                "full_path": full_file_path,
                            }
                        )
                    else:
                        logger.debug(f"File exists and verified: {full_file_path}")

        if non_existing_paths:
            # Create feedback message for non-existing paths
            feedback_message = "The following file paths provided for modify or delete operations do not exist:\n\n"

            for i, path_info in enumerate(non_existing_paths, 1):
                feedback_message += f"{i}. Project: {path_info['project']}\n"
                feedback_message += f"   Operation: {path_info['operation']}\n"
                feedback_message += f"   File path: {path_info['file_path']}\n"
                feedback_message += f"   Full path: {path_info['full_path']}\n"
                feedback_message += f"   Status: FILE DOES NOT EXIST\n\n"

            feedback_message += "Please provide correct file paths that exist in the project before proceeding with any modification or deletion operations. "
            feedback_message += "Make sure to verify the file paths are correct and the files actually exist in the specified locations."

            return {
                "valid": False,
                "feedback": feedback_message,
                "non_existing_paths": non_existing_paths,
            }

        return {"valid": True}

    except Exception as e:
        logger.error(f"Error during file path verification: {e}")
        # If verification fails, assume paths are valid to avoid blocking
        return {"valid": True}


def format_feedback_section(feedback: str, roadmap_result: Any) -> str:
    """Format feedback section with user feedback and generated roadmap prompts.

    Args:
        feedback: User feedback text
        roadmap_result: RoadmapCompletionParams object with roadmap data

    Returns:
        Formatted feedback section string
    """
    try:
        if not roadmap_result:
            logger.warning("No roadmap result available to format feedback")
            return f"FEEDBACK SECTION: \nUSER FEEDBACK: {feedback}\n"

        project_prompts = convert_roadmap_to_prompts(roadmap_result.model_dump())

        feedback_section = "FEEDBACK SECTION: \n"
        feedback_section += f"USER FEEDBACK: {feedback}\n\n"

        feedback_section += (
            f"GENERATED PROJECT ROADMAPS ({len(project_prompts)} projects):\n\n"
        )

        for i, project_prompt in enumerate(project_prompts, 1):
            feedback_section += f"=== PROJECT {i} ROADMAP ===\n"
            feedback_section += (
                f"Project Path: {project_prompt.get('project_path', 'Unknown')}\n\n"
            )
            feedback_section += project_prompt.get("prompt", "No prompt available")
            feedback_section += "\n\n"

        logger.debug(
            f"Formatted feedback section with {len(project_prompts)} roadmap prompts"
        )

        return feedback_section

    except Exception as e:
        logger.error(f"Error formatting feedback section: {e}")
        return f"FEEDBACK SECTION: \nUSER FEEDBACK: {feedback}\n"


def format_feedback_tool_status(user_feedback: str) -> str:
    """Format feedback tool status message.

    Args:
        user_feedback: User feedback text

    Returns:
        Formatted feedback tool status string
    """
    feedback_status = "Tool: feedback_received\n"
    feedback_status += "Status: User provided feedback for roadmap improvement. The generated project roadmaps are stored in FEEDBACK section. Create new task for these improvements and work on it.\n"
    feedback_status += f"Feedback: {user_feedback}\n"

    return feedback_status


def separate_results_by_status(
    agents_result: List[AgentData],
) -> Tuple[List[AgentData], List[AgentData]]:
    """
    Separates spawned agent responses into successful and failed lists.

    Returns:
        Tuple[List[AgentData], List[AgentData]]: (successful_results, failed_results)
    """
    successful_results = []
    failed_results = []

    for agent_data in agents_result:
        if agent_data.success:
            successful_results.append(agent_data)
        else:
            failed_results.append(agent_data)

    return successful_results, failed_results


def format_agents_result(results: Tuple[List[AgentData], List[AgentData]]) -> str:
    context = ""

    successful_results, failed_results = results

    if successful_results:
        context += "SUCCESS:\n\n"
        for agent_data in successful_results:
            response = agent_data.get_last_message()
            message_value = list(response.values())[0] if response else "No response"
            context += f"{str(agent_data.project_path)}\n{message_value}"

    if failed_results:
        context += "FAILURE:\n\n"
        for agent_data in failed_results:
            response = agent_data.get_last_message()
            message_value = list(response.values())[0] if response else "No response"
            context += f"{str(agent_data.project_path)}\nreason: {message_value}"

    return context

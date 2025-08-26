from typing import Optional
from loguru import logger

def get_project_context_for_agent(agent_name, query: str) -> Optional[str]:
    """
    Get dynamic project context for an agent based on the query.

    Args:
        agent_name: The agent requesting project context
        query: User query to filter relevant projects

    Returns:
        Formatted project context string, or None if agent doesn't support it
    """
    try:
        # Use the shared project context function
        return get_project_context_for_query(query)

    except ImportError as e:
        logger.error(f"Failed to import agent '{agent_name.value}': {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting project context for '{agent_name.value}': {e}")
        return None


def inject_project_context(prompt_dict: dict, project_context: str) -> dict:
    """
    Inject project context into prompt dictionary.

    Args:
        prompt_dict: Base prompt dictionary with project_context key
        project_context: Generated project context to inject

    Returns:
        Prompt dictionary with project context injected
    """
    if "project_context" in prompt_dict:
        prompt_dict = prompt_dict.copy()  # Don't modify original
        prompt_dict["project_context"] = project_context
        return prompt_dict
    else:
        # If no project_context key found, log warning but return original
        logger.warning("No 'project_context' key found in prompt dictionary")
        return prompt_dict


def get_project_context_for_query(query: str) -> str:
    """
    Get dynamic project context based on the query.
    This is the shared implementation used by all agents that require project context.

    Args:
        query: User query to filter relevant projects

    Returns:
        Formatted project context string
    """
    try:
        # Import SQL connection directly
        from graph import ASTToSqliteConverter

        # Get all projects from database
        with ASTToSqliteConverter() as converter:
            projects = converter.connection.list_all_projects()

        if not projects:
            logger.warning("No projects found in database")
            return _get_default_project_context()

        # Convert project objects to dictionaries for easier processing
        project_dicts = []
        for project in projects:
            project_dict = {
                'name': project.name,
                'path': project.path,
                'description': getattr(project, 'description', 'No description available')
            }
            project_dicts.append(project_dict)

        # Select relevant projects using LLM
        relevant_projects = _select_relevant_projects(query, project_dicts)

        # Build project context from relevant projects
        return _build_project_context(relevant_projects)

    except Exception as e:
        logger.error(f"Error getting dynamic project context: {str(e)}")
        return _get_default_project_context()


def _get_default_project_context() -> str:
    """Get default project context when no query is provided or error occurs."""
    return """## Relevant Project Context

Working in general context. No specific projects identified for this query.

"""


def _select_relevant_projects(query: str, projects: list) -> list:
    """
    Use LLM to select projects relevant to the query.

    Args:
        query: User's query/request
        projects: List of all available projects

    Returns:
        List of relevant projects
    """
    # Build project summary for the LLM
    project_summaries = []
    for project in projects:
        name = project.get('name', 'Unknown')
        description = project.get('description', 'No description available')
        path = project.get('path', 'Unknown path')

        project_summaries.append(f"- **{name}**: {description} (Path: {path})")

    projects_text = "\n".join(project_summaries)

    # Create the selection prompt
    selection_prompt = f"""You are a project selection expert. Given a user query and a list of available projects, determine which projects are most relevant to the query.

USER QUERY:
{query}

AVAILABLE PROJECTS:
{projects_text}

Your task is to select the projects that are most likely to be relevant to this query. Consider:
- Direct mentions of project names or technologies
- Related functionality or domains
- Dependencies or interconnections between projects
- The scope and context of the query

Respond with ONLY the project names that are relevant, one per line, exactly as they appear in the list above. If no projects seem relevant, respond with "NONE".

RELEVANT PROJECTS:"""

    try:
        # Get LLM client and make the call
        from services.llm_clients.llm_factory import llm_client_factory
        client = llm_client_factory()

        response = client.call_llm_with_usage(
            system_prompt="You are a helpful assistant that selects relevant projects.",
            user_message=selection_prompt,
            return_raw=True
        )

        # Extract response content
        response_text = response.strip() if isinstance(response, str) else str(response).strip()

        # Parse the response to get project names
        if response_text.upper() == "NONE":
            return []

        selected_names = [name.strip().lstrip('-').strip() for name in response_text.split('\n') if name.strip()]

        # Filter projects based on selected names
        relevant_projects = []
        for project in projects:
            project_name = project.get('name', '')
            if any(selected_name.lower() in project_name.lower() or
                  project_name.lower() in selected_name.lower()
                  for selected_name in selected_names):
                relevant_projects.append(project)

        logger.info(f"Selected {len(relevant_projects)} relevant projects out of {len(projects)} total")
        return relevant_projects

    except Exception as e:
        logger.error(f"Failed to select relevant projects with LLM: {str(e)}")
        # Fallback: return all projects if selection fails
        return projects


def _build_project_context(projects: list) -> str:
    """
    Build the PROJECT_CONTEXT string from selected projects.

    Args:
        projects: List of relevant projects

    Returns:
        Formatted project context string
    """
    if not projects:
        return """## Relevant Project Context

No specific projects identified as relevant to this query. Working in general context.

"""

    context_lines = ["## RELEVANT PROJECT CONTEXT", ""]
    context_lines.append("Here is a list of projects that are relevant to the current task. Use their descriptions to understand their purpose and how they might be interconnected.")
    context_lines.append("")

    for project in projects:
        name = project.get('name', 'Unknown')
        path = project.get('path', 'Unknown path')
        description = project.get('description', 'No description available')

        context_lines.append(f"project: {name}")
        context_lines.append(f"path: {path}")
        if description != 'No description available':
            context_lines.append(f"description: {description}")
        context_lines.append("")

    return "\n".join(context_lines)

// Semantic Search Tool Prompts

template_string SemanticSearchToolTemplate() #"
    ## semantic_search
    Description: Find similar implementations and patterns in codebase using semantic similarity. Use when you DON'T have specific function/class/file/method names (use database for specific names). Use for discovering existing patterns before creating new code.

    Parameters:
    - query: (required) The search terms to find similar implementations - describe what you're looking for in natural language
    - project_name: (optional) Name of the project to search within. If not provided, searches across all projects
    - fetch_next_code: (optional) Set to true to fetch next chunks of results when more are available



    Parameter Details:
    - query: Use descriptive terms that capture the concept you're looking for (e.g., "user authentication", "file upload handler", "database connection setup")
    - project_name: Specify a project name to limit search scope to that project only. Useful when you want to find patterns within a specific codebase
    - fetch_next_code: Only use when the system explicitly tells you there are more results available - do not use preemptively

    Notes:
    - Results are delivered in batches for performance - the system will tell you if more chunks are available
    - IMPORTANT: When using semantic search, always store relevant results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration
    - The query parameter is passed through the JSON structure and processed as action.parameters.get("query")

    Parameter Examples:
    - Find authentication patterns: query: "user authentication login"
    - Find API routing patterns: query: "API routing router express"
    - Find file upload implementations: query: "file upload multer storage"
    - Find database patterns in project: query: "database connection setup", project_name: "my-backend-project"
    - Find error handling patterns: query: "error handling try catch exception"
    - Find payment processing: query: "payment processing stripe integration"
    - Fetch next chunk: query: "database connection setup mongodb", fetch_next_code: true
"#

// Semantic Search Tool Prompts

template_string SemanticSearchToolTemplate() #"
    ## semantic_search
    Description: Find similar implementations and patterns in codebase using semantic similarity. Use when you DON'T have specific function/class/file/method names (use database for specific names). Use for discovering existing patterns before creating new code.

    Parameters:
    - query: (required) The search terms to find similar implementations - describe what you're looking for in natural language
    - project_name: (optional) Name of the project to search within. If not provided, searches across all projects
    - fetch_next_chunk: (optional) Set to true to fetch next chunks of results when more are available

    Parameter Details:
    - query: Use descriptive terms that capture the concept you're looking for (e.g., "user authentication", "file upload handler", "database connection setup")
    - project_name: Specify a project name to limit search scope to that project only. Useful when you want to find patterns within a specific codebase
    - fetch_next_chunk: Only use when the system explicitly tells you there are more results available - do not use preemptively

    Notes:
    - Results are delivered in batches for performance - the system will tell you if more chunks are available
    - IMPORTANT: When using semantic search, always store relevant results in sutra memory if you are not making changes in current iteration or want this code for later use, as search results will not persist to next iteration
    - The query parameter is passed through the JSON structure and processed as action.parameters.get("query")

    Parameter Examples:
    - Find user authentication logic: query: "validate user credentials check password hash compare login verification"
    - Find API endpoint handlers: query: "handle HTTP requests parse request body validate input send JSON response"
    - Find file upload functionality: query: "process uploaded files save to disk validate file type handle multipart form data"
    - Find database query patterns: query: "execute SQL queries handle database connections close connections transaction management", project_name: "backend-api"
    - Find error handling middleware: query: "catch exceptions log errors return error responses handle validation failures"
    - Find JWT token management: query: "generate JWT tokens verify token signature decode payload check expiration"
    - Find email sending functionality: query: "send emails configure SMTP create email templates handle delivery failures"
    - Find data validation patterns: query: "validate form input sanitize user data check required fields return validation errors"
    - Find caching implementation: query: "cache frequently accessed data Redis integration cache invalidation TTL management"
    - Find pagination logic: query: "paginate database results limit offset calculate total pages navigation links"
    - Fetch next chunk: query: "process user registration create new account validate email", fetch_next_chunk: true
"#

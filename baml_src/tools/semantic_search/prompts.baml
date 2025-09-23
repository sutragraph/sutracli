// Semantic Search Tool Prompts

template_string SemanticSearchToolTemplate() #"
## semantic_search

### Description
Find similar implementations and patterns in the codebase using semantic similarity. Use this tool when seeking conceptual matches without specific names (e.g., for discovering patterns before new code). For exact names, prefer database or search_keyword.

### Parameters
- query: REQUIRED - Describe the concept in natural language (type: string).
- project_name: OPTIONAL - Limit to a specific project (type: string?).
- fetch_next_chunk: OPTIONAL - Set to true only if more results are available (type: bool?).

### Usage
{
  "tool_name": "semantic_search",
  "parameters": {
    "query": "descriptive terms",
    "project_name": "project_name",
    "fetch_next_chunk": true
  }
}

### Guidelines
Think step-by-step: 'Goal: Discover patterns? Tool: semantic_search. Why: Conceptual search.'
Use dense, explicit queries for best results.
Store relevant results in sutra_memory for later use or if not acting immediately, as results do not persist.
Fetch next chunk only when indicated.

### Examples
1. Authentication patterns:
{
  "query": "user authentication login"
}

2. API routing:
{
  "query": "API routing router express"
}

3. File uploads:
{
  "query": "file upload multer storage"
}

4. Database in specific project:
{
  "query": "database connection setup",
  "project_name": "my-backend-project"
}

5. Error handling:
{
  "query": "error handling try catch exception"
}

6. Payments:
{
  "query": "payment processing stripe integration"
}

7. Next chunk:
{
  "query": "database connection setup mongodb",
  "fetch_next_chunk": true
}
"#

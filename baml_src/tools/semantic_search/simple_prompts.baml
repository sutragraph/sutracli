template_string SimpleSemanticSearchToolTemplate() #"
## semantic_search

Find similar implementations and patterns in the codebase using semantic similarity. Use this tool when seeking conceptual matches without specific names (e.g., for discovering patterns before new code). For exact names, prefer database or search_keyword.

Required Parameters:
  - query: Describe the concept in natural language.

Optional Parameters:
  - fetch_next_chunk: Set to true only if more results are available.
"#

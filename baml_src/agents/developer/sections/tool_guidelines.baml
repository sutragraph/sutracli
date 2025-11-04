template_string DeveloperGuidelines() #"
====

# Tool Use

1. Make sure to adhere to the tools schema.
2. Provide every required argument.
3. DO NOT use tools to access items that are already available in the context section.
4. Avoid HTML entity escaping - use plain characters instead.
5. After you are done with the changes in a file use the `diagnostics` tool to check for possible errors.
6. Use `'fetch_next_chunk': true` only when there are more results available. (do not use preemptively)
7. Use only the tools that are currently available
8. Tool Status is provided by user after every tool call.

## Searching and Reading:
  - If you are unsure how to fulfill the user's request, gather more information with tool calls.
  - Bias towards not asking the user for help if you can find the answer yourself
  - Before you read or edit a file, you must first find the full path
  - Refer to the history for proper decision making and to avoid redundant tool calls

## Tool Usage Best Practices:
  - Document every tool call in sutra memory's history section with the command used and results obtained
  - `search_keyword` is best for finding specific functions, classes, or keywords across multiple files; it does not search file names. Use the `list_files` tool to search for files
  - NEVER make blind guesses or assumptions - always research and understand existing structures first before writing code (e.g., examine actual database schema before writing queries, study existing API patterns before creating new endpoints, review existing class structures before implementing new methods)
  - Do NOT create code that references non-existent tables, functions, or structures - always investigate what actually exists in the codebase before writing new code
"#

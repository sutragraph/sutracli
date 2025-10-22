template_string QAEngineerToolGuidelines() #"
====

# Tool Use

1. Make sure to adhere to the tools schema
2. Provide every required argument
3. DO NOT use tools to access items that are already available in the sutra memory
4. Use only the tools that are currently available
5. NEVER run commands that don't terminate on their own such as web servers or file watchers
6. Use `"fetch_next_chunk": true` only when user explicitly tells you there are more results available. (do not use preemptively)

## Searching and Reading:
  - If you are unsure how to fulfill the testing requirements, gather more information with tool calls.
  - Bias towards not asking the user for help if you can find the answer yourself
  - When providing paths to tools, always use absolute paths
  - Before you read or edit a file, you must first find the full path
  - Refer to the history for proper decision making and to avoid redundant tool calls

## Tool Usage Best Practices:
  - Always use the list_files tool before creating tasks or unit tests to understand the workspace structure
  - Use the terminal tool to execute unit tests and capture results
  - Document every tool call in history with the command used and results obtained
  - When tests fail, capture complete error messages and stack traces from terminal output
  - Store important test execution details in history for tracking and reference
  - `search_keyword` is best for finding specific functions, classes, or keywords across multiple files; it does not search file names. Use the `list_files` tool to search for files
"#

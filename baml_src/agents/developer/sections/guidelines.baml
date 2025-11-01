template_string DeveloperGuidelines() #"
## Searching and Reading
1. If you are unsure how to fulfill the user's request, gather more information with tool calls.
2. Always Use Chain of Thought Reasoning step-by-step before giving your json response.

## Tool Use
1. Make sure to adhere to the tools schema.
2. Provide every required argument.
3. DO NOT use tools to access items that are already available in the context section.
4. Avoid HTML entity escaping - use plain characters instead.
5. After you are done with the changes in a file use the `diagnostics` tool to check for possible errors.
6. Use `'fetch_next_chunk': true` only when there are more results available. (do not use preemptively)
"#

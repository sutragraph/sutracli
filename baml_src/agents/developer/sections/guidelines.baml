template_string DeveloperGuidelines() #"
## Searching and Reading
If you are unsure how to fulfill the user's request, gather more information with tool calls.

## Tool Use
1. Make sure to adhere to the tools schema.
2. Provide every required argument.
3. DO NOT use tools to access items that are already available in the context section.
4. Avoid HTML entity escaping - use plain characters instead.
5. After you are done with the changes in a file use the `diagnostics` tool to check for possible errors.
"#

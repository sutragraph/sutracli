template_string ChainOfThought(action: string?) #"
# Reasoning Methodology

Before providing your JSON response, first use `<thinking>` tags to think through the current situation step-by-step and what should happen next. Consider what is in sutra_memory - the code snippets, history, and tasks. Think about what needs to be added or moved, what information should be retrieved or stored, and how past actions inform the current decision.

After your thinking block, provide the JSON response. Include inline comments with your thinking for the `tool_call`, `add_history`, `tasks`, and `code` to make decisions about these fields.

Example:
<thinking>
- ...
- ...
...
</thinking>
{
  "message": "...",
  "sutra_memory": {
    // <Your thinking in comment>
    "add_history": "...",
    // <Your thinking in comment>
    "tasks": [...],
    // <Your thinking in comment>
    "code": [...]
  },
  // <Your thinking in comment>
  "tool_call": {
    ...
  }
}

Important: You must include comments in the JSON. We will automatically strip them before parsing. JSON with comments is completely valid here.
"#

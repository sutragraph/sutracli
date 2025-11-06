template_string ChainOfThought(action: string?) #"
# Reasoning Methodology

Before providing the JSON response, first use `<thinking>` tags for your step-by-step thought process. This is your space to think about the task, code storage, history, explore possibilities, and plan your response. After you have finished thinking, provide your response as a JSON object. Inside the JSON, add comments for your thinking before the following fields: `tool_call`, `add_history`, `tasks`, and `code`.

Example:
<thinking>
- ...
- ...
...
</thinking>
{
  message: "...",
  // <Your thinking in comment>
  tool_call: {
    ...
  },
  sutra_memory: {
    // <Your thinking in comment>
    add_history: "...",
    // <Your thinking in comment>
    tasks: [...],
    // <Your thinking in comment>
    code: [...]
  }
}

Important: You must include comments in the JSON. We will automatically strip them before parsing.
"#

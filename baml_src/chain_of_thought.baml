// template_string ChainOfThought(action: string?) #"
// # Chain of Thought Reasoning

// Before you respond, engage in a step-by-step thinking process, which is crucial for complex tasks. Your thought process should cover your primary objective, what relevant information is available in your Sutra Memory, what you can learn from past interactions and code snippets (History & Context), what information you are missing and need to do next (Needs Assessment), and finally, formulate an optimal next step and what you will need to complete it (Action Plan). This structured thinking will help you make better decisions. After your thinking process, provide your structured response in JSON.

// Example:
// - ...
// - ...
// ...
// {
//   ... // schema
// }
// "#

template_string ChainOfThought(action: string?) #"
# Reasoning Methodology

Before providing the JSON response, first use `<thinking>` tags for your step-by-step thought process. This is your space to think about the task, explore possibilities, and plan your response. After you have finished thinking, provide your response as a JSON object. Inside the JSON, add comments for your reasoning before the following fields: `tool_call`, `add_history`, `tasks`, and `code`.

Example:
<thinking>
- ...
- ...
...
</thinking>
{
  thinking: "...",
  // <Your Reasoning Here>
  tool_call: {
    ...
  },
  sutra_memory: {
    // <Your Reasoning Here>
    add_history: "...",
    // <Your Reasoning Here>
    tasks: [...],
    // <Your Reasoning Here>
    code: [...]
  }
}

Important: You must include comments in the JSON. We will automatically strip them before parsing.
"#

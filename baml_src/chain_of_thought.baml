template_string ChainOfThought(action: string?) #"
Think through problems, brainstorm ideas, and plan any actions before you provide a structured response in JSON. This helps you work through complex problems, develop strategies, and outline approaches before taking action. It also helps you organize your thoughts.

Example:
- ...
- ...
...
{
  ... // schema
}
"#

// A tool for thinking through problems, brainstorming ideas, or planning without executing any actions.

// This tool allows you to work through complex problems, develop strategies, or outline approaches before taking action. It doesn't perform any actual operations but helps organize thoughts.

// ## Parameters:

// - `content` (string, required): Content to think about. This should be a description of what to think about or a problem to solve.

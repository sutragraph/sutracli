template_string CrossIndexingCompletion() #"
====

## attempt_completion

Give summary of current task in short in 3-4 lines when you are done with your all task.

Usage:
{
  "tool_call": {
    "tool_name": "attempt_completion",
    "parameters": {
      "result": "your brief summary of what was accomplished and key findings in 3-4 lines."
    }
  }
}

Paramerters Example:
{
  "result": "Implemented user authentication and authorization features, including login, registration, and role-based access control. Key findings include the need for enhanced password security measures and improved session management."
}

Summary Requirements:
  - Provide only a brief 3-4 line summary
  - Mention what you accomplished in your current task
  - Include key findings or results
  - Do NOT include detailed information
  - MANDATORY: This tool MUST be used when you complete your task
"#

template_string Output_TaskFilter() #"
# Output Format

You must provide the filtered task list in JSON format that matches the TaskFilterResponse structure:

```json
{
  "tasks": [
    {
      "id": 1,
      "description": "First filtered task description"
    },
    {
      "id": 2,
      "description": "Second filtered task description"
    }
  ]
}
```

Always provide a complete filtered task list that eliminates duplicates while preserving all necessary functionality.
"#

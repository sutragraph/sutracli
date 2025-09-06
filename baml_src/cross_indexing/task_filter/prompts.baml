template_string SystemPrompt_TaskFilter() #"
{{ Base_TaskFilter() }}
{{ Objective_TaskFilter() }}
{{ Rules_TaskFilter() }}
{{ Output_TaskFilter() }}
{{ Examples_TaskFilter() }}
"#

template_string UserPrompt_TaskFilter(task_list: string) #"
{{ _.role("user") }}
## Tasks to Filter

The following tasks were created by the previous phase and need to be filtered for duplicates and optimized:

{{ task_list }}

## Instructions

1. Analyze the above tasks for duplicates and similarities
2. Merge similar tasks while preserving all functionality
3. Optimize task descriptions for clarity and completeness
4. Create a clean, deduplicated task list in JSON format
5. Provide a summary of filtering actions performed

Please provide the filtered task list now.
"#

function AwsTaskFilter(task_list: string) -> TaskFilterResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_TaskFilter() }}
    {{ UserPrompt_TaskFilter(task_list) }}
  "#
}

function AnthropicTaskFilter(task_list: string) -> TaskFilterResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_TaskFilter() }}
    {{ UserPrompt_TaskFilter(task_list) }}
  "#
}

function ChatGPTTaskFilter(task_list: string) -> TaskFilterResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_TaskFilter() }}
    {{ UserPrompt_TaskFilter(task_list) }}
  "#
}

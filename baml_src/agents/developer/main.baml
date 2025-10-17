template_string DeveloperSystemPromptBase() #"
You are a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices.

Your task is to make precise, efficient, code changes based on user requirements.

## OUTPUT FORMAT
Output exactly in this structure:

{
  "thinking": "REQUIRED: Brief Chain-of-Thought (e.g., 'Goal: Trace auth. Memory: Bug1 unresolved. Tool: semantic_search. Why: Broad discovery. Audit: Covers all tracks?').",
  "tool_call": {  // REQUIRED: Select one tool
    "tool_name": "search_keyword|database|list_files|semantic_search|attempt_completion",
    "parameters": { ... }  // Tool-specific (e.g., 'query': string)
  },
  "sutra_memory": {
    "add_history": "REQUIRED: summary of only new progress and findings (e.g., - New Progress: Traced main_func. - New Finding: Bug1 at line 45. - Unresolved: helperFunc)—avoid repetition from prior history. Limit to 3-5 findings.",
    "tasks": [  // OPTIONAL: Array of TaskOperation objects
      { "action": "add|move", "id": string, "to_status": "pending|current|completed", "description": string? }
    ],
    "code": [  // OPTIONAL: Array of code storage objects
      {
        "action": "add",
        "id": string, // eg. "1",
        "file": string?,
        "start_line": int?,
        "end_line": int?,
        "description": string?,
    ]
  }
}

## Tool Use
1. Make sure to adhere to the tools schema.
2. Provide every required argument.
3. DO NOT use tools to access items that are already available in the context section.
4. Avoid HTML entity escaping - use plain characters instead.

## Searching and Reading
If you are unsure how to fulfill the user's request, gather more information with tool calls.

##
"#

template_string DeveloperUserPrompt(context: string) #"
{{ _.role("user") }}
{{ context }}
"#

template_string DeveloperSystemPrompt(params: DeveloperPromptParams) #"
{{ BaseSystemPrompt(Agent.DEVELOPER, [ToolName.Database, ToolName.SearchKeyword, ToolName.SemanticSearch, ToolName.ListFiles], params.base_params) }}

"#

function AwsBedrockDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function AnthropicClaudeDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function OpenAIChatGPTDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function GoogleGeminiDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function GCPVertexAIDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function AzureOpenAIDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function AzureAIFoundryDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

function OpenRouterDeveloperAgent(params: DeveloperAgentParams) -> DeveloperResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPrompt(params.prompt_params) }}
    {{ DeveloperUserPrompt(params.context) }}
  "#
}

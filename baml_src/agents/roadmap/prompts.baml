template_string RoadmapSystemPromptBase() #"
{{ RoadmapIdentity() }}
{{ RoadmapConstraints() }}
{{ RoadmapWorkflow() }}
{{ RoadmapStrategy() }}
{{ SutraMemoryPrompt() }}
"#

template_string RoadmapUserPrompt(context: string) #"
{{ _.role("user") }}
{{ context }}
"#

template_string RoadmapSystemPrompt(params: RoadmapPromptParams) #"
{{ BaseSystemPrompt(Agent.ROADMAP, [ToolName.Database, ToolName.SearchKeyword, ToolName.SemanticSearch, ToolName.ListFiles], params.base_params) }}

"#

function AwsBedrockRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AnthropicClaudeRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function OpenAIChatGPTRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function GoogleGeminiRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function GCPVertexAIRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AzureOpenAIRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AzureAIFoundryRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function OpenRouterRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

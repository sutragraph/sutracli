template_string RoadmapSystemPromptBase() #"
    {{ RoadmapIdentity() }}

    {{ RoadmapWorkflow() }}

    {{ RoadmapConstraints() }}
"#

template_string RoadmapUserPrompt(context: string) #"
    {{ _.role("user") }}
    {{ context }}
"#

template_string RoadmapSystemPrompt(params: RoadmapPromptParams) #"
{{ BaseSystemPrompt(AgentName.ROADMAP, [ToolName.Database, ToolName.SearchKeyword, ToolName.SemanticSearch, ToolName.ListFiles], params.base_params) }}

## ADDITIONAL ROADMAP RULES
7. **Multi-Project Focus**: Always analyze ecosystem impact, never single-project tunnel vision
8. **Simplicity First**: Extend existing code before creating new, choose minimal viable solutions

Remember: You are generating strategic roadmaps, not implementing code.
"#

function AwsRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}

    {{ RoadmapSystemPrompt(params.prompt_params) }}

    {{RoadmapUserPrompt(params.context)}}
  "#
}

function AnthropicRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}

    {{ RoadmapSystemPrompt(params.prompt_params) }}

    {{RoadmapUserPrompt(params.context)}}
  "#
}


function ChatGPTRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}

    {{ RoadmapSystemPrompt(params.prompt_params) }}

    {{RoadmapUserPrompt(params.context)}}
  "#
}

template_string RoadmapSystemPromptBase() #"
{{ RoadmapIdentity() }}
{{ RoadmapWorkflow() }}
{{ RoadmapStrategy() }}
{{ RoadmapConstraints() }}
"#

template_string RoadmapUserPrompt(context: string) #"
{{ _.role("user") }}
{{ context }}
"#

template_string RoadmapSystemPrompt(params: RoadmapPromptParams) #"
{{ BaseSystemPrompt(Agent.ROADMAP, [ToolName.Database, ToolName.SearchKeyword, ToolName.SemanticSearch, ToolName.ListFiles], params.base_params) }}

##  RULES
1. Multi-Project Focus: Always analyze ecosystem impact, never single-project tunnel vision
2. Simplicity First: Extend existing code before creating new, choose minimal viable solutions

## COMPLETION TOOL USAGE
The `attempt_completion` tool accepts two parameter formats:

Simple Format - For non-implementation requests (greetings, questions, info requests):
Use parameters with just `result: "Your simple response here"`

Full Roadmap Format - For implementation planning (features, fixes, architecture):
Use parameters with full roadmap structure including `projects` array and `summary` field

Decision Rule: Does the user want implementation planning?
- NO → Use simple format with just `result`
- YES → Use full roadmap format with `projects` and `summary`

Remember: You are generating strategic roadmaps, not implementing code.
"#

function AwsRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AnthropicRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function ChatGPTRoadmapAgent(params: RoadmapAgentParams) -> RoadmapResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params.prompt_params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

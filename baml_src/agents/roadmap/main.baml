template_string RoadmapSystemPrompt(params: RoadmapPromptParams) #"
{{ RoadmapIdentity() }}

{{ ctx.output_format }}

{{ ChainOfThought() }}

{{ RoadmapGuidelines() }}

{{ RoadmapWorkflow() }}

{{ RoadmapSutraMemoryPrompt() }}

{{ ToolsPrompt(Agent.Roadmap, [ToolName.DatabaseSimple, ToolName.SearchKeyword, ToolName.SemanticSearchSimple, ToolName.ListFilesWithProjectName]) }}
{% if params.project_context.projects|length > 0 %}
{{ ProjectContextTemplate(params.project_context) }}
{% endif %}
"#

template_string RoadmapUserPrompt(context: string) #"
{{ _.role("user") }}
{{ context }}
"#


function AwsBedrockRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AnthropicClaudeRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function OpenAIChatGPTRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function GoogleGeminiRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function GCPVertexAIRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AzureOpenAIRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function AzureAIFoundryRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

function OpenRouterRoadmapAgent(params: RoadmapPromptParams) -> RoadmapResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ RoadmapSystemPrompt(params) }}
    {{ RoadmapUserPrompt(params.context) }}
  "#
}

test TestName {
  functions [AwsBedrockRoadmapAgent]
  args {
    params {
        context #"
        hello world
      "#
        system_info {
          os #"
          hello world
        "#
          shell #"
          hello world
        "#
          home #"
          hello world
        "#
          current_dir #"
          hello world
        "#
      }
        project_context {
          projects [
          {
              name #"
              hello world
            "#
              path #"
              hello world
            "#
              description #"
              hello world
            "#
          },
          {
              name #"
              hello world
            "#
              path #"
              hello world
            "#
              description #"
              hello world
            "#
          }
        ]
      }
    }
  }
}

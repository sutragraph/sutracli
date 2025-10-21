template_string QAEngineerSystemPrompt(params: QAEngineerPromptParams) #"
{{ QAEngineerIdentity() }}

{{ ToolsPrompt(Agent.QAEngineer, [ToolName.DatabaseSimple, ToolName.SearchKeywordSimple, ToolName.SemanticSearchSimple, ToolName.ListFilesSimple, ToolName.Terminal]) }}
{{ QAEngineerToolGuidelines() }}

{{ QAEngineerSutraMemory() }}

{{ QAEngineerWorkflow() }}

{{ SystemInfo(params.system_info) }}

====

"#

template_string QAEngineerUserPrompt(context: string) #"
{{ ChainOfThought() }}

====

{{ _.role("user") }}
{{ context }}
"#

function AwsBedrockQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}

    {{ ctx.output_format() }}

    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function AnthropicClaudeQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function OpenAIChatGPTQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function GoogleGeminiQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function GCPVertexAIQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function AzureOpenAIQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function AzureAIFoundryQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function OpenRouterQAEngineerAgent(params: QAEngineerAgentParams) -> QAEngineerResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params.prompt_params) }}
    {{ ctx.output_format() }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

test AwsBedrockQAEngineerAgent {
  functions [AwsBedrockQAEngineerAgent]
  args {
    params{
      context "Code changes detected in sutra memory."
      prompt_params {
        system_info {
          os "Linux"
          shell "bash"
          home "/home/user"
          current_dir "/home/user/project"
        }
      }
    }
  }
}

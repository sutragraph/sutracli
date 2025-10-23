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

function AwsBedrockQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ QAEngineerSystemPrompt(params) }}

    {{ ctx.output_format }}

    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function AnthropicClaudeQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function OpenAIChatGPTQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function GoogleGeminiQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function GCPVertexAIQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function AzureOpenAIQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function AzureAIFoundryQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

function OpenRouterQAEngineerAgent(params: QAEngineerPromptParams) -> QAEngineerResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ QAEngineerSystemPrompt(params) }}
    {{ ctx.output_format }}
    {{ QAEngineerUserPrompt(params.context) }}
  "#
}

test AwsBedrockQAEngineerAgent {
  functions [AwsBedrockQAEngineerAgent]
  args {
    params{
      context "Code changes detected in sutra memory."

        system_info {
          os "Linux"
          shell "bash"
          home "/home/user"
          current_dir "/home/user/project"
        }

    }
  }
}

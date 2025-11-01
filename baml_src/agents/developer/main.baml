template_string DeveloperSystemPromptBase(params:DeveloperPromptParams) #"
{{ DeveloperIdentity() }}

{{ ctx.output_format }}

{{ ChainOfThought() }}

{{ DeveloperGuidelines() }}

{{ToolsPrompt(Agent.Developer, [ToolName.DatabaseSimple, ToolName.SearchKeywordSimple, ToolName.SemanticSearchSimple, ToolName.ListFilesSimple, ToolName.EditFile, ToolName.Diagnostics, ToolName.Terminal]) }}
{{ DeveloperSutraMemoryPrompt() }}
{{ SystemInfo(params.system_info)}}
"#

function AwsBedrockDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}
  "#
}

function AnthropicClaudeDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}

  "#
}

function OpenAIChatGPTDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}

  "#
}

function GoogleGeminiDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}

  "#
}

function GCPVertexAIDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}

  "#
}

function AzureOpenAIDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}

  "#
}

function AzureAIFoundryDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}

  "#
}

function OpenRouterDeveloperAgent(params:DeveloperPromptParams) -> DeveloperResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ DeveloperSystemPromptBase(params) }}
    {{ _.role("user") }}
    {{ params.context }}
  "#
}


test TestName {
  functions [AwsBedrockDeveloperAgent]
  args {
    params {
        context #"
        can you create a new file named abc.txt with content hello world
      "#
        system_info {
          os #"
          linux
        "#
          shell #"
          fish
        "#
          home #"
          /home
        "#
          current_dir #"
          /home/fishmeister/repos/tests/test folder/
        "#
      }
    }
  }
}

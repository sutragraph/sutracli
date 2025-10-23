template_string DeveloperSystemPromptBase(params:DeveloperPromptParams) #"
{{ DeveloperIdentity() }}

{{ ctx.output_format }}

## Searching and Reading
If you are unsure how to fulfill the user's request, gather more information with tool calls.

## Tool Use
1. Make sure to adhere to the tools schema.
2. Provide every required argument.
3. DO NOT use tools to access items that are already available in the context section.
4. Avoid HTML entity escaping - use plain characters instead.
5. After you are done with the changes in a file use the `diagnostics` tool to check for possible errors.

{{ToolsPrompt(Agent.Developer, [ToolName.DatabaseSimple, ToolName.SearchKeywordSimple, ToolName.SemanticSearchSimple, ToolName.ListFilesSimple, ToolName.EditFile, ToolName.Diagnostics, ToolName.Terminal]) }}
{{ DeveloperSutraMemoryPrompt() }}
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
    }
  }
}

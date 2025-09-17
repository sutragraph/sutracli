template_string SystemPrompt_Phase1(home: string, current_dir: string) #"
{{ Base_Phase1() }}
{{ CrossIndexingToolCalls([ToolName.Database, ToolName.SearchKeywordWithoutProjectName, ToolName.ListFilesWithoutProjectName]) }}
{{ SutraMemory_Phase1() }}
{{ ToolGuidelines_Phase1() }}
{{ ToolUsageExamples_Phase1() }}
{{ Objective_Phase1() }}
{{ Capabilities_Phase1() }}
{{ Rules_Phase1() }}
{{ CrossIndexingSystemInfoTemplate(home, current_dir) }}
"#

template_string UserPrompt_Phase1(analysis_query: string, memory_context: string) #"
{{ _.role("user") }}
ANALYSIS REQUEST: {{analysis_query}}

SUTRA MEMORY CONTEXT:
{{memory_context if memory_context else "No previous context"}}
"#

function AwsBedrockPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function AnthropicClaudePackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function OpenAIChatGPTPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function GoogleGeminiPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function GCPVertexAIPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function AzureOpenAIPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function AzureAIFoundryPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

function OpenRouterPackageDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase1(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase1(analysis_query, memory_context) }}
  "#
}

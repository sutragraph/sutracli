template_string SystemPrompt_Phase2(home: string, current_dir: string) #"
{{ Base_Phase2() }}
{{ CrossIndexingToolCalls([ToolName.Database, ToolName.SearchKeywordWithoutProjectName, ToolName.ListFilesWithoutProjectName]) }}
{{ SutraMemory_Phase2() }}
{{ ToolGuidelines_Phase2() }}
{{ ToolUsageExamples_Phase2() }}
{{ Objective_Phase2() }}
{{ Capabilities_Phase2() }}
{{ Rules_Phase2() }}
{{ CrossIndexingSystemInfoTemplate(home, current_dir) }}
"#

template_string UserPrompt_Phase2(analysis_query: string, memory_context: string) #"
{{ _.role("user") }}
ANALYSIS REQUEST: {{analysis_query}}

SUTRA MEMORY CONTEXT:
{{memory_context if memory_context else "No previous context"}}
"#

function AwsBedrockImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function AnthropicClaudeImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function OpenAIChatGPTImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function GoogleGeminiImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function GCPVertexAIImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function AzureOpenAIImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function AzureAIFoundryImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function OpenRouterImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

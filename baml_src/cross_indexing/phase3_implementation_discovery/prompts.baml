template_string SystemPrompt_Phase3(home: string, current_dir: string) #"
{{ Base_Phase3() }}
{{ CrossIndexingToolCalls([ToolName.Database, ToolName.SearchKeywordWithoutProjectName, ToolName.ListFilesWithoutProjectName]) }}
{{ SutraMemory_Phase3() }}
{{ ToolGuidelines_Phase3() }}
{{ ToolUsageExamples_Phase3() }}
{{ Objective_Phase3() }}
{{ Capabilities_Phase3() }}
{{ Rules_Phase3() }}
{{ CrossIndexingSystemInfoTemplate(home, current_dir) }}
"#

template_string UserPrompt_Phase3(analysis_query: string, memory_context: string) #"
{{ _.role("user") }}
ANALYSIS REQUEST: {{analysis_query}}

SUTRA MEMORY CONTEXT:
{{memory_context if memory_context else "No previous context"}}
"#

function AwsBedrockImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function AnthropicClaudeImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function OpenAIChatGPTImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function GoogleGeminiImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function GCPVertexAIImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function AzureOpenAIImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function AzureAIFoundryImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function OpenRouterImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

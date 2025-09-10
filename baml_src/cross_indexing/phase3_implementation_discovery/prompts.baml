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

function AwsImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function AnthropicImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

function ChatGPTImplementationDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase3(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase3(analysis_query, memory_context) }}
  "#
}

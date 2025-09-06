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

function AwsImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AwsClaudeSonnet4
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function AnthropicImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}

function ChatGPTImportDiscovery(analysis_query: string, memory_context: string, system_info: SystemInfo_CrossIndexing) -> CrossIndexingResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Phase2(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Phase2(analysis_query, memory_context) }}
  "#
}


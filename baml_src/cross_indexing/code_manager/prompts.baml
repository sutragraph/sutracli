template_string SystemPrompt_Manager(home: string, current_dir: string) #"
{{ Base_Manager() }}
{{ Objective_Manager() }}
{{ Capabilities_Manager() }}
{{ Rules_Manager() }}
{{ Examples_Manager() }}
{{ Completion_Manager() }}
{{ CrossIndexingSystemInfoTemplate(home, current_dir) }}
"#

template_string UserPrompt_Manager(tool_results: string) #"
{{ _.role("user") }}
# CODE SNIPPET TO ANALYZE

Please analyze the following code snippet from cross-indexing analysis and extract any connection code that should be returned:

{{tool_results}}
"#

function AwsCodeManager(tool_results: string, system_info: SystemInfo_CrossIndexing) -> CodeManagerResponse {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Manager(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Manager(tool_results) }}
  "#
}

function AnthropicCodeManager(tool_results: string, system_info: SystemInfo_CrossIndexing) -> CodeManagerResponse {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SystemPrompt_Manager(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Manager(tool_results) }}
  "#
}

function ChatGPTCodeManager(tool_results: string, system_info: SystemInfo_CrossIndexing) -> CodeManagerResponse {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Manager(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Manager(tool_results) }}
  "#
}

function GeminiCodeManager(tool_results: string, system_info: SystemInfo_CrossIndexing) -> CodeManagerResponse {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Manager(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Manager(tool_results) }}
  "#
}

function VertexAICodeManager(tool_results: string, system_info: SystemInfo_CrossIndexing) -> CodeManagerResponse {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Manager(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Manager(tool_results) }}
  "#
}

function AzureCodeManager(tool_results: string, system_info: SystemInfo_CrossIndexing) -> CodeManagerResponse {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ SystemPrompt_Manager(system_info.home, system_info.current_dir) }}
    {{ UserPrompt_Manager(tool_results) }}
  "#
}
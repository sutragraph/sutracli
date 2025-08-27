template_string GlobalToolsPrompt(tools: ToolName[]) #"
## Available Tools

{% for tool in tools %}
{% if tool == "Database" %}
{{ DatabaseToolTemplate() }}

{% elif tool == "SearchKeyword" %}
{{ SearchKeywordToolTemplate() }}

{% elif tool == "SemanticSearch" %}
{{ SemanticSearchToolTemplate() }}

{% elif tool == "ListFiles" %}
{{ ListFilesToolTemplate() }}

{% endif %}
{% endfor %}
"#

// Agent-specific completion tool injection
template_string CompletionToolPrompt(agent_name: AgentName) #"
{% if agent_name == "ROADMAP" %}
{{ RoadmapCompletionToolTemplate() }}
{% endif %}
"#

template_string ToolsPrompt(agent_name: AgentName, tools: ToolName[]) #"
{% set global_tools = tools | reject("equalto", "Completion") | list %}
{% set has_completion = "Completion" in tools %}

{% if global_tools|length > 0 %}
{{ GlobalToolsPrompt(global_tools) }}
{% endif %}

{% if has_completion %}
{{ CompletionToolPrompt(agent_name) }}
{% endif %}
"#
template_string GlobalToolsPrompt(tools: ToolName[]) #"
## Available Tools

{% for tool in tools %}
{% if tool == ToolName.Database %}
{{ DatabaseToolTemplate() }}

{% elif tool == ToolName.SearchKeyword %}
{{ SearchKeywordToolTemplate() }}

{% elif tool == ToolName.SearchKeywordWithoutProjectName %}
{{ SearchKeywordToolWithoutProjectNameTemplate() }}


{% elif tool == ToolName.SemanticSearch %}
{{ SemanticSearchToolTemplate() }}

{% elif tool == ToolName.ListFiles %}
{{ ListFilesToolTemplate() }}

{% elif tool == "ListFilesToolWithoutProjectName" %}
{{ ListFilesToolWithoutProjectNameTemplate() }}

{% endif %}
{% endfor %}
"#

template_string CompletionToolPrompt(agent_name: AgentName) #"
{% if agent_name == AgentName.ROADMAP %}
{{ RoadmapCompletionToolTemplate() }}

{% elif agent_name == "CrossIndexing" %}
{{ CrossIndexingCompletion() }}

{% endif %}
"#

template_string ToolsPrompt(agent_name: AgentName, tools: ToolName[]) #"
{% if tools|length > 0 %}
{{ GlobalToolsPrompt(tools) }}
{% endif %}

{{ CompletionToolPrompt(agent_name) }}
"#

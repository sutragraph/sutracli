template_string GlobalToolsPrompt(tools: ToolName[]) #"
# Tools

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

{% elif tool == ToolName.ListFilesWithoutProjectName %}
{{ ListFilesToolWithoutProjectNameTemplate() }}

{% endif %}
{% endfor %}
"#

template_string CompletionToolPrompt(agent_name: Agent) #"
{% if agent_name == Agent.ROADMAP %}
{{ RoadmapCompletionToolTemplate() }}

{% elif agent_name == Agent.CrossIndexing %}
{{ CrossIndexingCompletion() }}

{% endif %}
"#

template_string ToolsPrompt(agent_name: Agent, tools: ToolName[]) #"
{% if tools|length > 0 %}
{{ GlobalToolsPrompt(tools) }}
{% endif %}

{{ CompletionToolPrompt(agent_name) }}
"#

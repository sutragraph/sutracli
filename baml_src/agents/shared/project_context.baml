class Project {
  name string
  path string
  description string
}

class ProjectContext {
  projects Project[]
}

template_string ProjectEntry(project: Project) #"
project_name: {{ project.name }}
path: {{ project.path }}
description: {{ project.description }}
"#

template_string ProjectContextTemplate(project_context: ProjectContext) #"
## PROJECTS CONTEXT:

NOTE: Project Path is the complete root directory. Use it exactly as provided - do NOT append project name to the path.

{% for project in project_context.projects %}
{{ ProjectEntry(project) }}

{% endfor %}
"#

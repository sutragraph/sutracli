template_string RoadmapWorkflow(projects_count:int) #"
====

# Workflow

{% if projects_count > 1 %}
# Multi-Project Workflow

Phase 1: Cross-Project Pattern Discovery:
  - Map communication patterns: search for API calls, service interfaces, data contracts between projects
  - Search targets: service endpoints, message queues, shared models, client libraries, API gateways
  - Stop when: no new relevant patterns found in 2 consecutive searches
  - Store cross-project connections in sutra_memory immediately

Phase 2: Systematic Code Analysis:
  - Search for existing implementations of similar functionality across identified projects
  - Target search terms: action verbs (create, update, delete, process), entity names, API patterns
  - Stop when: find 2-3 relevant examples OR complete 3 focused searches with low relevance results
  - For each finding, evaluate: reusability (0-10), modification effort, integration complexity
  - Connection tracing: if Service A calls Service B, trace both sides completely

Phase 3: Coordinated Change Planning:
  - For each affected project, define minimal changes leveraging existing patterns
  - Prioritize: reuse existing code, maintain current contracts, minimize cross-boundary modifications
  - Document dependencies between changes across projects
  - Create implementation sequence maintaining system stability

{% else %}
# Workflow

Phase 1: Targeted Code Discovery:
  - Identify search scope: controllers, services, models, utilities, configurations
  - Primary search: keywords directly related to requested functionality
  - Secondary search: related concepts, similar patterns, adjacent functionality
  - Stop when: found relevant implementations OR completed 2-3 targeted searches per category
  - Store key findings (file paths, function signatures, patterns) in sutra_memory

Phase 2: Hierarchical Pattern Analysis:
  - Search hierarchy (stop at each level when good matches found):
    1. Exact functionality matches (same action, same entity)
    2. Similar functionality patterns (same action, different entity)
    3. Architectural patterns (similar structure/approach)
    4. Utility functions and shared components
  - For each pattern, analyze: relevance (0-10), adaptation effort, integration points
  - Search concrete examples: error handling, validation, logging, transaction management
  - Stop when: have 2-3 reusable patterns OR diminishing relevance in results

Phase 3: Implementation Planning:
  - Select best-matched existing pattern as primary template
  - Identify integration points: existing imports, dependencies, configurations
  - Plan minimal changes: extend rather than replace, leverage existing utilities
  - Define success criteria: integration with current patterns and conventions
  - Stop when: clear implementation path defined OR blocking gaps identified
{% endif %}

Universal Search Guidelines:
- Search expansion: start specific, broaden gradually if no results
- Search limits: maximum 3 searches per category before proceeding
- Relevance threshold: stop if results relevance < 3/10 for 2 consecutive searches
- Pattern quality: prefer complete working examples over partial snippets
"#

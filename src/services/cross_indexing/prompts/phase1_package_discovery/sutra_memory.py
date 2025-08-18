"""
Sutra Memory Guidelines for Package Discovery

Memory management guidelines specific to package discovery.
"""

PACKAGE_DISCOVERY_SUTRA_MEMORY = """====

SUTRA MEMORY

Sutra Memory is a dynamic memory system that tracks package discovery state across iterations. It ensures continuity, prevents redundant operations, and maintains context for comprehensive package analysis. The system tracks iteration history and manages analysis tasks for import pattern discovery.

Required Components:
- add_history: Comprehensive summary of current iteration actions, tool usage, package discoveries, and task creation (MANDATORY in every response)

Optional Components:
- task: Manage analysis tasks by adding new ones with unique IDs

Usage Format

<sutra_memory>
<task>
<add id="unique_id" to="pending">specific task description</add>
<move from="current" to="completed">id</move>
<move from="panding" to="current">id</move>
</task>
<add_history>Brief summary of current iteration actions and findings</add_history>
</sutra_memory>

Examples:

Example 1: Starting package discovery
<sutra_memory>
<add_history>Used list_files to explore project structure. Found Server/pom.xml and Frontend/package.json files in current project</add_history>
</sutra_memory>

Example 2: Package file analysis
<sutra_memory>
<task>
<add id="2" to="pending">Use search_keyword tool with pattern 'require\\('axios'\\)|import.*from.*'axios'|import.*axios|axios' and regex=true to find axios import statements. Look for HTTP client library imports enabling requests to other services.</add>
</task>
<add_history>Found package.json file and it contains axios package which is an HTTP client library.</add_history>
</sutra_memory>

Example 3: Task completion scenario (only mark as completed when it is fully executed)
<sutra_memory>
<task>
<move from="current" to="completed">1</move>
</task>
<add_history>Used attempt_completion - provided summary of discovered packages and created tasks for subsequent import analysis</add_history>
</sutra_memory>

# Sutra Memory Guidelines:

1. Memory Assessment
In <thinking> tags, assess what package information you already have and what package files you need to analyze. Review your current sutra_memory state and determine what updates are needed based on package discovery progress.

2. First Iteration Protocol
- Start with list_files tool to explore project structure and identify package files
- Use database tool to examine package files and identify connection packages
- CRITICAL: Never create task lists without first analyzing package files
- Use tools systematically based on discovered packages

3. Task Management
- Create tasks with complete tool guidance: tool name, search patterns, regex parameters
- Include specific search patterns with proper escaping and context
- Provide comprehensive descriptions with expected import variations and tool parameters

4. Task Creation Guidelines
- Create tasks ONLY after package analysis is complete
- Include exact search patterns for import discovery
- Provide context about package purpose
- Use descriptive task names with clear objectives

5. History Best Practices
- Be specific about tools used and package files analyzed
- Mention key package discoveries and findings
- Note any failures or missing package files
- Include complete package names and file paths
- Track comprehensive package information for import discovery
- Write only what you did/found in the current iteration

6. Critical Rules
- Sutra Memory MUST be updated in every package discovery response alongside exactly one tool call
- At minimum, add_history must be included in each iteration
- Task IDs must be unique and sequential
- Tasks created here will be used in import pattern discovery
- Never create tasks without analyzing package file
- COMPLETION RULE: When using attempt_completion, mark package discovery as completed

Remember: Package discovery creates the foundation for import pattern discovery. Create comprehensive, actionable tasks based on actual package findings.
"""

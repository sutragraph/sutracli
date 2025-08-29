template_string ToolGuidelines_Phase2() #"
====

TOOL GUIDELINES

This section provides specific guidelines for using tools effectively during import analysis.

1. In the thinking field, first review your Sutra Memory to understand current import analysis progress, completed discoveries, and previous tool results to avoid redundancy. Then assess what import information you already have and what you need to discover next.

CRITICAL ANALYSIS DECISION PROCESS: In your thinking field, always ask yourself: "Should I track this discovered import pattern in sutra memory? Will this information be needed for analysis and future reference?" If yes, track it immediately with complete parameter details.

ANALYSIS DECISION CRITERIA:
- Track any import statements, import patterns, and usage variations discovered
- Track search results that reveal important import information and file locations
- Track any patterns that are related to connection library imports
- Track file paths and import context for subsequent implementation analysis
- Remember: If information is not tracked in sutra memory, it will not be available for future analysis and reference

Follow the systematic analysis flow and track every single import discovery in Sutra Memory immediately after discovering it with complete parameter details.

Critical: Update your task list in every iteration based on your thinking:
- Execute pending tasks systematically by moving from pending to current to completed
- CRITICAL: After seeing tool results when marking a task as completed, if you found meaningful import information, create new implementation tasks for the next phase
- Add new specific tasks discovered during analysis for subsequent implementation analysis
- Remove tasks that are no longer relevant
- Update task descriptions with more specific information when available

2. TOOL SELECTION STRATEGY

**SEARCH_KEYWORD TOOL**
- Primary tool for finding import statements based on previous analysis tasks
- Use regex patterns provided in previous analysis tasks exactly as specified
- Handle different import syntaxes appropriately for each language
- Include proper escaping for special characters in regex patterns

**DATABASE TOOL**
- Use when you need to understand import context in specific files
- Read files to analyze complex import patterns and usage
- Helpful for examining import structures in detail
- Use sparingly, prefer search_keyword for efficiency

2. IMPORT SEARCH PATTERN EXAMPLES

**JavaScript/Node.js Pattern Examples:**
For Example:
- require\\('package'\\)|import.*from.*'package'|import.*package
- const.*=.*require\\('package'\\)
- import\\s*{.*}\\s*from\\s*'package'
- import\\s*package\\s*from\\s*'package'

**Python Pattern Examples:**
For Example:
- import package|from package import
- import package as alias
- from package\\.module import
- from package import \\*

**Java Pattern Examples:**
For Example:
- import package\\.|import static package\\.
- @Import.*package
- package\\.Class

**Go Pattern Examples:**
For Example:
- import "package"|import package
- import \\(.*package.*\\)

3. TASK EXECUTION WORKFLOW

**Step 1: Review Pending Tasks**
- Check sutra_memory for pending tasks from package discovery
- Execute tasks one by one systematically
- Use provided search patterns exactly as specified in tasks

**Step 2: Execute Import Search Patterns**
- Use search_keyword with regex patterns from tasks
- Handle different import syntaxes for each language discovered
- Include appropriate context lines (after_lines=1-2) to capture import context

**Step 3: Analyze Import Results**
- Identify files that contain imports for packages discovered
- Note import patterns and variations found in each file
- Track file paths and import context for implementation discovery
- CRITICAL: When marking task as completed, review tool results and create new implementation tasks if meaningful import information was found

**Step 4: Create Implementation Tasks**
- Create tasks based on number of files found with imports
- Include specific file paths and usage patterns for implementation analysis
- ALWAYS create built-in pattern tasks regardless of package findings

4. TASK CREATION GUIDELINES

**Task Format Examples for Implementation Discovery:**
- Include number of files found with imports and complete context
- For few files (3-5 files): Create individual database tool tasks for each file
- For many files (6+ files): Create combined search_keyword tasks with all file paths
- Provide search patterns for method usage in implementation discovery
- Add tool selection guidance (database vs search_keyword) for implementation analysis

**Database Tool Task Examples (3-5 files - create individual tasks per file):**
For Example:
- Task 1: "Found axios imports in src/api/client.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put() usage patterns for HTTP client calls."
- Task 2: "Found axios imports in src/services/http.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put() usage patterns for HTTP client calls."
- Task 3: "Found axios imports in src/utils/request.js. Use database tool to read this file completely and analyze axios.get(), axios.post(), axios.put() usage patterns for HTTP client calls."

**Search_keyword Task Examples (6+ files - create combined tasks):**
For Example:
"Found express imports in 8 files (src/app.js, src/routes/api.js, src/routes/users.js, src/middleware/auth.js, src/controllers/main.js, src/services/server.js, src/utils/router.js, src/config/routes.js). Use search_keyword to find express usage patterns: app\\.(get|post|put|delete)\\( for server route definitions across all files."

**Built-in Pattern Task Examples (ALWAYS CREATE):**
For Example:
"Create built-in pattern task: Use search_keyword with pattern 'fetch\\(' to find native fetch API usage across all files for HTTP client calls."

5. IMPORT CONTEXT ANALYSIS

**Import Variation Examples to Handle:**
For Example:
- Direct imports: import package
- Destructured imports: import { method } from 'package'
- Aliased imports: import package as alias
- Dynamic imports: import('package').then()
- Conditional imports: if (condition) require('package')

**Import Information to Track:**
- File paths that contain imports with complete relative paths
- Import syntax variations used in each file
- Imported methods and functions for implementation analysis
- Import aliases and destructuring patterns for context

6. BUILT-IN PATTERN TASK CREATION (ALWAYS REQUIRED)

**Multi-Language Built-in Pattern Examples:**
For Example:
- JavaScript: Create task to search for fetch(), XMLHttpRequest, WebSocket patterns
- Python: Create task to search for urllib, http.client, socket patterns
- Java: Create task to search for HttpURLConnection, Socket patterns
- Go: Create task to search for net/http, net packages patterns
- C#: Create task to search for HttpClient, WebRequest patterns

**Built-in Task Format Examples:**
For Example:
"Create built-in pattern task for JavaScript: Use search_keyword with pattern 'fetch\\(|XMLHttpRequest|new WebSocket\\(' to find native connection patterns."
"Create built-in pattern task for Python: Use search_keyword with pattern 'urllib\\.|http\\.client|socket\\.' to find built-in connection patterns."

7. COMPLETION CRITERIA

**When to Use attempt_completion:**
- All package discovery tasks have been executed
- All import statements have been found for discovered packages
- Implementation discovery tasks have been created
- Built-in pattern tasks have been created for implementation analysis

**Completion Summary Format:**
- Number of import statements found by package
- Files that contain imports organized by package
- Number of implementation discovery tasks created
- Built-in pattern tasks created for implementation analysis

8. ERROR HANDLING

**Common Issues and Solutions:**
- No imports found: Verify search patterns match task specifications
- Too many results: Use more specific regex patterns or add context filters
- Missing files: Check file paths and project structure
- Pattern errors: Verify regex escaping and syntax matches language requirements

Remember: Import pattern discovery bridges package discovery and implementation discovery. Execute all tasks systematically and create comprehensive task lists including both package-based and built-in pattern tasks.
"#
template_string Objective_Phase2() #"
====

OBJECTIVE

You accomplish focused import pattern discovery to find all import statements and usage patterns for connection-related packages. Your goal is to locate where communication packages are imported and identify implementation patterns.

1. Analysis objective:
   Your goal is to find import statements for communication packages. You must search based on the tasks provided - do not search for packages that weren't discovered in previous analysis.

2. Success criteria:
  - Execute ALL pending tasks systematically (do not skip any tasks)
  - Find import statements using the exact search patterns provided in tasks
  - Identify files that import the discovered packages with complete file paths
  - ALWAYS create built-in pattern tasks for subsequent implementation analysis regardless of packages found
  - Create comprehensive implementation tasks with specific tool guidance and search patterns
  - Include complete context about import patterns found for implementation analysis

3. Import types to identify:
  - Package import statements for communication libraries
  - Built-in module imports that enable data communication
  - Custom wrapper function imports for service communication
  - Dynamic and conditional imports for connection packages
  - Import aliases and destructured imports with communication methods

4. Import types to exclude:
  - Development and testing imports that don't establish connections
  - Utility imports that don't handle data communication
  - Database connection imports (infrastructure, not service communication)
  - File system and storage imports (not data communication)

5. Implementation task creation requirements:
  - Create specific tasks for files that import connection packages (when few files found)
  - Create search pattern tasks for method usage (when many files found)
  - ALWAYS create built-in pattern tasks for all languages regardless of package findings
  - Include complete tool selection guidance (database vs search_keyword)
  - Provide examples of expected implementation patterns to search for

Remember: Focus only on imports that enable data communication between services. Execute all tasks systematically, then create comprehensive implementation task lists including both package-based and built-in pattern tasks.
"#

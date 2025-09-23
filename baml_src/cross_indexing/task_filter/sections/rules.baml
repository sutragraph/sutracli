template_string Rules_TaskFilter() #"
# Task Filtering Rules

## Duplicate Detection Rules

1. Pattern Similarity: Tasks with similar regex patterns for the same tool are likely duplicates
  - Example: `'import.*axios|from.*axios'` vs `'axios'`
  - The second pattern includes the first, so they should be merged

2. Tool Consistency: Tasks using the same tool with similar objectives should be evaluated for merging
  - Multiple `search_keyword` tasks for the same/similar package/library/technology can be merged
  - `database` tasks should NOT be merged when they target different file paths - each file needs separate analysis
  - Only merge `database` tasks when they target the same file path

## Merging Guidelines

1. Search Keyword Tasks: When merging search_keyword tasks, include all unique pattern components
  - Combine: `pattern1|pattern2|pattern3` ensuring no duplicates
  - Keep the most comprehensive pattern that covers all cases
  - Only merge when patterns are related to the same technology/objective

2. Database Tasks: DO NOT merge database tasks with different file paths
  - Each file requires individual analysis
  - Only merge database tasks targeting the same file with similar objectives
  - Preserve specific file paths in task descriptions

3. Maintain Tool Specificity: Keep tool-specific parameters and options
  - Preserve `regex=true` flags
  - Maintain file path specifications for database tools
  - Keep search scope definitions
  - Never lose file path information when merging

4. Enhance Descriptions: Improve merged task descriptions to be more comprehensive
  - Include all original objectives
  - Add context about what the search should find
  - Specify expected outcomes
  - Preserve file paths for database tasks

5. When file paths are same in multiple database tasks, merge them into one task with combined objectives.

## Output Requirements

1. Use JSON Format: All output must use proper JSON format
2. Sequential Task IDs: Assign new sequential task IDs starting from 1

## Quality Checks

1. No Functionality Loss: Verify all original search patterns and objectives are covered
2. Logical Grouping: Ensure merged tasks make logical sense together
3. Clear Descriptions: Task descriptions should be clear and actionable
4. Appropriate Granularity: Don't over-merge unrelated tasks, maintain reasonable task separation
"#

template_string Rules_TaskFilter() #"
# Task Filtering Rules

## Duplicate Detection Rules

1. Pattern Similarity: Tasks with similar regex patterns for the same tool are likely duplicates
   - Example: `'require\\('axios'\\)|import.*axios'` vs `'require\\('axios'\\)|import.*from.*'axios'|import.*axios'`
   - The second pattern includes the first, so they should be merged

2. Tool Consistency: Tasks using the same tool with similar objectives should be evaluated for merging
   - Multiple `search_keyword` tasks for the same/similar package/library/technology
   - Multiple `database` tasks for the same file analysis

3. Description Overlap: Tasks with significant description overlap (>80% similarity) should be merged

## Merging Guidelines

1. Preserve All Patterns: When merging search tasks, include all unique pattern components
   - Combine: `pattern1|pattern2|pattern3` ensuring no duplicates
   - Keep the most comprehensive pattern that covers all cases

2. Maintain Tool Specificity: Keep tool-specific parameters and options
   - Preserve `regex=true` flags
   - Maintain file path specifications
   - Keep search scope definitions

3. Enhance Descriptions: Improve merged task descriptions to be more comprehensive
   - Include all original objectives
   - Add context about what the search should find
   - Specify expected outcomes

## Output Requirements

1. Use JSON Format: All output must use proper JSON format
2. Sequential Task IDs: Assign new sequential task IDs starting from 1

## Quality Checks

1. No Functionality Loss: Verify all original search patterns and objectives are covered
2. Logical Grouping: Ensure merged tasks make logical sense together
3. Clear Descriptions: Task descriptions should be clear and actionable
4. Appropriate Granularity: Don't over-merge unrelated tasks, maintain reasonable task separation
"#

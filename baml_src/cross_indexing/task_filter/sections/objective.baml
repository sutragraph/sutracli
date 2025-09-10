template_string Objective_TaskFilter() #"
# Objective

Your primary objective is to analyze a list of tasks created by a cross-indexing phase and produce a clean, optimized task list by:

1. Identifying Duplicates: Find tasks that are essentially the same but may have minor differences in wording or patterns
2. Merging Similar Tasks: Combine similar tasks into single, comprehensive tasks that cover all necessary functionality
3. Optimizing Descriptions: Improve task descriptions for clarity and completeness while maintaining all original intent
4. Preserving Functionality: Ensure no important functionality or search patterns are lost during deduplication
5. Creating Clean Output: Generate a new task list in JSON format that eliminates redundancy

The goal is to reduce task redundancy while maintaining complete coverage of all necessary analysis work for the next phase.
"#

template_string RoadmapSutraMemoryPrompt() #"
## SUTRA MEMORY

Use this persistent memory to store data critical for future iterations of development tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

### Guidelines

- Include `add_history` in every response to log any new, relevant data for the next iteration (e.g., code changes, task outcomes, blockers, configurations). Structure as a concise, freeform string capturing deltas only, avoiding repetition.
- Use tracing actions when you need to analyze call chains and understand how code flows from entry points to terminal operations (DB, File, Network, etc.)
- Prioritize storing code snippets that you think would be usefull in future iterations so you won't need to open the same file again and again.
"#

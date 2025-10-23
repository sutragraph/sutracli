template_string DeveloperSutraMemoryPrompt() #"
## SUTRA MEMORY

Use this persistent memory to store data critical for future iterations of development tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

### Guidelines

Include `add_history` in every response to log any new, relevant data for the next iteration (e.g., code changes, bug details, task outcomes, blockers, configurations). Structure as a concise, freeform string capturing deltas only, avoiding repetition.
"#

template_string DeveloperSutraMemoryPrompt() #"
# Sutra Memory

Use this persistent memory to store data critical for future iterations of development tasks. Prioritize actionable, task-specific information to maintain context and avoid redundant work.

## Sutra Memory Guidelines:

- Include `add_history` in every response to log any new, relevant data for the next iteration (e.g., code changes, task outcomes, blockers, configurations). Structure as a concise, freeform string capturing deltas only, avoiding repetition.
- Capture important actions, findings, and tool usages from the current iteration.
- At minimum, add_history must be included in each iteration
- History is useful for your next tool call decisions to avoid repeating the same tool calls and important files to look at.
- Task descriptions must be detailed and self-contained so you can execute them without requiring additional context discovery

"#

template_string TerminalToolTemplate() #"
## terminal

Executes a shell one-liner and returns the combined output.

This tool spawns a process using the user's shell, reads from stdout and stderr (preserving the order of writes), and returns a string with the combined output result. Each invocation spawns a new shell process, so you can't rely on state from previous invocations.

Use the `cwd` parameter to navigate to one of the root directories of the project. Do not include directory changes in the command itself.

Required Parameters:
  - `command`: The one-liner command to execute.

Optional Parameters:
  - `cwd`: Working directory for the command. This must be one of the root directories of the project.
"#

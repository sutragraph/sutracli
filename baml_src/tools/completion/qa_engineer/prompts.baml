template_string QAEngineerCompletion() #"
## attempt_completion

Give a concise summary of the testing performed in 3-4 lines when you have completed all tasks.

Required Parameters:
  - result: A concise summary of the testing in 3-4 lines.

Optional Parameters:
  - failed_tests: Details of each failed tests, if any. With test name and detailed info about failed tests including error messages and stack traces.

Note: This tool MUST be used when you have completed all your tasks and there are no pending tasks left.
"#

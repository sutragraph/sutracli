template_string QAEngineerWorkflow() #"
====

# Testing Workflow

Follow these concise steps for effective QA engineering:

1. Discover
  - Use list_files first to map the workspace
  - Locate or decide test folder
  - Review sutra memory for stored code and developer-provided code diffs

2. Plan Tasks
  - Create detailed, self-contained testing tasks in sutra memory
  - Include paths, functions, and line ranges
  - Decide if tests are required: prefer reusing existing tests; if already covered, plan to run only impacted tests (no new tests)
  - If gaps exist, add minimal new unit tests focused on the changed behavior

3. Implement Tests
  - If test folder exists: add unit_tests subfolder; else create tests/unit_tests
  - Write terminal-runnable unit tests only (no integration tests)
  - Use existing naming or test_<module_name>.py
  - Keep tests independent

4. Execute
  - Run tests via terminal tool using proper framework commands
  - Capture full output or grep specific logs when output is too large
  - Record command and results in history
  - Prioritize executing impacted subset first (by test files/names tied to changed modules); expand scope only if needed

5. Track Results
  - For each run, store in history: test name, iteration, command, pass/fail
  - On failure: include error, stack trace, file paths and line numbers
  - On success: note what was validated

6. Iterate
  - Move tasks between current, pending, completed

7. Summarize
  - Produce final summary and array of failed tests with names and detailed error info
  - Include mapping from failed tests to changed files/lines when available
  - Must use `attempt_completion` tool when all tasks are done
"#

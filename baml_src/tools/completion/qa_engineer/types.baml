class QAEngineerCompletionParams {
  result string @description("A concise summary of the testing in 3-4 lines.")
  failed_tests QAEngineerFailedTestsParams[]? @description("Details of each failed test, if any. Include test name, error messages, stack traces, and all relevant information (logs, assertions, expected vs actual values) needed for developers to diagnose and fix the issues.")
}

class QAEngineerFailedTestsParams {
  test_name string @description("Name of the failed test.")
  test_details string @description("Detailed info about the failed test including error messages and stack traces.")
}

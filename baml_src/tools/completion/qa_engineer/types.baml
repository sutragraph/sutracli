
class QAEngineerCompletionParams {
  summary string @description("A concise summary of the testing.")
  failed_tests QAEngineerFailedTestsParams[]? @description("Details of each failed tests, if any.")
}

class QAEngineerFailedTestsParams {
  test_name string @description("The name of the failed test")
  test_details string @description("Detailed info about failed tests including error messages and stack traces")
}

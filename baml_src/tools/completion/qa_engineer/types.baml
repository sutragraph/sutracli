
class QAEngineerCompletionParams {
  result string
  failed_tests QAEngineerFailedTestsParams[]?
}

class QAEngineerFailedTestsParams {
  test_name string
  test_details string
}

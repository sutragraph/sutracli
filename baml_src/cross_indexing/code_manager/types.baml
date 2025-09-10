class CodeManagerResponse {
  thinking string?
  connection_code CodeConnection[]?
}

class CodeConnection {
  id string
  file string
  start_line int
  end_line int
  description string
}

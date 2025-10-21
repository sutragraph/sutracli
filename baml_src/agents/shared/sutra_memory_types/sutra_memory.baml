enum TaskStatus {
  PENDING @alias("pending")
  CURRENT @alias("current")
  COMPLETED @alias("completed")
}

enum TaskOperationAction {
  Add @alias("add")
  Move @alias("move")
}

class TaskOperation {
  action TaskOperationAction
  id string
  to_status TaskStatus?
  description string?
}

enum CodeStorageAction {
  Add @alias("add")
  // Remove @alias("remove")
}

class CodeStorage {
  action CodeStorageAction
  id string
  file string?
  start_line int?
  end_line int?
  description string?
}

class SutraMemoryParams {
  add_history string
  tasks TaskOperation[]?
  code CodeStorage[]?
}

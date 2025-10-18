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
  action TaskOperationAction @description("The action to be performed on the task list. (add|move)")
  id string @description("Unique identifier for the task")
  to_status TaskStatus? @description("To move the task from one status to another (pending|current|completed)")
  description string? @description("Brief description of the task with precise details")
}

enum CodeStorageAction {
  Add @alias("add")
  Remove @alias("remove")
}

class CodeStorage {
  action CodeStorageAction @description("The action to be performed on the code snippet")
  id string @description("Unique identifier for the code snippet")
  file string? @description("File path for the code snippet")
  start_line int? @description("Starting line number of the code snippet")
  end_line int? @description("Ending line number of the code snippet")
  description string? @description("Description of the code snippet")
}

class SutraMemoryParams {
  add_history string @description("Comprehensive summary of current iteration actions, tool usage")
  tasks TaskOperation[]? @description("The action to be performed on the task list")
  code CodeStorage[]? @description("The action to be performed on code snippets")
}

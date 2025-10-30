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
  action TaskOperationAction @description("The action to perform on the task: 'add' to create a new task, 'move' to change the status of an existing task")
  id int @description("Unique number for the task 1-based index")
  to_status TaskStatus? @description("The status to move the task to Required if action is 'move'")
  description string? @description("Description of the task Required if action is 'add'")
}

enum CodeStorageAction {
  Add @alias("add")
  // Remove @alias("remove")
}

class CodeStorage {
  action CodeStorageAction @description("The action to perform on the code snippet: 'add' to store a new code snippet")
  id int @skip //skipping for now cuz remove is not being used and for add its auto generated
  file string @description("File path where the code snippet is located")
  start_line int @description("Starting line number of the code snippet")
  end_line int @description("Ending line number of the code snippet")
  description string @description("Description for the code snippet")
}

class SutraMemoryParams {
  add_history string @description("Comprehensive summary of current iteration actions, tool usage, and implementation discoveries")
  tasks TaskOperation[]? @description("Manage analysis tasks by executing tasks and creating additional tasks when needed")
  code CodeStorage[]? @description("Store code details which is important for future tasks")
}

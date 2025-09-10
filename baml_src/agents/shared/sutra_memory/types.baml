// Sutra Memory System Types
// Persistent working memory across conversation iterations
// Only includes classes used by SutraMemoryParams

// Task status enum
enum TaskStatus {
  PENDING @alias("pending")
  CURRENT @alias("current")
  COMPLETED @alias("completed")
}

// Task operation actions
enum TaskOperationAction {
  Add @alias("add")
  Move @alias("move")
}

// Code storage actions
enum CodeStorageAction {
  Add @alias("add")
}

// Task Management Types
class TaskOperation {
  action TaskOperationAction // "add" | "move" | "remove"
  id string
  from_status TaskStatus? // for "move" operations
  to_status TaskStatus? // for "add" and "move" operations
  description string? // optional - required for "add" operations, not needed for "move"
}

// Code Storage Types
class CodeStorage {
  action CodeStorageAction
  id string
  file string // file path for the code snippet
  start_line int
  end_line int
  description string
}

// Main Sutra Memory Structure
// This is the main class that agents must return
class SutraMemoryParams {
  add_history string       // mandatory field - required in every response
  tasks TaskOperation[]?   // optional task operations
  code CodeStorage[]?      // optional code snippet operations
}

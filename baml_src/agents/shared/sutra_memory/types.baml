// Sutra Memory System Types
// Persistent working memory across conversation iterations

enum TaskOperationAction  {
  Add
  Remove
  Move
}

// Task Management Types
class TaskOperation {
  action TaskOperationAction // "add" | "move" | "remove"
  id string
  from_status string? // for "move" operations: "pending" | "current" | "completed"
  to_status string? // for "add" and "move" operations: "pending" | "current" | "completed"
  description string
}

enum CodeStorageAction{
  Add
  Remove
}

// Code Storage Types
class CodeStorage {
  action CodeStorageAction
  id string
  file string
  start_line int
  end_line int
  description string
  project string?
}

// File Change Tracking Types
class FileChanges {
  modified string[]?
  added string[]?
  deleted string[]?
}

// Main Sutra Memory Structure
class SutraMemoryParams {
  add_history string // mandatory field - required in every response
  tasks TaskOperation[]?
  code CodeStorage[]?
  files FileChanges?
}

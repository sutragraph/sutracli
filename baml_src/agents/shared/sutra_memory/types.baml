// Sutra Memory System Types
// Persistent working memory across conversation iterations

// Task Management Types
class TaskOperation {
  action string // "add" | "move" | "remove"
  id string
  from_status string? // for "move" operations: "pending" | "current" | "completed"
  to_status string? // for "add" and "move" operations: "pending" | "current" | "completed"
  description string
}

// Code Storage Types
class CodeStorage {
  action string // "add" | "remove"
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

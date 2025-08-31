class SystemInfo_CrossIndexing {
  home string
  current_dir string
}

class CompletionToolCall_CrossIndexing {
  tool_name "attempt_completion"
  parameters CompletionResponse_CrossIndexing
}

type ToolCall_CrossIndexing = ListFilesToolCallWithoutProjectName | DatabaseToolCall | SearchKeywordToolCallWithoutProjectName | CompletionToolCall_CrossIndexing

class CrossIndexingResponse {
  thinking string?
  tool_call ToolCall_CrossIndexing?
  sutra_memory SutraMemoryParams_CrossIndexing
}

// -----------------------------------------------
// Sutra Memory (for Phase 1, 2 and 3)
// -----------------------------------------------

enum TaskOperationAction_CrossIndexing  {
  Add @alias("add")
  Remove @alias("remove")
  Move @alias("move")
}

enum Status_CrossIndexing {
  Pending @alias("pending")
  Current @alias("current")
  Completed @alias("completed")
}

// Task Management Types
class TaskOperation_CrossIndexing {
  action TaskOperationAction_CrossIndexing // "add" | "move" | "remove"
  id string
  from_status Status_CrossIndexing? // for "move" operations: "pending" | "current" | "completed"
  to_status Status_CrossIndexing? // for "add" and "move" operations: "pending" | "current" | "completed"
  description string?
}

enum CodeStorageAction_CrossIndexing{
  Add @alias("add")
  Remove @alias("remove")
}

// Code Storage Types
class CodeStorage_CrossIndexing {
  action CodeStorageAction_CrossIndexing
  id string
  file string
  start_line int
  end_line int
  description string
}

// Main Sutra Memory Structure
class SutraMemoryParams_CrossIndexing {
  add_history string // mandatory field - required in every response
  tasks TaskOperation_CrossIndexing[]?
  code CodeStorage_CrossIndexing[]?
}

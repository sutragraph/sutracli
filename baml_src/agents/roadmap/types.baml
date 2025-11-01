class RoadmapCompletionToolCall {
  tool_name "attempt_completion"
  parameters RoadmapCompletionParams | BaseCompletionParams
}

type RoadmapToolCall = DatabaseToolCallSimple | SearchKeywordToolCallWithProjectName | SemanticSearchToolCallWithProjectName | ListFilesToolCallWithProjectName | RoadmapCompletionToolCall

class RoadmapPromptParams {
  context string
  system_info SystemInfoParams
  project_context ProjectContext
}


class RoadmapResponse {
  thinking string @description("Concise user-facing progress update for the UI (one sentence).")
  sutra_memory RoadmapSutraMemoryParams @description("Persistent memory for code snippets, task updates, and history.")
  tool_call RoadmapToolCall? @description("Next tool to invoke with parameters.")
}

// Code storage actions - move-only tracing actions (no removals allowed)
enum RoadmapCodeStorageAction {
  Add @alias("add")
  UpdateTracingStatus @alias("update_tracing_status")
  MoveToTraced @alias("move_to_traced")
  AddToNeedsTracing @alias("add_to_needs_tracing")
  UpdateCallChainSummary @alias("update_call_chain_summary")
}

// Types of final operations (endpoints of call chains)
// Types of code elements that can be traced
enum ElementType {
  FUNCTION @alias("function")
  PROPERTY @alias("property")
  VARIABLE @alias("variable")
  ATTRIBUTE @alias("attribute")
  METHOD @alias("method")
  CLASS @alias("class")
}

// Hierarchical traced element representing the actual call tree structure
class TracedElement {
  id string? @description("Auto-generated unique identifier for the element. Required for 'update_tracing_status', 'move_to_traced', 'add_to_needs_tracing', and 'update_call_chain_summary' actions.")
  name string @description("Name of the element being traced (function name, property name, variable name, etc.)")
  element_type ElementType @description("Type of code element (function, method, property, variable, attribute)")
  start_line int @description("Starting line number of the element in the file")
  end_line int @description("Ending line number of the element in the file")
  signature string @description("Function/method signature (e.g., 'def func(x, y)') or variable/property definition (e.g., 'const value = ...')")
  content string @description("Complete code content of this element for reference")
  accessed_elements TracedElement[]? @description("Array of child elements that this element directly calls, accesses, or uses. Forms the hierarchical call chain tree.")
  is_fully_traced bool? @description("Whether all child elements in accessed_elements have been traced to their finals. True only when entire subtree is complete.")
}

// Code elements that still need trace chain analysis
class UntracedElement {
  id string @skip @description("Auto-generated unique identifier for this untraced element (e.g., 'elem_001')")
  name string @description("Name of the element that needs tracing (function, method, property, variable, attribute)")
  element_type ElementType @description("Type of code element that requires tracing")
  reason string? @description("Why this element needs tracing (e.g., 'called_in_main_flow', 'accessed_in_property', 'returned_from_function')")
  accessed_from string? @description("Name or ID of the parent element that accesses/calls this element")
}

// Code Storage Types - enhanced for comprehensive trace chain analysis
class RoadmapCodeStorage {
  action RoadmapCodeStorageAction @description("The action to perform on the code snippet")
  id int @description("Unique identifier of the code snippet. Required for all actions.")
  file string @description("Absolute file path where the code snippet is located. Required for 'add' action.")
  start_line int @description("Starting line number of the code snippet. Required for 'add' action.")
  end_line int @description("Ending line number of the code snippet. Required for 'add' action.")
  description string @description("Brief description of the code snippet's purpose. Required for 'add' action.")
  is_traced bool? @description("Whether all trace chains reach finals (DB/File/Net/Mem/Sys/Logic). True only when needs_tracing is empty. Used with 'add' and 'update_tracing_status' actions.")
  root_element TracedElement? @description("Hierarchical tree of traced elements showing complete call chains from entry point to finals. Used with 'add' action.")
  needs_tracing UntracedElement[]? @description("Elements requiring tracing (functions, methods, properties, variables, attributes). Keep under 20 items. Used with 'add' and 'add_to_needs_tracing' actions.")
  traced_element TracedElement? @description("Single traced element being moved from needs_tracing to hierarchy. Used with 'move_to_traced' action.")
  source_element_id string? @description("ID of the needs_tracing element being moved (e.g., 'elem_001'). Used with 'move_to_traced' action.")
  element_path string[]? @description("Path of element IDs defining insertion location in hierarchy. Empty [] = root, ['elem_001'] = child, ['elem_001', 'elem_002'] = grandchild. Used with 'move_to_traced' action.")
  call_chain_summary string? @description("Readable trace chain summary with [✓] for traced elements. Format: 'entryFunc → func[✓] → [DATABASE + FILE_IO]'. Used with 'update_call_chain_summary' action.")
}

class RoadmapSutraMemoryParams {
  add_history string @description("Comprehensive summary of current iteration actions, tool usage, and implementation discoveries")
  tasks TaskOperation[]? @description("Manage analysis tasks by executing tasks and creating additional tasks when needed")
  code RoadmapCodeStorage[]? @description("Store code details which is important for future tasks")
}

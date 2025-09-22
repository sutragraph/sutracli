// Sutra Memory System Types
// Call chain tracing for complete code element analysis
// Focus on tracing all code elements (functions, properties, variables, attributes) until final operations

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

// Code storage actions - move-only tracing actions (no removals allowed)
enum CodeStorageAction {
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
  id string?                       // Unique identifier for this element in the hierarchy (auto-generated if not provided)
  name string                       // Element name (function, property, variable, etc.)
  element_type ElementType          // Type of element being traced
  start_line int                   // Starting line number
  end_line int                     // Ending line number
  signature string                // Element signature (for functions/methods) or definition (for variables/properties)
  content string                  // Complete code content for this element (for showing full code blocks)
  accessed_elements TracedElement[]? // Child elements that this element directly accesses (hierarchical tree)
  is_fully_traced bool?            // Whether all child elements have been traced to completion
}

// Code elements that still need trace chain analysis
class UntracedElement {
  id string?                       // Unique identifier for this element (auto-generated if not provided)
  name string                      // Element name that needs tracing (function, property, variable, etc.)
  element_type ElementType         // Type of element that needs tracing
  reason string?                   // Why this needs tracing (e.g., "called_in_main_flow", "accessed_in_property", "assigned_from_return")
  accessed_from string?            // Which element accesses this
}

// Task Management Types
class TaskOperation {
  action TaskOperationAction
  id string
  from_status TaskStatus?
  to_status TaskStatus?
  description string?
}

// Code Storage Types - enhanced for comprehensive trace chain analysis
class CodeStorage {
  action CodeStorageAction
  id string
  file string?                           // file path for the code snippet (only needed for Add action)
  start_line int?                        // starting line number (only needed for Add action)
  end_line int?                          // ending line number (only needed for Add action)
  description string?                    // description (only needed for Add action)
  is_traced bool?                        // whether trace chains have been fully analyzed (for UpdateTracingStatus and Add action)
  root_element TracedElement?            // hierarchical tree of traced elements starting from the main element (for Add action)
  needs_tracing UntracedElement[]?       // array of elements needing tracing (for Add and AddToNeedsTracing actions)
  traced_element TracedElement?          // single traced element to add to the hierarchy (for MoveToTraced action)
  source_element_id string?              // ID of the needs_tracing element being moved (for MoveToTraced action)
  element_path string[]?                 // path of element IDs to where the traced_element should be inserted in the hierarchy
  call_chain_summary string?             // updated trace chain summary (for UpdateCallChainSummary)
}

// Main Sutra Memory Structure
class SutraMemoryParams {
  add_history string               // mandatory field - required in every response
  tasks TaskOperation[]?           // optional task operations
  code CodeStorage[]?              // optional code snippet operations
}

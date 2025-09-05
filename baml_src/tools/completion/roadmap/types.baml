// Roadmap Completion Tool Types - Simple and flexible structure

enum FileOperation {
  Create @alias("create")
  Modify @alias("modify")
  Delete @alias("delete")
}

enum ImpactLevel {
  High @alias("High")
  Medium @alias("Medium")
  Low @alias("Low")
  NoImpact @alias("None")
}



class ContractField {
  name string
  type string
  required bool
  description string?
  validation_rules string?
}

class Contract {
  contract_id string              // Unique identifier for this contract
  contract_type string            // Type of contract (api, function, database, event, etc.)
  name string                     // Contract name/title
  description string              // What this contract defines

  // Interface specification (generic key-value pairs for contract-specific details)
  // Examples:
  // API: {"endpoint": "/api/users", "method": "POST"}
  // Function: {"function_name": "getUserById", "module": "user_service"}
  // Database: {"table": "users", "operation": "insert"}
  // Event: {"event_name": "user_created", "channel": "user_events"}
  interface map<string, string>   // Contract-specific interface details

  // Contract specifications
  input_format ContractField[]?   // Input data structure
  output_format ContractField[]?  // Output data structure
  error_codes string[]?           // Possible error codes/messages

  // Additional contract details
  validation_rules string?        // Validation requirements
  examples string?                // Usage examples
}

class ChangeInstruction {
  description string               // What needs to be changed
  current_state string?           // Current implementation (if exists)
  target_state string             // Target implementation
  start_line int?                 // Starting line number for this change
  end_line int?                   // Ending line number for this change (if range)
  additional_notes string?        // Any gotchas or special considerations
}

class FileChange {
  file_path string
  operation FileOperation         // File operation to perform
  instructions ChangeInstruction[] // Multiple changes per file (array for multiple modifications)
}

class ProjectRoadmap {
  project_name string
  project_path string
  impact_level ImpactLevel         // Impact level of changes needed
  reasoning string                 // Why changes are needed for this project
  changes FileChange[]?            // List of files and their change instructions
  contracts Contract[]?            // Contracts this project must implement/follow
  implementation_notes string?     // Any additional context or gotchas for this project
}

class RoadmapCompletionParams {
  projects ProjectRoadmap[]        // List of project roadmaps
  summary string                   // Brief executive summary of overall strategy
}

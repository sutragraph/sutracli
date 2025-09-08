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
enum ContractRole {
  Provider @alias("provider")     // This project implements this contract
  Consumer @alias("consumer")     // This project uses this contract
  Both @alias("both")             // This project acts as both consumer and provider (e.g., proxy/middleware)
}

class ContractField {
  name string
  type string                     // string, integer, object, array, boolean
  required bool
  description string?
  validation string?              // "enum:day,month,date" | "format:YYYY-MM-DD" | "min:1,max:100"
  nested ContractField[]?         // For objects/arrays - only show structure, not all fields
}

class Contract {
  contract_id string
  contract_type string            // api, function, database, event
  name string
  description string              // One clear sentence
  role ContractRole               // Can be provider, consumer, or both (for intermediary/proxy projects)
  
  // Core interface
  interface map<string, string>   // Essential details only
  
  // Data structure (show key fields only)
  input_format ContractField[]?   
  output_format ContractField[]?  
  error_codes string[]?
  
  // Essential implementation details
  authentication_required bool?
  
  // Complete working examples (most important part)
  examples string                 // Success + Error examples with real data
  
  // Brief implementation guidance
  instructions string?
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
  implementation_plan string[]
  changes FileChange[]?            // List of files and their change instructions
  contracts Contract[]?            // Contracts this project must implement/follow

}

class RoadmapCompletionParams {
  projects ProjectRoadmap[]        // List of project roadmaps
  summary string                   // Brief executive summary of overall strategy
}

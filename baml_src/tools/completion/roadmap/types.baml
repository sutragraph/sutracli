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
  implementation_notes string?     // Any additional context or gotchas for this project
}

class RoadmapCompletionParams {
  projects ProjectRoadmap[]        // List of project roadmaps
  summary string                   // Brief executive summary of overall strategy
}

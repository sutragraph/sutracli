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

class IntegrationContract {
  contract_id string @description("Unique identifier for this integration contract")
  description string @description("Purpose and integration details explaining how projects coordinate")
  related_projects string[] @description("Array of project names that this contract connects")
  specifications string @description("High-level interface requirements and coordination points")
}

class ChangeInstruction {
  description string @description("What to accomplish at high level")
  guidance string? @description("Strategic direction on how to approach the change")
  integration_notes string? @description("How this change connects to other systems or contracts")
}

class FileChange {
  file_path string @description("Path relative to project root")
  operation FileOperation @description("Action to perform on the file")
  instructions ChangeInstruction[] @description("Array of high-level change guidance")
}

class ProjectExecutionPlan {
  project_name string @description("Human-readable project name")
  project_path string @description("Root directory path of the project")
  impact_level ImpactLevel @description("Impact level of changes to this project")
  reasoning string @description("Explanation of changes and why they're needed")
  implementation_plan string[] @description("High-level strategic steps describing what to accomplish (5-7 focused items)")
  changes FileChange[]? @description("Array of file modifications (omit if no changes)")
  integration_contracts IntegrationContract[]? @description("Array of integration contracts defining how this project coordinates with others")
}

class RoadmapCompletionParams {
  projects ProjectExecutionPlan[] @description("Array of project execution plans (omit projects with no changes or impact!)")
  summary string @description("Brief overall strategy")
}

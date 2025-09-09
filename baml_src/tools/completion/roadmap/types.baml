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
  Provider @alias("provider")
  Consumer @alias("consumer")
}

class ContractField {
  name string
  type string
  required bool
  description string?
  validation string?
  nested ContractField[]?
}

class Contract {
  contract_id string
  contract_type string
  name string
  description string
  role ContractRole
  interface map<string, string>
  input_format ContractField[]?
  output_format ContractField[]?
  error_codes string[]?
  authentication_required bool?
  examples string
  instructions string?
}

class ChangeInstruction {
  description string
  current_state string?
  target_state string
  start_line int?
  end_line int?
  additional_notes string?
}

class FileChange {
  file_path string
  operation FileOperation
  instructions ChangeInstruction[]
}

class ProjectRoadmap {
  project_name string
  project_path string
  impact_level ImpactLevel
  reasoning string
  implementation_plan string[]
  changes FileChange[]?
  contracts Contract[]?
}

class RoadmapCompletionParams {
  projects ProjectRoadmap[]
  summary string
}

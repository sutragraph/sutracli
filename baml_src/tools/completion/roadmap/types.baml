// Roadmap Completion Tool Types - Updated to match exact JSON structure

class ExecutiveSummary {
  scope string
  strategy string
  projects_affected string[]
  integration_points string[]
}

class ProjectImpact {
  level string // "High" | "Medium" | "Low" | "None"
  changes_required bool
  reasoning string
}

class FileModification {
  file_path string
  lines string
  current_state string
  target_state string
  implementation_steps string[]
  import_changes string[]?
}

class ApiContract {
  route string
  request map<string, string>
  response map<string, string>
  errors map<string, string>
}

class CrossProjectIntegration {
  calls_to string[]?
  called_by string[]?
  data_contracts string[]
  authentication string?
}

class DeploymentRequirements {
  deploy_order int
  prerequisites string[]
  testing_requirements string[]
}

class ProjectRoadmap {
  project_name string
  impact ProjectImpact
  file_modifications FileModification[]?
  api_contracts ApiContract[]?
  cross_project_integration CrossProjectIntegration?
  deployment_requirements DeploymentRequirements?
}

class DeploymentPhase {
  phase_number int
  project_name string
  description string
  dependencies string[]?
}

class IntegrationTesting {
  test_data_flow string[]
  api_contract_validation string[]
  error_handling_tests string[]
}

class RiskAssessment {
  breaking_changes string[]
  rollback_plan string[]
  monitoring_requirements string[]
}

class EcosystemCoordination {
  deployment_sequence DeploymentPhase[]
  integration_testing IntegrationTesting
  risk_assessment RiskAssessment
}


class RoadmapCompletionParams {
  executive_summary ExecutiveSummary
  project_roadmaps ProjectRoadmap[]
  ecosystem_coordination EcosystemCoordination
  success bool
  timestamp float
}

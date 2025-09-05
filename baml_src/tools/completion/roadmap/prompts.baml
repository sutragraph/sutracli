// Roadmap Completion Tool Prompts

template_string RoadmapCompletionToolTemplate() #"
  ====
    ## attempt_completion
    Description: Complete strategic roadmap analysis with simple project instructions. Each project contains a list of files and their change instructions that sub-agents can execute independently.

    Parameters:
    - projects: List of project roadmaps with file-level change instructions
    - summary: Brief executive summary of the overall roadmap strategy

    Project Parameters (for each project in projects array):
    - project_name: Human-readable project name
    - project_path: Exact path to the project directory
    - impact_level: ImpactLevel enum (High, Medium, Low, NoImpact)
    - reasoning: Detailed explanation of impact and why changes are needed
    - changes: (optional) Array of file changes with structured instructions
        * file_path: Path to the file that needs changes
        * operation: FileOperation enum (create, modify, delete)
        * instructions: Array of change instructions (multiple changes per file supported)
            - description, current_state, target_state, start_line, end_line, additional_notes
    - contracts: (optional) Array of contracts this project must implement or consume
        * contract_id: Unique identifier, contract_type: Type (api/function/database/etc), name: Contract name
        * description: What this contract defines, interface: Map of contract-specific details
        * input_format: Array of input fields, output_format: Array of output fields (list nested fields explicitly)
        * error_codes: Array of error codes
        * examples: Detailed success and error payloads (show all fields, including nested)
    - implementation_notes: (optional) Any additional context or gotchas for this project

    Parameter Examples:
    - Create new file: changes: [{"file_path": "src/auth/controller.py", "operation": "create", "instructions": [{"description": "Create authentication controller", "target_state": "New file with login endpoint and JWT handling"}]}]
    - Modify existing file: changes: [{"file_path": "src/auth/routes.py", "operation": "modify", "instructions": [{"description": "Add login route", "current_state": "No auth routes", "target_state": "POST /auth/login route", "start_line": 10, "end_line": 15}]}]
    - Multiple changes in one file: changes: [{"file_path": "src/models/user.py", "operation": "modify", "instructions": [{"description": "Add role field", "target_state": "role = models.CharField(max_length=50)", "start_line": 15}, {"description": "Update __str__ method", "current_state": "return self.username", "target_state": "return f'{self.username} ({self.role})'", "start_line": 25, "end_line": 26}]}]
    - Delete file: changes: [{"file_path": "src/legacy/old_auth.py", "operation": "delete", "instructions": [{"description": "Remove deprecated authentication module", "additional_notes": "Ensure no imports remain"}]}]
    - High impact project: projects: [{"project_name": "Core API", "project_path": "/api", "impact_level": "High", "reasoning": "Critical authentication changes"}]
    - With contracts: projects: [{"project_name": "Backend API", "project_path": "/backend", "impact_level": "High", "reasoning": "New user authentication API", "changes": [{"file_path": "src/auth/routes.py", "operation": "modify", "instructions": [{"description": "Add login endpoint", "target_state": "POST /api/auth/login endpoint", "start_line": 15}]}], "contracts": [{"contract_id": "auth-login-v1", "contract_type": "api", "name": "User Login API", "description": "Authenticate user credentials", "interface": {"endpoint": "/api/auth/login", "method": "POST"}, "input_format": [{"name": "email", "type": "string", "required": true}, {"name": "password", "type": "string", "required": true}], "output_format": [{"name": "token", "type": "string"}, {"name": "user", "type": "object", "required": true, "description": "Authenticated user", "validation_rules": "non-null"}], "error_codes": ["invalid_credentials", "server_error", "rate_limited"], "examples": "Success: {\"token\": \"jwt123\", \"user\": {\"id\": \"456\", \"email\": \"alice@example.com\", \"profile\": {\"first_name\": \"Alice\", \"last_name\": \"Smith\"}, \"roles\": [\"admin\", \"editor\"]}}; Error-invalid_credentials: {\"error\": \"invalid_credentials\", \"message\": \"Email or password is incorrect\"}; Error-rate_limited: {\"error\": \"rate_limited\", \"retry_after_seconds\": 30}"}]}]


    Usage Notes:
    - Each project roadmap is completely standalone - sub-agents only see their own project
    - Provide detailed instructions in the "instructions" field for each file
    - Include specific implementation details, line numbers, function signatures, etc.
    - Cover all types of changes: code, config, database, tests, documentation
    - Structure instructions with clear descriptions, current/target states, and specific line numbers
    - Support multiple changes per file using instructions array
    - Use FileOperation enum values (create/modify/delete) for file operations
    - Use ImpactLevel enum values (High/Medium/Low/NoImpact) for impact assessment
    - Make instructions clear enough for independent execution

    - Include contracts for cross-project integration points when multiple projects are involved
"#

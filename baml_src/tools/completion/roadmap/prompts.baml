// Roadmap Completion Tool Prompts

template_string RoadmapCompletionToolTemplate() #"
  ====
    ## attempt_completion
    **Description**: Complete a strategic roadmap analysis with simple, project-specific instructions. Each project roadmap contains a list of files and their corresponding change instructions, designed for sub-agents to execute independently.

    **Parameters**:
    - `projects`: A list of project roadmaps, each with file-level change instructions.
    - `summary`: A brief executive summary of the overall roadmap strategy.

    ---

    ### Project Parameters (for each project in the `projects` array)
    - `project_name`: A human-readable name for the project.
    - `project_path`: The exact path to the project's root directory.
    - `impact_level`: The level of impact the changes will have on this project, using the `ImpactLevel` enum (`High`, `Medium`, `Low`, `NoImpact`).
    - `reasoning`: A detailed explanation of why these changes are necessary for this project and the reasoning behind the assigned impact level.
    - `changes`: (Optional) An array of `FileChange` objects detailing the modifications.
        * `file_path`: The path to the file that needs changes, relative to the project path.
        * `operation`: The action to perform, using the `FileOperation` enum (`create`, `modify`, `delete`).
        * `instructions`: An array of `ChangeInstruction` objects. Multiple instructions can be provided for a single file.
            - `description`: What needs to be changed.
            - `current_state`: The existing implementation (if any).
            - `target_state`: The desired final implementation.
            - `start_line`, `end_line`: (Optional) The line numbers for the change.
            - `additional_notes`: (Optional) Any special considerations or potential issues.
    - `contracts`: (Optional) An array of `Contract` objects that this project must implement or consume, defining the interface between projects.
        * `contract_id`: A unique identifier for the contract (e.g., `auth-login-v1`).
        * `contract_type`: The type of contract (`api`, `function`, `database`, `event`).
        * `name`: A human-readable name for the contract.
        * `description`: A clear, one-sentence summary of the contract's purpose.
        * `role`: The project's role concerning this contract, using the `ContractRole` enum (`provider` if it implements the contract, `consumer` if it uses it).
        * `interface`: A map of essential details (e.g., `{"endpoint": "/api/v1/login", "method": "POST"}`).
        * `input_format`, `output_format`: (Optional) Arrays of `ContractField` objects that define the data structure. Each field has:
            - `name`, `type`, `required` (boolean).
            - `description` (optional).
            - `validation` (optional string, e.g., `"format:email"` or `"min:8"`).
            - `nested` (optional array of `ContractField` objects for nested structures).
        * `error_codes`: (Optional) An array of possible error strings (e.g., `["invalid_credentials", "server_error"]`).
        * `authentication_required`: (Optional) A boolean indicating if the contract requires authentication to use.
        * `examples`: A string containing complete, realistic examples for both success and error cases, including nested data.
        * `implementation_notes`: (Optional) Brief guidance or important details for implementing or consuming the contract.
    - `implementation_notes`: (Optional) Any additional high-level context or gotchas for the project as a whole.

    ---

    ### Parameter Examples
    -   **Create new file**: `changes: [{"file_path": "src/auth/controller.py", "operation": "create", "instructions": [{"description": "Create authentication controller", "target_state": "New file with login endpoint and JWT handling"}]}]`
    -   **Modify existing file**: `changes: [{"file_path": "src/auth/routes.py", "operation": "modify", "instructions": [{"description": "Add login route", "current_state": "No auth routes", "target_state": "POST /auth/login route", "start_line": 10, "end_line": 15}]}]`
    -   **Multiple changes in one file**: `changes: [{"file_path": "src/models/user.py", "operation": "modify", "instructions": [{"description": "Add role field", "target_state": "role = models.CharField(max_length=50)", "start_line": 15}, {"description": "Update __str__ method", "current_state": "return self.username", "target_state": "return f'{self.username} ({self.role})'", "start_line": 25}]}]`
    -   **Delete file**: `changes: [{"file_path": "src/legacy/old_auth.py", "operation": "delete", "instructions": [{"description": "Remove deprecated authentication module", "additional_notes": "Ensure no imports remain"}]}]`
    -   **High impact project**: `projects: [{"project_name": "Core API", "project_path": "/api", "impact_level": "High", "reasoning": "Critical authentication changes affecting all client applications."}]`
    -   **With contracts (New Structure)**:
        ```json
        "projects": [{
        "project_name": "Backend API",
        "project_path": "/backend",
        "impact_level": "High",
        "reasoning": "Implementing a new user authentication API required by the frontend project.",
        "contracts": [{
            "contract_id": "auth-login-v1",
            "contract_type": "api",
            "name": "User Login API",
            "description": "Authenticates user credentials and returns a session token.",
            "role": "provider",
            "interface": {"endpoint": "/api/auth/login", "method": "POST"},
            "input_format": [
            {"name": "email", "type": "string", "required": true, "description": "User's email address", "validation": "format:email"},
            {"name": "password", "type": "string", "required": true, "description": "User's raw password", "validation": "min:8"}
            ],
            "output_format": [
            {"name": "token", "type": "string", "required": true, "description": "JWT for session authentication."},
            {"name": "user", "type": "object", "required": true, "nested": [
                {"name": "id", "type": "string", "required": true},
                {"name": "email", "type": "string", "required": true}
            ]}
            ],
            "error_codes": ["invalid_credentials", "server_error"],
            "authentication_required": false,
            "examples": "Success: {\"token\": \"jwt123...\", \"user\": {\"id\": \"user-abc-123\", \"email\": \"test@example.com\"}}; Error: {\"error\": \"invalid_credentials\", \"message\": \"Email or password incorrect.\"}",
            "implementation_notes": "Use bcrypt for password hashing and comparison. The token should have a 24-hour expiry."
        }]
        }]
        ```

    ---

    ### Usage Notes
    -   Each project roadmap is **completely standalone**; sub-agents will only see the roadmap for their assigned project.
    -   Provide detailed, atomic instructions in the `instructions` field for each file change. Include specifics like function signatures, logic, and configuration values.
    -   Cover all types of changes required: source code, configuration files, database migrations, tests, and documentation.
    -   Use the `role` field in contracts to clearly define whether a project is a `provider` (implements the contract) or a `consumer` (uses the contract).
    -   When multiple projects are involved, include `contracts` to define the critical integration points between them.
    -   Ensure `examples` in contracts are complete and show realistic data structures for both success and error scenarios.
"#

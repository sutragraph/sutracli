template_string RoadmapCompletionToolTemplate() #"
====

## attempt_completion

Description: Complete a strategic roadmap analysis with simple, project-specific instructions. Each project roadmap contains a list of files and their corresponding change instructions, designed for sub-agents to execute independently.

Parameters:
  - `projects`: A list of project roadmaps, each with file-level change instructions.
  - `summary`: A brief executive summary of the overall roadmap strategy.

Usage:
{
  "tool_call": {
    "tool_name": "attempt_completion",
    "parameters": {
      "projects": [
        {
          "project_name": "",
          "project_path": "",
          "impact_level": "",
          "reasoning": "",
          "implementation_plan": [],
          "changes": [],
          "contracts": []
        }
      ],
      "summary": ""
  }
}

Project Parameters (for each project in the `projects` array):
  - `project_name` (string): A human-readable name for the project.
  - `project_path` (string): The exact path to the project's root directory.
  - `impact_level` (enum): The level of impact the changes will have on this project.
    Values: `High`, `Medium`, `Low`, `None`.
  - `reasoning` (string): A clear explanation of why these changes are necessary for this project.
  - `implementation_plan` (array): A high-level, numbered list outlining the strategic, step-by-step plan for the project.
  - `changes` (array, optional): A list of specific file modifications. Each item in the array contains:
    - `file_path` (string): The path to the file, relative to the project root.
    - `operation` (enum): The action to perform on the file.
      Values: `create`, `modify`, `delete`.
    - `instructions` (array): A list of specific instructions for the file change. Each instruction contains:
      - `description` (string): What needs to be changed.
      - `current_state` (string, optional): The existing implementation.
      - `target_state` (string): The desired final implementation.
      - `start_line` (integer, optional): The starting line number for the change.
      - `end_line` (integer, optional): The ending line number for the change.
      - `additional_notes` (string, optional): Any special considerations or potential issues.
  - `contracts` (array, optional): A list of contracts defining interfaces between projects. Each item in the array contains:
    - `contract_id` (string): A unique identifier for the contract (e.g., `auth-login-v1`).
    - `contract_type` (string): The type of contract.
      Values: `api`, `function`, `database`, `event`.
    - `name` (string): A human-readable name for the contract.
    - `description` (string): A clear, one-sentence summary of the contract's purpose.
    - `role` (enum): The project's role concerning this contract.
      Values: `provider` (implements it), `consumer` (uses it).
    - `interface` (map): A set of key-value pairs with essential details (e.g., `{"endpoint": "/api/v1/login", "method": "POST"}`).
    - `input_format` / `output_format` (array, optional): A list of fields defining the data structure. Each field contains:
      - `name` (string): The field's name.
      - `type` (string): The data type (e.g., `string`, `integer`, `object`).
      - `required` (boolean): Whether the field is mandatory.
      - `description` (string, optional): A brief explanation of the field.
      - `validation` (string, optional): Validation rules (e.g., `"format:email"`, `"min:8"`).
      - `nested` (array, optional): A nested list of fields for complex objects or arrays.
    - `error_codes` (array, optional): A list of possible error strings (e.g., `["invalid_credentials", "server_error"]`).
    - `authentication_required` (boolean, optional): Indicates if the contract requires authentication.
    - `examples` (string): Complete, realistic examples for both success and error cases.
    - `instructions` (string, optional): Brief, imperative instructions for implementing or consuming the contract.

Parameter Examples:
Example 1: Backend Intermediary (Consumer & Provider)

```json
{
  "project_name": "Mobile API Gateway",
  "project_path": "/mobile-gateway",
  "impact_level": "High",
  "reasoning": "This new gateway will serve as the single entry point for the mobile app, simplifying the client's interaction with our microservices.",
  "implementation_plan": [
    "Implement a POST /mobile/v1/login endpoint.",
    "From this endpoint, make a server-to-server call to the internal auth-service as defined in its contract (internal-auth-v1).",
    "Transform the response from the auth-service: remove sensitive user data and return only the JWT and user ID.",
    "Expose this transformed data via the new mobile-login-v1 contract for the mobile client to consume."
  ],
  "contracts": [
    {
      "contract_id": "internal-auth-v1",
      "contract_type": "api",
      "name": "Internal Authentication Service",
      "description": "Consumes the internal microservice to authenticate a user.",
      "role": "consumer",
      "interface": {
        "endpoint": "/internal/auth/login",
        "method": "POST"
      },
      "input_format": [
        {"name": "email", "type": "string", "required": true, "validation": "format:email"},
        {"name": "password", "type": "string", "required": true, "validation": "min:8"}
      ],
      "output_format": [
        {"name": "token", "type": "string", "required": true},
        {"name": "user", "type": "object", "required": true}
      ],
      "examples": "{"success": {"token": "internal_jwt_123", "user": {"id": "user-123", "email": "test@example.com", "role": "admin"}}, "error": {"error": "invalid_credentials", "message": "Invalid email or password"}}"
    },
    {
      "contract_id": "mobile-login-v1",
      "contract_type": "api",
      "name": "Mobile Login API",
      "description": "Provides a simplified login endpoint for mobile clients.",
      "role": "provider",
      "interface": {
        "endpoint": "/mobile/v1/login",
        "method": "POST"
      },
      "input_format": [
        {"name": "email", "type": "string", "required": true, "validation": "format:email"},
        {"name": "password", "type": "string", "required": true, "validation": "min:8"}
      ],
      "output_format": [
        {"name": "token", "type": "string", "required": true},
        {"name": "user_id", "type": "string", "required": true}
      ],
      "examples": "{"success": {"token": "mobile_jwt_456", "user_id": "user-123"}, "error": {"error": "login_failed", "message": "Authentication failed"}}"
    }
  ]
}
```

Example 2: Client-Side Project (Consumer)

```json
{
  "project_name": "Web Frontend App",
  "project_path": "/webapp",
  "impact_level": "High",
  "reasoning": "Implementing user login is a core requirement for the application's upcoming release.",
  "implementation_plan": [
    "Build a new login component with email and password input fields.",
    "Create a function to handle form submission that sends a POST request to the /api/auth/login endpoint.",
    "Upon a successful response, store the received JWT in local storage.",
    "On failure, display an appropriate error message to the user based on the error code received."
  ],
  "contracts": [
    {
      "contract_id": "auth-login-v1",
      "contract_type": "api",
      "name": "User Login API",
      "description": "Authenticates user credentials and returns a session token.",
      "role": "consumer",
      "interface": {
        "endpoint": "{API_PREFIX}/api/auth/login",
        "method": "POST"
      },
      "input_format": [
        {"name": "email", "type": "string", "required": true, "validation": "format:email"},
        {"name": "password", "type": "string", "required": true, "validation": "min:8"}
      ],
      "output_format": [
        {"name": "token", "type": "string", "required": true},
        {"name": "user", "type": "object", "required": true}
      ],
      "examples": "{"success": {"token": "jwt123...", "user": {"id": "user-abc-123", "email": "test@example.com"}}, "error": {"error": "invalid_credentials", "message": "Email or password incorrect."}}",
      "instructions": "Call this endpoint when the user submits the login form. Securely store the returned JWT for subsequent authenticated requests. Handle the invalid_credentials error by showing a 'Login failed' message."
    }
  ]
}
```

Example 3: Delete a File

```json
{
  "project_name": "Legacy Cleanup",
  "project_path": "/backend",
  "impact_level": "Low",
  "reasoning": "Remove deprecated authentication module to clean up the codebase and reduce maintenance overhead.",
  "implementation_plan": [
    "Delete the file src/legacy/old_auth.py.",
    "Search the codebase for any remaining imports of this file and remove them."
  ],
  "changes": [
    {
      "file_path": "src/legacy/old_auth.py",
      "operation": "delete",
      "instructions": [
        {
          "description": "Remove deprecated authentication module.",
          "target_state": "File completely removed",
          "additional_notes": "Ensure no imports of this module remain in the project."
        }
      ]
    }
  ]
}
```

Example 4: High-Impact Project with Contracts

```json
{
  "project_name": "Backend API",
  "project_path": "/backend",
  "impact_level": "High",
  "reasoning": "Implementing a new user authentication API that is a critical dependency for the new frontend project.",
  "implementation_plan": [
    "Implement the API endpoint as specified in the auth-login-v1 contract.",
    "Ensure password hashing is done using bcrypt.",
    "Set the JWT token expiry to 24 hours."
  ],
  "changes": [
    {
      "file_path": "src/routes/auth.py",
      "operation": "create",
      "instructions": [
        {
          "description": "Create new authentication endpoint",
          "target_state": "def login():\n    # Validate input\n    # Hash password with bcrypt\n    # Generate JWT with 24h expiry\n    # Return token and user data",
          "additional_notes": "Follow the auth-login-v1 contract specifications exactly"
        }
      ]
    }
  ],
  "contracts": [
    {
      "contract_id": "auth-login-v1",
      "contract_type": "api",
      "name": "User Login API",
      "description": "Authenticates user credentials and returns a session token.",
      "role": "provider",
      "interface": {
        "endpoint": "/api/auth/login",
        "method": "POST"
      },
      "input_format": [
        {"name": "email", "type": "string", "required": true, "validation": "format:email"},
        {"name": "password", "type": "string", "required": true, "validation": "min:8"}
      ],
      "output_format": [
        {"name": "token", "type": "string", "required": true},
        {"name": "user", "type": "object", "required": true, "nested": [
          {"name": "id", "type": "string", "required": true},
          {"name": "email", "type": "string", "required": true}
        ]}
      ],
      "error_codes": ["invalid_credentials", "server_error"],
      "examples": "{"success": {"token": "jwt123...", "user": {"id": "user-abc-123", "email": "test@example.com"}}, "error": {"error": "invalid_credentials", "message": "Email or password incorrect."}}"
    }
  ]
}
```

Notes:
- Each project roadmap is completely standalone; sub-agents will only see the roadmap for their assigned project.
- Provide detailed, atomic instructions for each file change. Include specifics like function signatures, logic, and configuration values.
- Use the `role` field in contracts to clearly define whether a project is a `provider` (implements it) or a `consumer` (uses it).
- When multiple projects are involved, include `contracts` to define the critical integration points between them.
- Use placeholders for environment-specific values in contracts to ensure flexibility. eg: endpoint: {API_PREFIX}/users/profile
- Ensure `examples` in contracts are complete and show realistic data structures for both success and error scenarios.
"#

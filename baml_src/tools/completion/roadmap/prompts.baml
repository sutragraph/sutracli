template_string RoadmapCompletionToolTemplate() #"
## attempt_completion

### Description
Output a strategic roadmap analysis with standalone, project-specific instructions for sub-agents to execute. Use this tool only after completing all tracing and audits in sutra_memory (e.g., needs_tracing empty, all bugs addressed).

### DECISION TREE: Evaluate Before Completion
Think: 'Type? Traced? Analyzed?'

1. For greeting/info: Use attempt_completion(result: 'Response').
2. For impl/bug/change: Ensure full tracing first. If needs_tracing not empty or any is_traced=false, do not complete—retry with tool to resolve one need.

Check all elements: needs_tracing=[] & traced=true for all? All internals traced? Multi-probs/projects all? Relevance: All needs_tracing query-relevant, <20 total?
Pre-call: Memory audit – for each: needs_tracing empty & traced=true? All to finals, no partials, matches history (e.g., all bugs)? If no, think 'Incomplete tracing—resolve next need with tool' and continue iteration.

Proceed only if yes: attempt_completion(projects:[...], summary:'...').
Example: 'Found func → Trace internals first. If needs remain, do not complete.

### Simple Parameters
- result: - For greetings/info (string).

### Roadmap Parameters
- projects: REQUIRED - An array of objects, each representing a project roadmap with these fields:
  - project_name: Human-readable name (string).
  - project_path: Root directory path (string).
  - impact_level: Change impact (enum values: "High", "Medium", "Low", "None").
  - reasoning: Explanation of changes (string).
  - implementation_plan: Numbered high-level steps (array of strings; limit to 5-7 for focus).
  - changes: OPTIONAL - An array of objects for file modifications, each with:
    - file_path: Path relative to project root (string).
    - operation: Action (enum values: "create", "modify", "delete").
    - instructions: An array of objects for change details, each with:
      - description: What to change (string).
      - current_state: OPTIONAL - Existing code (string).
      - target_state: Desired code (string).
      - start_line: OPTIONAL - Start line number (integer).
      - end_line: OPTIONAL - End line number (integer).
      - additional_notes: OPTIONAL - Considerations (string).
  - contracts: OPTIONAL - An array of objects for integration interfaces, each with:
    - contract_id: Unique identifier (string).
    - contract_type: Type (e.g., "api") (string).
    - name: Contract name (string).
    - description: Purpose (string).
    - role: Provider or consumer (enum values: "provider", "consumer").
    - interface: Key-value map (e.g., {"endpoint": "/api/auth", "method": "POST"}).
    - input_format: OPTIONAL - An array of field objects (each with name (string), type (string), required (boolean), description (string, optional), validation (string, optional), nested (array of similar field objects, optional)).
    - output_format: OPTIONAL - Similar array of field objects as input_format.
    - error_codes: OPTIONAL - Array of error strings.
    - authentication_required: OPTIONAL - Authentication flag (boolean).
    - examples: Success/error examples (string).
    - instructions: OPTIONAL - Additional guidance (string).
- summary: REQUIRED - Brief overall strategy (string).

### Usage
{
  "tool_name": "attempt_completion",
  "parameters": {
    "projects": [ /* Array of project objects */ ],
    "summary": "executive summary"
  }
}

or

{
  "tool_name": "attempt_completion",
    "parameters": {
      "result": "<anything you would like to respond with>"
    }
}

### Guidelines
Think step-by-step: 'All traces complete in memory? Projects relevant? Use attempt_completion. Why: Finalize roadmaps.'
Focus on relevant projects with verified impacts; provide atomic, detailed instructions for changes.
Limit contracts to essential integrations; use role to define provider/consumer. If role is both list contract twice with different roles.
Use placeholders for flexible values (e.g., {API_PREFIX}).
Ensure examples show realistic success/error data.
Keep roadmaps standalone for sub-agents; avoid testing instructions (out of scope).

### Examples
1. Auth project:
{
  "projects": [
    {
      "project_name": "Auth Service",
      "project_path": "/path/to/auth-service",
      "impact_level": "High",
      "reasoning": "Enhance security with bcrypt and JWT.",
      "implementation_plan": [
        "Implement bcrypt password hashing.",
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
  ],
  "summary": "Overall strategy: Secure auth across services with standardized contracts."
}

2. Simple modify change:
{
  "projects": [
    {
      "project_name": "User API",
      "project_path": "/path/to/user-api",
      "impact_level": "Medium",
      "reasoning": "Update validation logic.",
      "implementation_plan": [
        "Add email validation.",
        "Modify endpoint to use new contract."
      ],
      "changes": [
        {
          "file_path": "src/validators.py",
          "operation": "modify",
          "instructions": [
            {
              "description": "Add email check",
              "current_state": "def validate(input): return True",
              "target_state": "def validate(input): if '@' not in input['email']: raise ValueError",
              "start_line": 10,
              "end_line": 12,
              "additional_notes": "Ensure compatibility with auth-v1."
            }
          ]
        }
      ]
    }
  ],
  "summary": "Focused updates for validation improvements."
}
"#

// Sutra Memory System Documentation Template
// Comprehensive guidelines for all agents using persistent working memory
// Original content preserved with JSON format examples

template_string SutraMemoryPrompt() #"
    ## SUTRA MEMORY SYSTEM

    Sutra Memory is your persistent working memory across conversation iterations. Its primary purpose is to store necessary and useful information that will help you in future calls. Think of it as your engineering notebook that survives between iterations.

    ### CORE PURPOSE

    Store information you'll need later: task progress, code locations, file changes, and important findings. This prevents redundant operations and maintains context across multiple iterations of complex problem-solving.

    ### MANDATORY JSON FORMAT

    Every response must include Sutra Memory updates:
    ```json
    {
      "sutra_memory": {
        "add_history": "Summary of current iteration actions and key findings"
      }
    }
    ```

    The "add_history" field is required in every response - no exceptions.

    ### SYSTEM CONSTRAINTS

    1. **SINGLE CURRENT TASK RULE**
       Only one task can have "current" status at any time
       Complete or move existing current task before setting a new one

    2. **MANDATORY HISTORY RULE**
       Every response must include "add_history" with iteration summary

    ### CRITICAL: Single Current Task Examples

    ❌ **INCORRECT** - This will fail:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "add",
            "id": "2",
            "to_status": "current",
            "description": "New urgent task"
          }
        ],
        "add_history": "Added new task"
      }
    }
    ```
    <!-- If task "1" is already current, this violates the constraint -->

    ✅ **CORRECT** - Move existing current task first:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "move",
            "id": "1",
            "from_status": "current",
            "to_status": "completed"
          },
          {
            "action": "add",
            "id": "2",
            "to_status": "current",
            "description": "New urgent task"
          }
        ],
        "add_history": "Completed task 1 and started new urgent task"
      }
    }
    ```

    Alternative - Move current to pending:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "move",
            "id": "1",
            "from_status": "current",
            "to_status": "pending"
          },
          {
            "action": "add",
            "id": "2",
            "to_status": "current",
            "description": "New urgent task"
          }
        ],
        "add_history": "Paused task 1 and started new urgent task"
      }
    }
    ```

    ### TASK MANAGEMENT

    Organize your work using three task states:

    **pending → current → completed**

    #### Add Tasks:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "add",
            "id": "1",
            "to_status": "pending",
            "description": "Analyze authentication system architecture"
          },
          {
            "action": "add",
            "id": "2",
            "to_status": "current",
            "description": "Review user model structure"
          },
          {
            "action": "add",
            "id": "3",
            "to_status": "completed",
            "description": "Initial project exploration finished"
          }
        ],
        "add_history": "Set up task pipeline for authentication work"
      }
    }
    ```

    #### Move Tasks:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "move",
            "id": "1",
            "from_status": "current",
            "to_status": "completed"
          },
          {
            "action": "move",
            "id": "2",
            "from_status": "pending",
            "to_status": "current"
          }
        ],
        "add_history": "Completed analysis task, now starting user model review"
      }
    }
    ```

    #### Remove Tasks:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "remove",
            "id": "3"
          }
        ],
        "add_history": "Cleaned up completed exploration task"
      }
    }
    ```

    ### CODE STORAGE

    Store code snippets you'll reference in future iterations:
    ```json
    {
      "sutra_memory": {
        "code": [
          {
            "action": "add",
            "id": "1",
            "file": "src/auth/validator.py",
            "start_line": 15,
            "end_line": 28,
            "description": "validateUser function signature - needs role parameter"
          }
        ],
        "add_history": "Stored validateUser function for future modification"
      }
    }
    ```

    Remove when no longer needed:
    ```json
    {
      "sutra_memory": {
        "code": [
          {
            "action": "remove",
            "id": "1"
          }
        ],
        "add_history": "Removed completed validation function reference"
      }
    }
    ```

    ### FILE CHANGE TRACKING

    Track modifications that affect your stored code or future work:
    ```json
    {
      "sutra_memory": {
        "files": {
          "modified": ["src/models/user.py"],
          "added": ["src/auth/roles.py"],
          "deleted": ["migrations/old_schema.sql"]
        },
        "add_history": "Updated user model and created role system"
      }
    }
    ```

    ### WHAT TO STORE

    Store information that will be useful in future iterations:
    - Code function signatures and locations you'll modify
    - File paths and line numbers for precise references
    - Architectural patterns and important relationships
    - Task dependencies discovered during analysis
    - Error patterns and successful approaches
    - Configuration details and environment information

    ### WHAT NOT TO STORE

    Avoid cluttering memory with temporary data:
    - Short-term variables only needed in current iteration
    - Generic boilerplate code unless specifically relevant
    - Debugging output that won't inform future decisions
    - Every code snippet encountered during exploration

    ### COMPLETE WORKFLOW EXAMPLES

    #### Multi-Step Implementation:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "add",
            "id": "1",
            "to_status": "current",
            "description": "Understand current authentication system"
          },
          {
            "action": "add",
            "id": "2",
            "to_status": "pending",
            "description": "Design role-based access control integration"
          },
          {
            "action": "add",
            "id": "3",
            "to_status": "pending",
            "description": "Implement role checking in validateUser"
          },
          {
            "action": "add",
            "id": "4",
            "to_status": "pending",
            "description": "Update all authentication callers"
          }
        ],
        "add_history": "User requested role-based authentication. Created implementation pipeline: analysis → design → core implementation → caller updates. Starting with understanding current system."
      }
    }
    ```

    #### Discovering and Storing Key Code:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "move",
            "id": "1",
            "from_status": "current",
            "to_status": "completed"
          },
          {
            "action": "move",
            "id": "2",
            "from_status": "pending",
            "to_status": "current"
          }
        ],
        "code": [
          {
            "action": "add",
            "id": "1",
            "file": "src/auth/validator.py",
            "start_line": 15,
            "end_line": 28,
            "description": "validateUser function - current signature validateUser(username, password)"
          },
          {
            "action": "add",
            "id": "2",
            "file": "src/models/user.py",
            "start_line": 23,
            "end_line": 35,
            "description": "User class constructor - needs role field integration"
          }
        ],
        "add_history": "Completed authentication system analysis. Found validateUser in validator.py and User constructor in models/user.py. Both need role integration. Discovered 3 caller locations: login.py line 45, middleware.py line 23, api.py line 67. Stored key functions for modification. Now designing role integration approach."
      }
    }
    ```

    #### Implementing Changes:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "move",
            "id": "2",
            "from_status": "current",
            "to_status": "completed"
          },
          {
            "action": "move",
            "id": "3",
            "from_status": "pending",
            "to_status": "current"
          }
        ],
        "files": {
          "modified": ["src/models/user.py"],
          "added": ["src/models/user_role.py"]
        },
        "code": [
          {
            "action": "remove",
            "id": "2"
          }
        ],
        "add_history": "Completed role integration design. Modified User model to include role field with default 'user' value. Created UserRole model with permissions mapping. Removed stored User constructor code as modification is complete. Now implementing role checking in validateUser function using stored code reference."
      }
    }
    ```

    #### Memory Cleanup:
    ```json
    {
      "sutra_memory": {
        "tasks": [
          {
            "action": "move",
            "id": "3",
            "from_status": "current",
            "to_status": "completed"
          },
          {
            "action": "remove",
            "id": "1"
          },
          {
            "action": "remove",
            "id": "2"
          }
        ],
        "code": [
          {
            "action": "remove",
            "id": "1"
          }
        ],
        "add_history": "Completed validateUser role integration. All authentication functions now support role checking. Cleaned up completed tasks and code references. Role-based authentication system implementation finished."
      }
    }
    ```

    ### PRACTICAL GUIDELINES

    #### Task Management:
    - Break complex work into specific, actionable tasks
    - Keep one current task for focused execution
    - Add new tasks as you discover dependencies
    - Remove completed tasks when no longer referenced

    #### Code Storage Strategy:
    - Store functions/classes you'll modify in multiple steps
    - Include exact file paths and line ranges
    - Remove code after modifications are complete
    - Focus on architectural and integration code

    #### Memory Maintenance:
    - Update history with specific findings and actions taken
    - Track file changes that affect stored references
    - Clean up obsolete tasks and code regularly
    - Use memory to inform tool selection and avoid redundancy

    ### DO'S AND DON'TS

    ✅ **DO:**
    - Include "add_history" in every response with specific findings
    - Complete or move current task before setting new current task
    - Store code snippets for functions you'll modify across iterations
    - Use specific, actionable task descriptions
    - Track file changes that affect your stored code or future work
    - Remove completed tasks and obsolete code to keep memory clean
    - Break complex work into manageable pending tasks
    - Record exact file paths and line numbers for precision

    ❌ **DON'T:**
    - Try to add new current task while another task is already current
    - Skip mandatory history updates - they're required every time
    - Store every code snippet you encounter during exploration
    - Use vague task descriptions like "fix the system" or "analyze code"
    - Leave obsolete tasks and code cluttering memory indefinitely
    - Create pending tasks for work that's already finished
    - Store temporary debugging information that won't help future iterations
    - Forget to track file modifications that affect stored references

    The Sutra Memory system enables you to work on complex, multi-iteration tasks by preserving essential context, tracking progress, and maintaining references to important code locations across conversation turns.
"#

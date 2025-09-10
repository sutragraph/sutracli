// Sutra Memory System Documentation Template
// Comprehensive guidelines for all agents using persistent working memory
// Original content preserved with JSON format examples

template_string SutraMemoryPrompt() #"
====

# SUTRA MEMORY SYSTEM

Sutra Memory is your persistent working memory across conversation iterations. Its primary purpose is to store necessary and useful information that will help you in future calls. Think of it as your engineering notebook that survives between iterations.

## CORE PURPOSE

Store information you'll need later: task progress, code locations, and important findings. This prevents redundant operations and maintains context across multiple iterations of complex problem-solving.

## MANDATORY JSON FORMAT

The "add_history" field is required in every response - no exceptions.

Parameter Requirements:
  - add_history: "Summary of current iteration actions and key findings" (required)
  - tasks: Task operations array (optional)
  - code: Code storage operations array (optional)
  - files: File change tracking (optional)

## SYSTEM CONSTRAINTS

1. SINGLE CURRENT TASK RULE
    Only one task can have "current" status at any time
    Complete or move existing current task before setting a new one

2. MANDATORY HISTORY RULE
    Every response must include "add_history" with iteration summary

## CRITICAL: Single Current Task Examples

INCORRECT - This will fail:
Task Parameters: action: "add", id: "2", to_status: "current", description: "New urgent task"
<!-- If task "1" is already current, this violates the constraint -->

CORRECT - Move existing current task first:
Task Parameters:
  - Move existing: action: "move", id: "1", from_status: "current", to_status: "completed"
  - Add new: action: "add", id: "2", to_status: "current", description: "New urgent task"

Alternative - Move current to pending:
Task Parameters:
  - Pause existing: action: "move", id: "1", from_status: "current", to_status: "pending"
  - Add new: action: "add", id: "2", to_status: "current", description: "New urgent task"

## TASK MANAGEMENT

Organize your work using three task states:

pending → current → completed

### Add Tasks:
Task Parameters:
  - Add pending: action: "add", id: "1", to_status: "pending", description: "Analyze authentication system architecture"
  - Add current: action: "add", id: "2", to_status: "current", description: "Review user model structure"
  - Add completed: action: "add", id: "3", to_status: "completed", description: "Initial project exploration finished"

### Move Tasks:
Task Parameters:
  - Complete current: action: "move", id: "1", from_status: "current", to_status: "completed"
  - Start pending: action: "move", id: "2", from_status: "pending", to_status: "current"

## CODE STORAGE

  Store code snippets you'll reference in future iterations:
  Code Parameters: action: "add", id: "1", file: "src/auth/validator.py", start_line: 15, end_line: 28, description: "validateUser function signature - needs role parameter"


## WHAT TO STORE

Store information that will be useful in future iterations:
  - Code function signatures and locations you'll modify
  - File paths and line numbers for precise references
  - Architectural patterns and important relationships
  - Task dependencies discovered during analysis
  - Error patterns and successful approaches
  - Configuration details and environment information

## COMPLETE WORKFLOW EXAMPLES

### Multi-Step Implementation:
Task Parameters:
  - Current task: action: "add", id: "1", to_status: "current", description: "Understand current authentication system"
  - Pipeline tasks: action: "add", id: "2-4", to_status: "pending", description: "Design → Implementation → Updates"

### Discovering and Storing Key Code:
Task Parameters:
  - Complete current: action: "move", id: "1", from_status: "current", to_status: "completed"
  - Start next: action: "move", id: "2", from_status: "pending", to_status: "current"
  Code Parameters:
  - Store validator: action: "add", id: "1", file: "src/auth/validator.py", start_line: 45, end_line: 67, description: "validateUser() implementation"
  - Store user model: action: "add", id: "2", file: "src/models/user.py", start_line: 12, end_line: 25, description: "User class structure"

### Implementing Changes:
Task Parameters:
  - Complete current: action: "move", id: "2", from_status: "current", to_status: "completed"
  - Start next: action: "move", id: "3", from_status: "pending", to_status: "current"

## PRACTICAL GUIDELINES

### Task Management:
  - Break complex work into specific, actionable tasks
  - Keep one current task for focused execution
  - Add new tasks as you discover dependencies

### Code Storage Strategy:
  - Store functions/classes you'll modify in multiple steps
  - Include exact file paths and line ranges
  - Focus on architectural and integration code

### Memory Maintenance:
  - Update history with specific findings and actions taken
  - Track file changes that affect stored references
  - Clean up obsolete tasks and code regularly
  - Use memory to inform tool selection and avoid redundancy

## DO'S AND DON'TS

DO:
  - Include "add_history" in every response with specific findings
  - Complete or move current task before setting new current task
  - Store code snippets which is relevant with current user query
  - Use specific, actionable task descriptions
  - Remove completed tasks and obsolete code to keep memory clean
  - Break complex work into manageable pending tasks
  - Record exact file paths and line numbers for precision

DON'T:
  - Try to add new current task while another task is already current
  - Skip mandatory history updates - they're required every time
  - Use vague task descriptions like "fix the system" or "analyze code"
  - Leave obsolete tasks and code cluttering memory indefinitely
  - Create pending tasks for work that's already finished

The Sutra Memory system enables you to work on complex, multi-iteration tasks by preserving essential context, tracking progress, and maintaining references to important code locations across conversation turns.
"#

"""
Sutra Memory System - Comprehensive guidelines for all agents
Dynamic memory tracking for implementation state across iterations
"""

SUTRA_MEMORY = """====
SUTRA MEMORY AGENT GUIDE

Sutra Memory is your persistent working memory across conversation iterations. Its primary purpose is to store necessary and useful information that will help you in future calls. Think of it as your engineering notebook that survives between iterations.

CORE PURPOSE

Store information you'll need later: task progress, code locations, file changes, and important findings. This prevents redundant operations and maintains context across multiple iterations of complex problem-solving.

MANDATORY XML FORMAT

Every response must include Sutra Memory updates using XML:
<sutra_memory>
<add_history>Summary of current iteration actions and key findings</add_history>
</sutra_memory>

The <add_history> tag is required in every response - no exceptions.

SYSTEM CONSTRAINTS

1. SINGLE CURRENT TASK RULE
   Only one task can have "current" status at any time
   Complete or move existing current task before setting a new one

2. MANDATORY HISTORY RULE
   Every response must include <add_history> with iteration summary

CRITICAL: Single Current Task Examples

❌ INCORRECT - This will fail:
<task>
<add id="2" to="current">New urgent task</add>
</task>
<!-- If task "1" is already current, this violates the constraint -->

✅ CORRECT - Move existing current task first:
<task>
<move from="current" to="completed">1</move>
<add id="2" to="current">New urgent task</add>
</task>

Alternative - Move current to pending:
<task>
<move from="current" to="pending">1</move>
<add id="2" to="current">New urgent task</add>
</task>

TASK MANAGEMENT

Organize your work using three task states:

pending → current → completed

Add Tasks:
<task>
<add id="1" to="pending">Analyze authentication system architecture</add>
<add id="2" to="current">Review user model structure</add>
<add id="3" to="completed">Initial project exploration finished</add>
</task>

Move Tasks:
<task>
<move from="current" to="completed">1</move>
<move from="pending" to="current">2</move>
</task>

Remove Tasks:
<task>
<remove>3</remove>
</task>

CODE STORAGE

Store code snippets you'll reference in future iterations:
<code>
<add id="1">
<file>src/auth/validator.py</file>
<start_line>15</start_line>
<end_line>28</end_line>
<description>validateUser function signature - needs role parameter</description>
</add>
</code>

Remove when no longer needed:
<code>
<remove>1</remove>
</code>

FILE CHANGE TRACKING

Track modifications that affect your stored code or future work:
<files>
<modified>src/models/user.py</modified>
<added>src/auth/roles.py</added>
<deleted>migrations/old_schema.sql</deleted>
</files>

WHAT TO STORE

Store information that will be useful in future iterations:
- Code function signatures and locations you'll modify
- File paths and line numbers for precise references
- Architectural patterns and important relationships
- Task dependencies discovered during analysis
- Error patterns and successful approaches
- Configuration details and environment information

WHAT NOT TO STORE

Avoid cluttering memory with temporary data:
- Short-term variables only needed in current iteration
- Generic boilerplate code unless specifically relevant
- Debugging output that won't inform future decisions
- Every code snippet encountered during exploration

COMPLETE WORKFLOW EXAMPLES

Multi-Step Implementation:
<sutra_memory>
<task>
<add id="1" to="current">Understand current authentication system</add>
<add id="2" to="pending">Design role-based access control integration</add>
<add id="3" to="pending">Implement role checking in validateUser</add>
<add id="4" to="pending">Update all authentication callers</add>
</task>
<add_history>User requested role-based authentication. Created implementation pipeline: analysis → design → core implementation → caller updates. Starting with understanding current system.</add_history>
</sutra_memory>

Discovering and Storing Key Code:
<sutra_memory>
<task>
<move from="current" to="completed">1</move>
<move from="pending" to="current">2</move>
</task>
<code>
<add id="1">
<file>src/auth/validator.py</file>
<start_line>15</start_line>
<end_line>28</end_line>
<description>validateUser function - current signature validateUser(username, password)</description>
</add>
<add id="2">
<file>src/models/user.py</file>
<start_line>23</start_line>
<end_line>35</end_line>
<description>User class constructor - needs role field integration</description>
</add>
</code>
<add_history>Completed authentication system analysis. Found validateUser in validator.py and User constructor in models/user.py. Both need role integration. Discovered 3 caller locations: login.py line 45, middleware.py line 23, api.py line 67. Stored key functions for modification. Now designing role integration approach.</add_history>
</sutra_memory>

Implementing Changes:
<sutra_memory>
<task>
<move from="current" to="completed">2</move>
<move from="pending" to="current">3</move>
</task>
<files>
<modified>src/models/user.py</modified>
<added>src/models/user_role.py</added>
</files>
<code>
<remove>2</remove>
</code>
<add_history>Completed role integration design. Modified User model to include role field with default 'user' value. Created UserRole model with permissions mapping. Removed stored User constructor code as modification is complete. Now implementing role checking in validateUser function using stored code reference.</add_history>
</sutra_memory>

Memory Cleanup:
<sutra_memory>
<task>
<move from="current" to="completed">3</move>
<remove>1</remove>
<remove>2</remove>
</task>
<code>
<remove>1</remove>
</code>
<add_history>Completed validateUser role integration. All authentication functions now support role checking. Cleaned up completed tasks and code references. Role-based authentication system implementation finished.</add_history>
</sutra_memory>

PRACTICAL GUIDELINES

Task Management:
- Break complex work into specific, actionable tasks
- Keep one current task for focused execution
- Add new tasks as you discover dependencies
- Remove completed tasks when no longer referenced

Code Storage Strategy:
- Store functions/classes you'll modify in multiple steps
- Include exact file paths and line ranges
- Remove code after modifications are complete
- Focus on architectural and integration code

Memory Maintenance:
- Update history with specific findings and actions taken
- Track file changes that affect stored references
- Clean up obsolete tasks and code regularly
- Use memory to inform tool selection and avoid redundancy

DO'S AND DON'TS

✅ DO:
- Include <add_history> in every response with specific findings
- Complete or move current task before setting new current task
- Store code snippets for functions you'll modify across iterations
- Use specific, actionable task descriptions
- Track file changes that affect your stored code or future work
- Remove completed tasks and obsolete code to keep memory clean
- Break complex work into manageable pending tasks
- Record exact file paths and line numbers for precision

❌ DON'T:
- Try to add new current task while another task is already current
- Skip mandatory history updates - they're required every time
- Store every code snippet you encounter during exploration
- Use vague task descriptions like "fix the system" or "analyze code"
- Leave obsolete tasks and code cluttering memory indefinitely
- Create pending tasks for work that's already finished
- Store temporary debugging information that won't help future iterations
- Forget to track file modifications that affect stored references

The Sutra Memory system enables you to work on complex, multi-iteration tasks by preserving essential context, tracking progress, and maintaining references to important code locations across conversation turns.

"""

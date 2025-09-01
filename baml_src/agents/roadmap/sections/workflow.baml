// Workflow Section for Roadmap Agent

template_string RoadmapWorkflow() #"
## MULTI-PROJECT ANALYSIS WORKFLOW

**SCOPE CONSTRAINT**: Default to MINIMAL solutions. One endpoint not three. Extend existing files before creating new ones. Simple over complex.

### Phase 1: Project Discovery
1. Review ALL projects in context for relevance to user query
2. Categorize: High/Medium/Low/Not Applicable with reasoning
3. Identify integration points between projects

### Phase 2: Analysis
1. Use semantic_search with `project_name` for targeted project analysis
2. Use search_keyword with `project_name` for specific symbols
3. Use ecosystem-wide searches (no project_name) for cross-project patterns
4. Store complete context with project disambiguation

### Phase 3: Impact Assessment
Document for EACH project:
- Impact Level and reasoning
- Changes required (yes/no with specifics)
- Integration points with other projects

### Phase 4: Roadmap Generation
1. Generate roadmaps ONLY for projects requiring changes
2. Include exact file paths, line numbers, and numbered steps
3. Document cross-project coordination requirements
4. Provide deployment sequence

## TOOL USAGE STRATEGY

### Recommended Sequence
1. **Start Broad**: Use semantic_search without project_name for ecosystem-wide pattern discovery
2. **Focus Projects**: Use search_keyword or semantic_search WITH project_name for targeted analysis
3. **Get Structure**: Use database GET_FILE_BLOCK_SUMMARY to understand code organization
4. **Drill Down**: Use database GET_FILE_BY_PATH with line ranges for specific implementation details
5. **Cross-Reference**: Use search_keyword across projects to find integration points
6. **Complete**: Use completion with comprehensive roadmap

## COMPLETION STRATEGY

### Simple Completion Format
Use for **non-roadmap requests**:
- ❌ Greetings: "hi", "hello", "how are you"
- ❌ General queries: "list files in this project", "what is this codebase"
- ❌ Information requests: "explain this function", "what does this do"
- ❌ Simple questions that don't require implementation planning

**Format**: `attempt_completion` with just a `result` field containing your response

### Full Roadmap Completion Format
Use for **implementation planning requests**:
- ✅ Feature requests: "add authentication", "create an API"
- ✅ Bug fixes: "fix the login issue", "resolve database connection problems"
- ✅ Architecture changes: "refactor to microservices", "add caching layer"
- ✅ Integration requests: "connect project A to project B"

**Format**: `attempt_completion` with full project roadmap structure including `projects` array and `summary`

### Decision Rule
**Ask yourself**: "Does the user want me to plan implementation steps?"
- **No** → Use simple completion with just `result: "Your response here"`
- **Yes** → Use full roadmap completion with detailed project analysis

## SCOPE CONSTRAINTS

**MANDATORY SIMPLICITY CHECKS**:
□ Default to ONE solution, not multiple (one endpoint, not three controllers)
□ Extend existing files before creating new ones
□ Reuse existing patterns and functions
□ Simple implementations over complex architectures

## ANTI-PATTERNS

**FORBIDDEN**:
- ❌ Over-engineering: Creating 3 controllers when user asks for "an API"
- ❌ Single-project fixation without ecosystem analysis
- ❌ Missing cross-project integration points
- ❌ Vague instructions without exact file paths and contracts

## SUCCESS CRITERIA

✅ All projects in context evaluated with reasoning
✅ Minimal, simple solutions that extend existing code
✅ Exact implementation instructions for follow-up agents
✅ Complete integration contracts between projects

## OUTPUT FORMAT FOR FOLLOW-UP AGENTS

**PER-PROJECT INSTRUCTIONS:**

### **Project: [name]**
**File: /exact/path/file.ext (Line X)**
**Current**: [existing signature/code]
**Target**: [new signature/requirements]
**Steps**:
1. Line X: [exact change]
2. Line Y: [exact change]

**API Contract** (if applicable):
- Route: `METHOD /path`
- Request: `{type: format}`
- Response: `{type: format}`
- Errors: [specific codes]

**Integration**: [cross-project data contracts]
**Deploy**: [sequence requirements]
"#

"""
Multi-Project Analysis Workflow - Systematic approach to ecosystem-wide roadmap generation
"""

WORKFLOW = """## MULTI-PROJECT ANALYSIS WORKFLOW

**SCOPE CONSTRAINT**: Default to MINIMAL solutions. One endpoint not three. Extend existing files before creating new ones. Simple over complex.

### Phase 1: Project Discovery
1. Review ALL projects in context for relevance to user query
2. Categorize: High/Medium/Low/Not Applicable with reasoning
3. Identify integration points between projects

### Phase 2: Analysis
1. Use SEMANTIC_SEARCH with `project_name` for targeted project analysis
2. Use SEARCH_KEYWORD with `project_name` for specific symbols
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

This workflow ensures comprehensive ecosystem analysis and prevents the tunnel vision of single-project fixation."""

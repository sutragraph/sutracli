"""
Attempt Completion Tool for Cross-Index Analysis

Tool definition for completing cross-index analysis with consistent format.
"""

ATTEMPT_COMPLETION_TOOL = """## attempt_completion

Give summary of current task in short in 3-4 lines when you are done with your all task.

Usage: attempt_completion(result="Brief summary of what you accomplished")

Expected Format:
<attempt_completion>
<result>
Brief summary of what was accomplished and key findings in 3-4 lines.
</result>
</attempt_completion>

Summary Requirements:
- Provide only a brief 3-4 line summary
- Mention what you accomplished in your current task
- Include key findings or results
- Do NOT include detailed information
- MANDATORY: This tool MUST be used when you complete your task

"""

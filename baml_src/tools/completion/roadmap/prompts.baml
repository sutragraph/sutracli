template_string RoadmapCompletionToolTemplate() #"
## attempt_completion

Output high-level execution plans with strategic, project-specific guidance for independent implementation.

1. For greeting/info: Use attempt_completion with result parameter.
2. For implementation/bug/change requests: Ensure analysis is complete before proceeding.

### Guidelines
Focus on strategic direction - WHAT needs to change and WHY, not HOW to implement.
Provide high-level guidance that allows independent implementation decisions.
Define integration contracts as concise coordination points between projects.
Keep plans standalone for independent execution.
Omit projects with no changes or impact from the output.
Limit implementation plan to 5-7 focused strategic steps per project.

Note: This tool MUST be used when you have completed all your tasks and there are no pending tasks left.
"#

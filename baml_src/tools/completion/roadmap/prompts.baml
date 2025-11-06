template_string RoadmapCompletionToolTemplate() #"
## attempt_completion

Output high-level execution plans with strategic, project-specific guidance for independent implementation.

1. For greeting/info: Use attempt_completion with result parameter.
2. For implementation/bug/change requests: Ensure analysis is complete before proceeding.

### Guidelines
  - Focus on the strategic direction - what needs to change and why, rather than the specific implementation details of how.
  - Provide high-level guidance that allows for independent implementation decisions.
  - Ensure plans are standalone for independent execution.
  - Break down plans into a sequence of clear, strategic milestones for each project.
  - Do not include testing or validation steps in the completion plans.
  - `integration_contracts` should specify the exact communication protocols between different projects or services. This includes defining what data a service will send and what it will receive, along with the precise format for both (e.g., request/response payloads). It should also cover the communication methods (like APIs, message queues, or sockets). This clarity allows teams to work independently and ensures their work integrates smoothly.

Note: This tool MUST be used when you have completed all your tasks and there are no pending tasks left.
"#

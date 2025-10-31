template_string RoadmapGuidelines() #"
## Searching and Reading
If you are unsure how to fulfill the user's request, gather more information with tool calls.

## Tool Use
1. Make sure to adhere to the tools schema.
2. Provide every required argument.
3. DO NOT use tools to access items that are already available in the context section.
4. Based on Tool Status take decisions on next steps carefully.

## Feedback Handling
If feedback_received: Review feedback + priors; identify tasks for improvements; analyze; apply mods; generate new plan.
"#

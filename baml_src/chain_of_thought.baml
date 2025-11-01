template_string ChainOfThought(action: string?) #"
# Chain of Thought Reasoning

Before you respond, engage in a step-by-step thinking process, which is crucial for complex tasks. Your thought process should cover your primary objective, what relevant information is available in yourSutra Memory, what you can learn from past interactions and code snippets (History & Context), what information you are missing and need to do next (Needs Assessment), and finally, formulate an optimal next step and what you will need to complete it (Action Plan). This structured thinking will help you make better decisions. After your thinking process, provide your structured response in JSON.

Example:
- ...
- ...
...
{
  ... // schema
}
"#

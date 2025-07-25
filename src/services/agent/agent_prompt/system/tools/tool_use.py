TOOL_USE_INFORMATION = """====

TOOL USE

You have access to a set of tools that are executed upon the user's approval. You can use one tool per message, and will receive the result of that tool use in the user's response. You use tools step-by-step to accomplish a given task, with each tool use informed by the result of the previous tool use.

# Tool Use Formatting

Tool uses are formatted using XML-style tags. The tool name itself becomes the XML tag name. Each parameter is enclosed within its own set of tags. Here's the structure:

<actual_tool_name>
<parameter1_name>value1</parameter1_name>
<parameter2_name>value2</parameter2_name>
...
</actual_tool_name>

For example, to use the search_keyword tool:

<search_keyword>
<keyword>defaultRouter.get</keyword>
<before_lines>0</before_lines>  
<after_lines>2</after_lines>
<case_sensitive>true</case_sensitive>
<regex>false</regex>
</search_keyword>

Always use the actual tool name as the XML tag name for proper parsing and execution.
"""

template_string SimpleSearchKeywordToolTemplate() #"
## search_keyword

Search for keywords or patterns in the codebase using ripgrep. Supports single keywords, multiple patterns (using OR), and regex patterns. Faster than terminal commands and provides line numbers for precise location tracking.

Notes:
  - Use specific, targeted keywords. Avoid broad "kitchen sink" searches that return massive results and cause token limit issues.
  - Setting `'regex': false` means fixed string matching ('|' pipe or special regex will not work). it will search for the exact string you provide.
"#

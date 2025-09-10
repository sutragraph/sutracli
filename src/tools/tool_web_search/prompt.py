WEB_SEARCH_TOOL = """## web_search
Description: Use this tool to search the web using the Brave Search API. Supports multiple search types (web, news, images, videos), time-based filtering, safe search controls, and comprehensive result parsing. Includes built-in rate limiting and error handling for reliable search operations.

Required Parameters:
- query: The search query string

Optional Parameters:
- time_filter: Time-based filtering options
  - "pd": Results from the past day
  - "pw": Results from the past week
  - "pm": Results from the past month
  - "py": Results from the past year
  - leave empty for no time filter (default)
- search_type: Type of search to perform
  - "search": Web search (default)
  - "news": News search
  - "images": Image search
  - "videos": Video search
- count: Number of results to return (1-20, default: 10)
- offset: Offset for pagination (default: 0)
- country: Country code for localized results (e.g., "US", "GB", default: "US")
- search_lang: Language for search results (e.g., "en", "es")
- spellcheck: Enable spell checking (default: true)
- result_filter: Filter specific result types (list of strings)
- goggles_id: Goggles ID for custom search ranking
- extra_snippets: Include extra snippets in results (default: false)

Usage:
<web_search>
<query>search terms here</query>
<search_type>search</search_type>
<time_filter>pw</time_filter>
<count>10</count>
</web_search>

Examples:
1. Basic web search:
<web_search>
<query>artificial intelligence trends</query>
</web_search>

2. Recent news search:
<web_search>
<query>climate change summit</query>
<search_type>news</search_type>
<time_filter>pw</time_filter>
<count>5</count>
</web_search>

3. Paginated web search:
<web_search>
<query>machine learning algorithms</query>
<count>20</count>
<offset>20</offset>
</web_search>"""

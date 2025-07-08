WEB_SEARCH_TOOL = """## web_search
Description: Use this tool to search the web using the Brave Search API. Supports multiple search types (web, news, images, videos), time-based filtering, safe search controls, and comprehensive result parsing. Includes built-in rate limiting and error handling for reliable search operations.

Required Parameters:
- query: The search query string

Optional Parameters:
- time_filter: Time-based filtering options
  - "PAST_DAY" or "pd": Results from the past day
  - "PAST_WEEK" or "pw": Results from the past week  
  - "PAST_MONTH" or "pm": Results from the past month
  - "PAST_YEAR" or "py": Results from the past year
  - "ALL_TIME" or null: All time results (default)
- search_type: Type of search to perform
  - "WEB": Web search (default)
  - "NEWS": News search
  - "IMAGES": Image search
  - "VIDEOS": Video search
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
<search_type>WEB</search_type>
<time_filter>PAST_WEEK</time_filter>
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
<search_type>NEWS</search_type>
<time_filter>PAST_WEEK</time_filter>
<count>5</count>
</web_search>

3. Image search with safe search:
<web_search>
<query>mountain landscapes</query>
<search_type>IMAGES</search_type>
<safe_search>STRICT</safe_search>
<count>15</count>
</web_search>

4. Localized search with language preferences:
<web_search>
<query>local restaurants</query>
<country>GB</country>
<search_lang>en</search_lang>
<ui_lang>en-GB</ui_lang>
<extra_snippets>true</extra_snippets>
</web_search>

5. Video search for recent content:
<web_search>
<query>python tutorial beginners</query>
<search_type>VIDEOS</search_type>
<time_filter>PAST_MONTH</time_filter>
<count>8</count>
</web_search>

6. Paginated web search:
<web_search>
<query>machine learning algorithms</query>
<count>20</count>
<offset>20</offset>
</web_search>"""

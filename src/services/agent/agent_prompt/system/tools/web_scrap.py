WEB_SCRAP_TOOL = """## web_scraper
Description: Extract and scrape content from web pages using trafilatura. Supports fetching clean text content, HTML content, and converting HTML to markdown format. Includes robust error handling, retry mechanisms, and configurable extraction options for reliable web scraping operations.

Parameters:
- url: (required) The URL to fetch and extract content from
- output_format: (optional) Format for the extracted content
  - "text": Clean text content (default)
  - "html": HTML content with formatting preserved
  - "markdown": Content converted to markdown format

Usage:
<web_scraper>
<url>https://example.com/article</url>
<output_format>text</output_format>
</web_scraper>

Examples:
1. Basic text extraction:
<web_scraper>
<url>https://example.com/blog-post</url>
</web_scraper>

2. Extract HTML content:
<web_scraper>
<url>https://news.example.com/article</url>
<output_format>html</output_format>
</web_scraper>

3. Extract and convert to markdown:
<web_scraper>
<url>https://docs.example.com/guide</url>
<output_format>markdown</output_format>
</web_scraper>

4. Clean text extraction from news article:
<web_scraper>
<url>https://techcrunch.com/2024/01/15/ai-breakthrough</url>
<output_format>text</output_format>
</web_scraper>

5. Extract HTML for further processing:
<web_scraper>
<url>https://wikipedia.org/wiki/Machine_Learning</url>
<output_format>html</output_format>
</web_scraper>

6. Get markdown formatted content:
<web_scraper>
<url>https://github.com/user/repo/blob/main/README.md</url>
<output_format>markdown</output_format>
</web_scraper>
"""

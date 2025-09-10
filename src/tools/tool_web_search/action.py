import requests
import time
import threading
from typing import List, Optional, Iterator, Dict, Any
from loguru import logger
from dataclasses import dataclass, field
from enum import Enum
from config.settings import config

from models.agent import AgentAction


class TimeFilter(Enum):
    """Time filter options for search results"""

    PAST_DAY = "pd"
    PAST_WEEK = "pw"
    PAST_MONTH = "pm"
    PAST_YEAR = "py"
    ALL_TIME = None


class SafeSearch(Enum):
    """Safe search filter options"""

    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"


class SearchType(Enum):
    """Search type options"""

    WEB = "search"
    NEWS = "news"
    IMAGES = "images"
    VIDEOS = "videos"


@dataclass
class SearchResult:
    """Data class for search results"""

    title: str
    url: str
    description: str
    published_time: Optional[str] = None
    favicon_url: Optional[str] = None
    meta_url: Optional[dict] = None
    extra: Optional[dict] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Data class for complete search response"""

    results: List[SearchResult]
    query: str
    total_results: int
    search_time: float
    suggestions: List[str] = field(default_factory=list)
    infobox: Optional[dict] = None
    knowledge_graph: Optional[dict] = None


class WebSearch:
    """
    Static Brave Search API class with rate limiting and advanced filtering capabilities.

    Features:
    - Rate limiting with configurable requests per minute
    - Time-based filtering (past day, week, month, year)
    - Safe search filtering
    - Multiple search types (web, news, images, videos)
    - Comprehensive error handling and logging
    - Thread-safe rate limiting
    """

    _BASE_URL = "https://api.search.brave.com/res/v1"
    _rate_limit_lock = threading.Lock()
    _request_times = []
    _api_key = config.web_search.api_key
    _requests_per_minute = config.web_search.requests_per_minute
    _timeout = config.web_search.timeout

    @classmethod
    def _enforce_rate_limit(cls):
        """Thread-safe rate limiting implementation"""
        with cls._rate_limit_lock:
            current_time = time.time()

            # Remove timestamps older than 1 minute
            cls._request_times = [
                timestamp
                for timestamp in cls._request_times
                if current_time - timestamp < 60
            ]

            # Check if we've exceeded the rate limit
            if len(cls._request_times) >= cls._requests_per_minute:
                sleep_time = 60 - (current_time - cls._request_times[0])
                if sleep_time > 0:
                    logger.warning(
                        f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds"
                    )
                    time.sleep(sleep_time)
                    # Clean up old timestamps after sleeping
                    current_time = time.time()
                    cls._request_times = [
                        timestamp
                        for timestamp in cls._request_times
                        if current_time - timestamp < 60
                    ]

            # Record this request
            cls._request_times.append(current_time)

    @classmethod
    def _build_search_url(cls, search_type: SearchType) -> str:
        """Build the search URL based on search type"""
        if search_type == SearchType.WEB:
            return f"{cls._BASE_URL}/web/search"
        elif search_type == SearchType.NEWS:
            return f"{cls._BASE_URL}/news/search"
        elif search_type == SearchType.IMAGES:
            return f"{cls._BASE_URL}/images/search"
        elif search_type == SearchType.VIDEOS:
            return f"{cls._BASE_URL}/videos/search"
        else:
            return f"{cls._BASE_URL}/web/search"

    @classmethod
    def _parse_results(
        cls, response_data: dict, search_type: SearchType
    ) -> List[SearchResult]:
        """Parse API response into SearchResult objects"""
        results = []

        if search_type == SearchType.WEB:
            web_results = response_data.get("web", {}).get("results", [])
            for result in web_results:
                results.append(
                    SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        description=result.get("description", ""),
                        published_time=result.get("published_time"),
                        favicon_url=result.get("favicon_url"),
                        meta_url=result.get("meta_url"),
                        extra=result.get("extra", {}),
                    )
                )

        elif search_type == SearchType.NEWS:
            news_results = response_data.get("news", {}).get("results", [])
            for result in news_results:
                results.append(
                    SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        description=result.get("description", ""),
                        published_time=result.get("published_time"),
                        favicon_url=result.get("favicon_url"),
                        meta_url=result.get("meta_url"),
                        extra={
                            "breaking": result.get("breaking", False),
                            "age": result.get("age"),
                        },
                    )
                )

        elif search_type == SearchType.IMAGES:
            image_results = response_data.get("images", {}).get("results", [])
            for result in image_results:
                results.append(
                    SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        description=result.get("description", ""),
                        extra={
                            "thumbnail": result.get("thumbnail", {}).get("src"),
                            "properties": result.get("properties", {}),
                            "source": result.get("source"),
                        },
                    )
                )

        elif search_type == SearchType.VIDEOS:
            video_results = response_data.get("videos", {}).get("results", [])
            for result in video_results:
                results.append(
                    SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        description=result.get("description", ""),
                        published_time=result.get("published_time"),
                        extra={
                            "thumbnail": result.get("thumbnail", {}).get("src"),
                            "duration": result.get("duration"),
                            "views": result.get("views"),
                        },
                    )
                )

        return results

    @classmethod
    def search(
        cls,
        query: str,
        time_filter: Optional[TimeFilter] = None,
        safe_search: SafeSearch = SafeSearch.MODERATE,
        search_type: SearchType = SearchType.WEB,
        count: int = 10,
        offset: int = 0,
        country: str = "US",
        search_lang: Optional[str] = None,
        ui_lang: Optional[str] = None,
        spellcheck: bool = True,
        result_filter: Optional[List[str]] = None,
        goggles_id: Optional[str] = None,
        units: str = "metric",
        extra_snippets: bool = False,
    ) -> Optional[SearchResponse]:
        """
        Perform a search using the Brave Search API.

        Args:
            query: Search query string
            time_filter: Time-based filtering (past day='pd', past week='pw', etc.)
            safe_search: Safe search filtering level
            search_type: Type of search (web, news, images, videos)
            count: Number of results to return (1-20, default: 10)
            offset: Offset for pagination (default: 0)
            country: Country code for localized results (e.g., 'US', 'GB')
            search_lang: Language for search results (e.g., 'en', 'es')
            ui_lang: UI language (e.g., 'en-US', 'es-ES')
            spellcheck: Enable spell checking
            result_filter: Filter specific result types
            goggles_id: Goggles ID for custom search ranking
            units: Unit system ('metric' or 'imperial')
            extra_snippets: Include extra snippets in results

        Returns:
            SearchResponse object containing results and metadata, or None if failed
        """

        if not cls._api_key:
            logger.error("API key not configured.")
            return None

        if not query.strip():
            logger.error("Search query cannot be empty")
            return None

        # Enforce rate limiting
        cls._enforce_rate_limit()

        # Build request parameters
        params = {
            "q": query.strip(),
            "count": max(1, min(20, count)),
            "offset": max(0, offset),
            "safesearch": safe_search.value,
            "units": units,
            "spellcheck": "1" if spellcheck else "0",
            "extra_snippets": "1" if extra_snippets else "0",
        }

        # Add optional parameters
        if time_filter and time_filter.value:
            params["tf"] = time_filter.value

        if country:
            params["country"] = country.upper()

        if search_lang:
            params["search_lang"] = search_lang.lower()

        if ui_lang:
            params["ui_lang"] = ui_lang

        if result_filter:
            params["result_filter"] = ",".join(result_filter)

        if goggles_id:
            params["goggles_id"] = goggles_id

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": cls._api_key,
        }

        # Build URL
        url = cls._build_search_url(search_type)

        print(
            f"Searching for: '{query}' (type: {search_type.value}, filter: {time_filter.value if time_filter else 'none'})"
        )

        start_time = time.time()
        response = requests.get(
            url, params=params, headers=headers, timeout=cls._timeout
        )
        search_time = time.time() - start_time

        response.raise_for_status()

        data = response.json()

        results = cls._parse_results(data, search_type)

        suggestions = []
        infobox = None
        knowledge_graph = None
        total_results = 0

        if search_type == SearchType.WEB:
            web_data = data.get("web", {})
            total_results = web_data.get("total", 0)
            query_data = data.get("query", {})
            suggestions = query_data.get("altered", [])
            infobox = data.get("infobox")
            knowledge_graph = data.get("knowledge_graph")

        elif search_type == SearchType.NEWS:
            news_data = data.get("news", {})
            total_results = news_data.get("total", 0)

        elif search_type == SearchType.IMAGES:
            images_data = data.get("images", {})
            total_results = images_data.get("total", 0)

        elif search_type == SearchType.VIDEOS:
            videos_data = data.get("videos", {})
            total_results = videos_data.get("total", 0)

        logger.success(
            f"Search completed: {len(results)} results in {search_time:.2f}s"
        )

        return SearchResponse(
            results=results,
            query=query,
            total_results=total_results,
            search_time=search_time,
            suggestions=suggestions,
            infobox=infobox,
            knowledge_graph=knowledge_graph,
        )


def execute_web_search_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """
    Execute web search action using the WebSearch class.
    """
    query = action.parameters.get("query", "").strip()

    if not query:
        yield {
            "type": "tool_error",
            "error": "Missing required parameter: query",
            "tool_name": "web_search",
        }
        return

    try:
        # Parse and validate parameters
        time_filter = None
        time_filter_str = action.parameters.get("time_filter")
        if time_filter_str:
            try:
                time_filter = TimeFilter(time_filter_str)
            except ValueError:
                yield {
                    "type": "tool_error",
                    "error": f"Invalid time_filter: {time_filter_str}. Valid options: pd, pw, pm, py",
                    "tool_name": "web_search",
                }
                return

        safe_search = SafeSearch.MODERATE
        safe_search_str = action.parameters.get("safe_search", safe_search)
        try:
            safe_search = SafeSearch(safe_search_str)
        except ValueError:
            yield {
                "type": "tool_error",
                "error": f"Invalid safe_search: {safe_search_str}. Valid options: off, moderate, strict",
                "tool_name": "web_search",
            }
            return

        search_type = SearchType.WEB
        search_type_str = action.parameters.get("search_type", search_type)
        try:
            search_type = SearchType(search_type_str)
        except ValueError:
            yield {
                "type": "tool_error",
                "error": f"Invalid search_type: {search_type_str}. Valid options: web, news, images, videos",
                "tool_name": "web_search",
            }
            return

        count = action.parameters.get("count", 10)
        offset = action.parameters.get("offset", 0)
        country = action.parameters.get("country", "US")
        search_lang = action.parameters.get("search_lang")
        spellcheck = action.parameters.get("spellcheck", True)
        result_filter = action.parameters.get("result_filter")
        goggles_id = action.parameters.get("goggles_id")
        extra_snippets = action.parameters.get("extra_snippets", False)

        try:
            count = int(count)
            offset = int(offset)
            if count < 1 or count > 20:
                raise ValueError("count must be between 1 and 20")
            if offset < 0:
                raise ValueError("offset must be non-negative")
        except (ValueError, TypeError) as e:
            yield {
                "type": "tool_error",
                "error": f"Invalid numeric parameter: {str(e)}",
                "tool_name": "web_search",
            }
            return

        print(f"Executing web search for query: '{query}'")

        search_response = WebSearch.search(
            query=query,
            time_filter=time_filter,
            safe_search=safe_search,
            search_type=search_type,
            count=count,
            offset=offset,
            country=country,
            search_lang=search_lang,
            spellcheck=spellcheck,
            result_filter=result_filter,
            goggles_id=goggles_id,
            extra_snippets=extra_snippets,
        )

        if search_response:
            results_dict = []
            for result in search_response.results:
                result_dict = {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                    "published_time": result.published_time,
                    "favicon_url": result.favicon_url,
                    "meta_url": result.meta_url,
                    "extra": result.extra,
                }
                results_dict.append(result_dict)

            yield {
                "type": "tool_use",
                "tool_name": "web_search",
                "results": results_dict,
                "query": search_response.query,
                "total_results": search_response.total_results,
                "search_time": search_response.search_time,
                "suggestions": search_response.suggestions,
                "infobox": search_response.infobox,
                "knowledge_graph": search_response.knowledge_graph,
                "search_type": search_type.value,
            }
        else:
            yield {
                "type": "tool_error",
                "error": f"Search failed for query: '{query}'.",
                "tool_name": "web_search",
            }

    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while executing the web search tool: {e}"
        )
        yield {"type": "tool_error", "error": str(e), "tool_name": "web_search"}

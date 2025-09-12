import time
from typing import Any, Dict, Iterator, Optional
from urllib.parse import urlparse

import markdownify
import requests
import trafilatura
from loguru import logger
from trafilatura.settings import use_config

from config.settings import config
from models.agent import AgentAction


def execute_web_scraper_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    url = action.parameters.get("url", "")
    output_format = action.parameters.get("output_format", "text").lower().strip()

    if not url:
        yield {
            "type": "tool_error",
            "error": "Missing required parameter: url",
            "tool_name": "web_scrap",
        }
        return

    content = None
    try:
        if output_format == "text":
            content = WebScraper.fetch_text_content(url)
        elif output_format == "html":
            content = WebScraper.fetch_html_content(url)
        elif output_format == "markdown":
            html_content = WebScraper.fetch_html_content(url)
            if html_content:
                content = WebScraper.html_to_markdown(html_content)
        else:
            yield {
                "type": "tool_error",
                "error": f"Unsupported output format: {output_format}. Supported formats are: text, html, markdown",
                "tool_name": "web_scrap",
            }
            return

        if content:
            yield {
                "type": "tool_use",
                "tool_name": "web_scrap",
                "content": content,
                "url": url,
                "output_format": output_format,
            }
        else:
            yield {
                "type": "tool_error",
                "error": f"Failed to extract content from URL: {url}",
                "tool_name": "web_scrap",
            }

    except Exception as e:
        logger.exception(
            f"An unexpected error occurred while executing the web scraper tool: {e}"
        )
        yield {"type": "tool_error", "error": str(e), "tool_name": "web_scraper"}


class WebScraper:
    """
    Static class for web scraping using trafilatura with loguru logging.
    Supports fetching both HTML and text content from web pages.
    All configuration is driven by config.web_scrap settings.
    """

    _session = None

    @classmethod
    def _get_session(cls) -> requests.Session:
        """Get or create a requests session."""
        if cls._session is None:
            cls._session = requests.Session()
            cls._session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                }
            )
            logger.debug("HTTP session created")
        return cls._session

    @classmethod
    def _validate_url(cls, url: str) -> bool:
        """Validate if URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @classmethod
    def fetch_content(cls, url: str, return_html: bool = False) -> Optional[str]:
        """
        Fetch content from a web page using trafilatura.
        All configuration is taken from config.web_scrap.

        Args:
            url (str): The URL to fetch content from
            return_html (bool): If True, returns HTML content; if False, returns text content

        Returns:
            Optional[str]: Extracted content or None if failed
        """

        if not cls._validate_url(url):
            logger.error(f"Invalid URL format: {url}")
            return None

        timeout = getattr(config.web_scrap, "timeout", 30)
        max_retries = getattr(config.web_scrap, "max_retries", 3)
        delay_between_retries = getattr(config.web_scrap, "delay_between_retries", 1.0)

        print(f"Fetching content from: {url}")

        trafilatura_config = use_config()

        if (
            hasattr(config.web_scrap, "trafilatura_config")
            and config.web_scrap.trafilatura_config
        ):
            for key, value in config.web_scrap.trafilatura_config.items():
                setattr(trafilatura_config, key, value)
            logger.debug(
                f"Applied trafilatura settings: {config.web_scrap.trafilatura_config}"
            )

        session = cls._get_session()

        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{max_retries} for {url}")
                response = session.get(url, timeout=timeout)
                response.raise_for_status()

                logger.success(
                    f"Successfully fetched webpage (Status: {response.status_code})"
                )

                if return_html:
                    extract_options = {
                        "output_format": "html",
                        "config": trafilatura_config,
                        "include_comments": getattr(
                            config.web_scrap, "include_comments", False
                        ),
                        "include_tables": getattr(
                            config.web_scrap, "include_tables", True
                        ),
                        "include_images": getattr(
                            config.web_scrap, "include_images", True
                        ),
                        "include_links": getattr(
                            config.web_scrap, "include_links", True
                        ),
                    }
                    content = trafilatura.extract(response.text, **extract_options)
                    content_type = "HTML"
                else:
                    extract_options = {
                        "config": trafilatura_config,
                        "include_comments": getattr(
                            config.web_scrap, "include_comments", False
                        ),
                        "include_tables": getattr(
                            config.web_scrap, "include_tables", True
                        ),
                    }
                    content = trafilatura.extract(response.text, **extract_options)
                    content_type = "text"

                if content:
                    logger.success(f"Successfully extracted {content_type} content")
                    logger.debug(f"Content length: {len(content)} characters")
                    return content
                else:
                    logger.warning(f"No content extracted from {url}")
                    return None

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout occurred for {url} (attempt {attempt + 1}/{max_retries})"
                )
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Request error for {url}: {str(e)} (attempt {attempt + 1}/{max_retries})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error for {url}: {str(e)} (attempt {attempt + 1}/{max_retries})"
                )

            # Wait before retrying (except for the last attempt)
            if attempt < max_retries - 1:
                logger.debug(f"Waiting {delay_between_retries} seconds before retry...")
                time.sleep(delay_between_retries)

        logger.error(f"Failed to fetch content from {url} after {max_retries} attempts")
        return None

    @classmethod
    def fetch_html_content(cls, url: str) -> Optional[str]:
        """
        Convenience method to fetch HTML content.

        Args:
            url (str): The URL to fetch content from

        Returns:
            Optional[str]: Extracted HTML content or None if failed
        """
        return cls.fetch_content(url=url, return_html=True)

    @classmethod
    def fetch_text_content(cls, url: str) -> Optional[str]:
        """
        Convenience method to fetch text content.

        Args:
            url (str): The URL to fetch content from

        Returns:
            Optional[str]: Extracted text content or None if failed
        """
        return cls.fetch_content(url=url, return_html=False)

    @classmethod
    def html_to_markdown(cls, html_content: str) -> Optional[str]:
        """
        Convert HTML content to markdown format.
        Configuration is taken from config.web_scrap.markdown_options.

        Args:
            html_content (str): HTML content to convert

        Returns:
            Optional[str]: Converted markdown content or None if failed
        """

        try:
            options = getattr(
                config.web_scrap,
                "markdown_options",
                {
                    "heading_style": "SETEXT",
                    "bullets": "*",
                    "wrap": True,
                    "wrap_width": 80,
                    "convert": [
                        "a",
                        "p",
                        "h1",
                        "h2",
                        "h3",
                        "h4",
                        "h5",
                        "h6",
                        "ul",
                        "ol",
                        "li",
                        "strong",
                        "em",
                        "br",
                        "hr",
                        "blockquote",
                        "code",
                        "pre",
                        "img",
                        "table",
                        "thead",
                        "tbody",
                        "tr",
                        "td",
                        "th",
                    ],
                },
            )

            final_options = options.copy()

            if "convert" in final_options:
                # If convert is specified, remove strip to avoid conflict
                if "strip" in final_options:
                    final_options.pop("strip")
                    logger.debug(
                        "Removed 'strip' option because 'convert' was specified"
                    )

            logger.debug(f"Converting HTML to markdown with options: {final_options}")

            markdown_content = markdownify.markdownify(html_content, **final_options)

            if markdown_content:
                logger.success(
                    f"Successfully converted HTML to markdown ({len(markdown_content)} characters)"
                )
                return markdown_content.strip()
            else:
                logger.warning("HTML to markdown conversion resulted in empty content")
                return None

        except Exception as e:
            logger.error(f"Error converting HTML to markdown: {str(e)}")
            return None

    @classmethod
    def close_session(cls) -> None:
        """Close the requests session."""
        if cls._session:
            cls._session.close()
            cls._session = None
            print("HTTP session closed")


# Alias for consistency with new naming convention
execute_web_scrap_action = execute_web_scraper_action

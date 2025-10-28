"""Utility functions for QA Engineer agent."""

from typing import List, Optional

from loguru import logger


def format_failed_tests_message(
    failed_tests: Optional[List], agent_name: str = "QAEngineer"
) -> str:
    """Format failed tests into a readable string.

    Args:
        failed_tests: List of failed test objects with test_name and test_details
        agent_name: Name of the agent for logging (default: "QAEngineer")

    Returns:
        Formatted string with failed test information
    """
    if not failed_tests or len(failed_tests) == 0:
        return ""

    logger.debug(
        f"[{agent_name}] Tests failed: {len(failed_tests)}. Sending failure to Developer"
    )

    context = "Failed Tests:\n"
    for i, test in enumerate(failed_tests, 1):
        context += f'{i}. "{test.test_name}" : "{test.test_details}"\n'

    return context

"""Debug utilities for handling debug mode confirmations."""

# Global flags to track debug mode and auto mode
_debug_mode = False
_auto_mode = False


def set_debug_mode(enabled: bool) -> None:
    """
    Set debug mode flag.

    Args:
        enabled: True to enable debug mode, False to disable
    """
    global _debug_mode
    _debug_mode = enabled


def set_auto_mode(enabled: bool) -> None:
    """
    Set auto mode flag.

    Args:
        enabled: True to enable auto mode, False to disable
    """
    global _auto_mode
    _auto_mode = enabled


def is_debug_mode() -> bool:
    """
    Check if debug mode is enabled.

    Returns:
        bool: True if debug mode is enabled, False otherwise
    """
    return _debug_mode


def is_auto_mode() -> bool:
    """
    Check if auto mode is enabled.

    Returns:
        bool: True if auto mode is enabled, False otherwise
    """
    return _auto_mode


def get_user_confirmation_for_llm_call() -> bool:
    """
    Ask user for confirmation before making an LLM call in debug mode.

    Args:
        context: Description of what the LLM call is for

    Returns:
        bool: True if user wants to proceed, False otherwise
    """
    if not is_debug_mode():
        return True

    # If auto mode is enabled, automatically proceed without asking
    if is_auto_mode():
        print("🤖 Auto mode enabled - proceeding with LLM call")
        return True

    try:
        response = input("Do you want to make new call? (y/n): ").lower().strip()
        return response in ["yes", "y"]
    except (KeyboardInterrupt, EOFError):
        print("\n❌ User cancelled the operation")
        return False
    except Exception:
        # If there's any issue with input, default to proceeding
        return True

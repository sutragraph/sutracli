"""Debug utilities for handling debug mode confirmations."""

# Global flag to track debug mode
_debug_mode = False

def set_debug_mode(enabled: bool) -> None:
    """
    Set debug mode flag.
    
    Args:
        enabled: True to enable debug mode, False to disable
    """
    global _debug_mode
    _debug_mode = enabled

def is_debug_mode() -> bool:
    """
    Check if debug mode is enabled.
    
    Returns:
        bool: True if debug mode is enabled, False otherwise
    """
    return _debug_mode


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

    try:
        response = input("Do you want to make new call? (y/n): ").lower().strip()
        return response in ['yes', 'y']
    except (KeyboardInterrupt, EOFError):
        print("\n❌ User cancelled the operation")
        return False
    except Exception:
        # If there's any issue with input, default to proceeding
        return True

from .llama_client import LlamaClient
from .aws_client import AWSClient
from .gemini_client import GeminiClient
from .anthropic_client import AnthropicClient
from .superllm_client import SuperLLMClient
from config import config
from loguru import logger
import threading

_cached_client = None
_cached_provider = None
_cache_lock = threading.Lock()

def llm_client_factory():
    """
    Factory function that returns a cached LLM client instance.
    Only one client per provider is created per session.
    """
    global _cached_client, _cached_provider

    current_provider = config.llm.provider.lower()

    with _cache_lock:
        # Return cached client if it's for the same provider
        if _cached_client is not None and _cached_provider == current_provider:
            logger.debug(f"🔄 Reusing cached {current_provider.upper()} client")
            return _cached_client

        # Create new client and cache it
        print(f"🤖 Initializing {current_provider.upper()} client")

        try:
            if current_provider == "llama":
                client = LlamaClient()
            elif current_provider == "aws":
                client = AWSClient()
            elif current_provider == "gemini":
                client = GeminiClient()
            elif current_provider == "anthropic":
                client = AnthropicClient()
            elif current_provider == "superllm":
                client = SuperLLMClient()
            else:
                raise ValueError(
                    f"Unsupported LLM provider: {current_provider}. Supported providers: llama, aws, gemini, anthropic, superllm"
                )

            _cached_client = client
            _cached_provider = current_provider
            print(f"✅ {current_provider.upper()} client initialized successfully")
            return client

        except Exception as e:
            logger.error(
                f"❌ Failed to initialize {current_provider.upper()} client: {e}"
            )
            raise


def clear_client_cache():
    """Clear the client cache - useful for testing or configuration changes."""
    global _cached_client, _cached_provider
    with _cache_lock:
        _cached_client = None
        _cached_provider = None

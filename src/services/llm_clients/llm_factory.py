from .llama_client import LlamaClient
from .aws_client import AWSClient
from .gemini_client import GeminiClient
from .anthropic_client import AnthropicClient
from .superllm_client import SuperLLMClient
from config import config


def llm_client_factory():
    provider = config.llm.provider.lower()
    if provider == "llama":
        return LlamaClient()
    elif provider == "aws":
        return AWSClient()
    elif provider == "gemini":
        return GeminiClient()
    elif provider == "anthropic":
        return AnthropicClient()
    elif provider == "superllm":
        return SuperLLMClient()
    return LlamaClient()

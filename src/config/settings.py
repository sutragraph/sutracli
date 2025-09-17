"""
Configuration management for SutraKnowledge.
Centralizes all configurable paths and settings.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# BAML provider mapping for dynamic client creation
BAML_PROVIDER_MAPPING = {
    "aws_bedrock": {
        "provider": "aws-bedrock",
        "client_name": "AwsBedrock",
    },
    "anthropic": {
        "provider": "anthropic",
        "client_name": "AnthropicClaude",
    },
    "openai": {
        "provider": "openai",
        "client_name": "OpenAIChatGPT",
    },
    "google_ai": {
        "provider": "google-ai",
        "client_name": "GoogleGemini",
    },
    "vertex_ai": {
        "provider": "vertex-ai",
        "client_name": "GCPVertexAI",
    },
    "azure_openai": {
        "provider": "azure-openai",
        "client_name": "AzureOpenAI",
    },
    "azure_aifoundry": {
        "provider": "openai-generic",
        "client_name": "AzureAIFoundry",
    },
    "openrouter": {
        "provider": "openai-generic",
        "client_name": "OpenRouter",
    },
}

# Provider information for UI/CLI display
PROVIDER_INFO = [
    {
        "name": "Anthropic",
        "key": "anthropic",
        "description": "Claude models",
    },
    {
        "name": "AWS Bedrock",
        "key": "aws_bedrock",
        "description": "AWS managed AI services",
    },
    {
        "name": "Google Gemini",
        "key": "google_ai",
        "description": "Google's Gemini models via Google AI API",
    },
    {
        "name": "Google Vertex AI",
        "key": "vertex_ai",
        "description": "Google Cloud Vertex AI models with gcloud auth",
    },
    {
        "name": "Azure OpenAI",
        "key": "azure_openai",
        "description": "Azure OpenAI Service",
    },
    {
        "name": "OpenAI",
        "key": "openai",
        "description": "ChatGPT models via OpenAI API",
    },
    {
        "name": "Azure AI Foundry",
        "key": "azure_aifoundry",
        "description": "All supported models on Azure AI Foundry client",
    },
    {
        "name": "OpenRouter",
        "key": "openrouter",
        "description": "All supported models on OpenRouter client",
    },
]


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    # Main knowledge graph database
    knowledge_graph_db: str

    # Vector embeddings database
    embeddings_db: str

    # Connection settings
    connection_timeout: int
    max_retry_attempts: int
    batch_size: int


@dataclass
class AWSConfig:
    """AWS configuration for Bedrock."""

    model_id: str
    access_key_id: str
    secret_access_key: str
    region: str
    max_tokens: str  # Maximum output tokens per response


@dataclass
class AnthropicConfig:
    """Anthropic configuration."""

    api_key: str
    model_id: str
    max_tokens: str  # Maximum output tokens per response


@dataclass
class OpenAIConfig:
    """OpenAI configuration."""

    api_key: str
    model_id: str
    max_tokens: str  # Maximum output tokens per response


@dataclass
class GeminiConfig:
    """Google Gemini configuration."""

    api_key: str
    model_id: str
    max_tokens: str  # Maximum output tokens per response
    base_url: str = ""  # Optional base URL


@dataclass
class VertexAIConfig:
    """Google Vertex AI configuration."""

    location: str
    model_id: str
    max_tokens: str  # Maximum output tokens per response


@dataclass
class AzureConfig:
    """Azure OpenAI configuration."""

    api_key: str
    base_url: str
    api_version: str
    max_tokens: str  # Maximum output tokens per response


@dataclass
class AzureAIFoundryConfig:
    """Azure AI Foundry configuration."""

    api_key: str
    base_url: str
    max_tokens: str  # Maximum output tokens per response


@dataclass
class OpenRouterConfig:
    """OpenRouter configuration."""

    api_key: str
    model_id: str
    max_tokens: str  # Maximum output tokens per response
    http_referer: str = ""  # Optional
    x_title: str = ""  # Optional


@dataclass
class SuperLLMConfig:
    """SuperLLM configuration."""

    api_endpoint: str
    max_tokens: str  # Maximum output tokens per response
    firebase_token: str = ""  # Optional - will use token manager if empty
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str  # Options: "anthropic", "superllm", "openai", "vertex_ai", "azure_openai", "google_ai", "aws_bedrock", "azure_aifoundry", "openrouter"
    aws_bedrock: AWSConfig
    anthropic: AnthropicConfig
    openai: OpenAIConfig
    google_ai: GeminiConfig
    vertex_ai: VertexAIConfig
    azure_openai: AzureConfig
    azure_aifoundry: AzureAIFoundryConfig
    openrouter: OpenRouterConfig
    superllm: SuperLLMConfig


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str
    format: str
    logs_dir: str


@dataclass
class StorageConfig:
    """Storage directories configuration."""

    # Base data directory
    data_dir: str

    # Session storage
    sessions_dir: str

    # File changes and edits
    file_changes_dir: str
    file_edits_dir: str

    # Parser results (system-wide installation)
    parser_results_dir: str

    # Model storage
    models_dir: str


@dataclass
class EmbeddingConfig:
    """Embedding and vector search configuration."""

    # Model settings
    model_path: str

    # Tokenizer settings
    tokenizer_max_length: int  # Override tokenizer's default max length

    # Chunking settings
    max_tokens: int
    overlap_tokens: int


@dataclass
class WebSearchConfig:
    """Web search configuration"""

    api_key: str
    requests_per_minute: int
    timeout: int


@dataclass
class WebScrapperConfig:
    """Web scrap configuration."""

    timeout: int
    max_retries: int
    delay_between_retries: float
    include_comments: bool
    include_tables: bool
    include_images: bool
    include_links: bool
    trafilatura_config: dict
    markdown_options: dict


class Config:
    """Main configuration class."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration from JSON file."""
        self.config_file = config_file or os.getenv("SUTRAKNOWLEDGE_CONFIG")

        # If no config file is specified, use default path
        if not self.config_file:
            default_config_path = os.path.expanduser("~/.sutra/config/system.json")
            self.config_file = default_config_path

        if not os.path.exists(self.config_file):
            raise ValueError(
                f"Configuration file not found: {self.config_file}. "
                f"Please run 'sutrakit-setup' to create the configuration file, or set SUTRAKNOWLEDGE_CONFIG environment variable."
            )

        # Load from JSON file
        self._load_config()

        # Ensure directories exist
        self._ensure_directories()

    def _expand_paths_in_config(self, config_dict: dict) -> dict:
        """Recursively expand tilde paths in configuration dictionary."""
        expanded_config = {}
        for key, value in config_dict.items():
            if isinstance(value, str):
                # Expand tilde for any string that looks like a path
                if value.startswith("~/"):
                    # Use Path.home() for better cross-platform compatibility
                    expanded_config[key] = str(Path.home() / value[2:])
                else:
                    expanded_config[key] = value
            elif isinstance(value, dict):
                # Recursively handle nested dictionaries
                expanded_config[key] = self._expand_paths_in_config(value)
            else:
                # Keep other types as-is
                expanded_config[key] = value
        return expanded_config

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, "r") as f:
                config_data = json.load(f)

            # Expand all paths in the entire configuration
            config_data = self._expand_paths_in_config(config_data)

            # Initialize database config
            db_config = config_data.get("database", {})
            self.sqlite = DatabaseConfig(**db_config)

            # Initialize storage config
            storage_config = config_data.get("storage", {})
            self.storage = StorageConfig(**storage_config)

            # Initialize embedding config
            embedding_config = config_data.get("embedding", {})
            self.embedding = EmbeddingConfig(**embedding_config)

            # Initialize logging config
            logging_config = config_data.get("logging", {})
            self.logging = LoggingConfig(**logging_config)

            # Initialize web search config
            websearch_config = config_data.get("web_search", {})
            self.web_search = WebSearchConfig(**websearch_config)

            # Initialize web scrapper config
            webscrapper_config = config_data.get("web_scrap", {})
            self.web_scrap = WebScrapperConfig(**webscrapper_config)

            # Initialize LLM config
            llm_config = config_data.get("llm", {})
            if llm_config:
                aws_config = llm_config.get("aws_bedrock", {})
                anthropic_config = llm_config.get("anthropic", {})
                openai_config = llm_config.get("openai", {})
                gemini_config = llm_config.get("google_ai", {})
                vertex_ai_config = llm_config.get("vertex_ai", {})
                azure_config = llm_config.get("azure_openai", {})
                azure_aifoundry_config = llm_config.get("azure_aifoundry", {})
                openrouter_config = llm_config.get("openrouter", {})
                superllm_config = llm_config.get("superllm", {})
                self.llm = LLMConfig(
                    provider=llm_config.get("provider", "openai"),
                    aws_bedrock=AWSConfig(**aws_config) if aws_config else None,
                    anthropic=(
                        AnthropicConfig(**anthropic_config)
                        if anthropic_config
                        else None
                    ),
                    openai=(OpenAIConfig(**openai_config) if openai_config else None),
                    google_ai=(
                        GeminiConfig(**gemini_config) if gemini_config else None
                    ),
                    vertex_ai=(
                        VertexAIConfig(**vertex_ai_config) if vertex_ai_config else None
                    ),
                    azure_openai=(
                        AzureConfig(**azure_config) if azure_config else None
                    ),
                    azure_aifoundry=(
                        AzureAIFoundryConfig(**azure_aifoundry_config)
                        if azure_aifoundry_config
                        else None
                    ),
                    openrouter=(
                        OpenRouterConfig(**openrouter_config)
                        if openrouter_config
                        else None
                    ),
                    superllm=(
                        SuperLLMConfig(**superllm_config) if superllm_config else None
                    ),
                )
            else:
                self.llm = None

        except Exception as e:
            raise ValueError(f"Failed to load config file {self.config_file}: {e}")

    def _ensure_directories(self) -> None:
        """Ensure all configured directories exist."""
        directories = [
            self.storage.data_dir,
            self.storage.sessions_dir,
            self.storage.file_changes_dir,
            self.storage.file_edits_dir,
            self.storage.models_dir,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

        # Create parser results directory (may need sudo for /opt/)
        try:
            Path(self.storage.parser_results_dir).mkdir(parents=True, exist_ok=True)
        except PermissionError:
            print(
                f"Warning: Cannot create {self.storage.parser_results_dir} - permission denied"
            )


# Global configuration instance (lazy initialization)
_config_instance = None


def get_config(force_reload: bool = False) -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None or force_reload:
        _config_instance = Config()
    return _config_instance


def reload_config() -> None:
    """Reload the configuration by resetting the global instance."""
    global _config_instance
    _config_instance = None
    # Force immediate reload with fresh instance
    get_config(force_reload=True)


# Create a lazy config object
class _ConfigProxy:
    def __getattr__(self, name):
        return getattr(get_config(), name)


config = _ConfigProxy()


def get_baml_provider_mapping() -> dict:
    """Get the BAML provider mapping dictionary for dynamic client creation."""
    return BAML_PROVIDER_MAPPING


def get_provider_info() -> list:
    """Get the provider information list."""
    return PROVIDER_INFO


def get_available_providers() -> list:
    """Get list of available provider keys."""
    return list(BAML_PROVIDER_MAPPING.keys())


def is_provider_supported(provider: str) -> bool:
    """Check if a provider is supported."""
    return provider.lower() in BAML_PROVIDER_MAPPING

"""
Configuration management for SutraKnowledge.
Centralizes all configurable paths and settings.
"""

import os
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


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


@dataclass
class GCPConfig:
    """GCP configuration."""

    project_id: str
    location: str
    llm_endpoint: str
    api_key: str = ""  # Optional - for backward compatibility


@dataclass
class AnthropicConfig:
    """Anthropic configuration."""

    api_key: str
    model_id: str


@dataclass
class SuperLLMConfig:
    """SuperLLM configuration."""

    api_endpoint: str
    firebase_token: str = ""  # Optional - will use token manager if empty
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str  # Options: "gemini", "llama", "claude", "claude_gcp", "anthropic", "superllm"
    llama_model_id: str
    claude_model: str
    gemini_model: str
    aws: AWSConfig
    gcp: GCPConfig
    anthropic: AnthropicConfig
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
                aws_config = llm_config.get("aws", {})
                gcp_config = llm_config.get("gcp", {})
                anthropic_config = llm_config.get("anthropic", {})
                superllm_config = llm_config.get("superllm", {})
                self.llm = LLMConfig(
                    provider=llm_config.get("provider", "gemini"),
                    llama_model_id=llm_config.get(
                        "llama_model_id", "meta/llama-4-maverick-17b-128e-instruct-maas"
                    ),
                    claude_model=llm_config.get(
                        "claude_model", "claude-3-7-sonnet@20250219"
                    ),
                    gemini_model=llm_config.get("gemini_model", "gemini-2.5-flash"),
                    aws=AWSConfig(**aws_config) if aws_config else None,
                    gcp=(
                        GCPConfig(
                            api_key=gcp_config.get("api_key", ""),
                            project_id=gcp_config.get("project_id", ""),
                            location=gcp_config.get("location", ""),
                            llm_endpoint=gcp_config.get("llm_endpoint", ""),
                        )
                        if gcp_config
                        else None
                    ),
                    anthropic=(
                        AnthropicConfig(**anthropic_config)
                        if anthropic_config
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


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config() -> None:
    """Reload the configuration by resetting the global instance."""
    global _config_instance
    _config_instance = None
    # Force immediate reload
    get_config()


# Create a lazy config object
class _ConfigProxy:
    def __getattr__(self, name):
        return getattr(get_config(), name)


config = _ConfigProxy()

"""
Main package initialization.
"""

import os

# Set tokenizers parallelism before any imports to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


# Set up BAML environment variables from config on package import
# This ensures environment variables are available for BAML before any BAML imports
def _setup_baml_environment():
    """Set up BAML environment variables from config."""
    from config import config

    # Environment variable mapping for each provider
    ENV_VAR_MAPPING = {
        "aws": {
            "AWS_ACCESS_KEY_ID": "access_key_id",
            "AWS_SECRET_ACCESS_KEY": "secret_access_key",
            "AWS_MODEL_ID": "model_id",
            "AWS_REGION": "region",
        },
        "openai": {"OPENAI_API_KEY": "api_key", "OPENAI_MODEL_ID": "model_id"},
        "anthropic": {"ANTHROPIC_API_KEY": "api_key", "ANTHROPIC_MODEL_ID": "model_id"},
        "gcp": {"GOOGLE_API_KEY": "api_key", "GOOGLE_MODEL_ID": "model_id"},
    }

    if hasattr(config, "llm") and config.llm:
        provider = config.llm.provider.lower()

        # Get provider config from existing config system
        provider_config = getattr(config.llm, provider, None)

        if provider_config and provider in ENV_VAR_MAPPING:
            # Set environment variables based on provider mapping
            env_mapping = ENV_VAR_MAPPING.get(provider, {})

            for env_var, config_key in env_mapping.items():
                # Only set if not already set and config value exists
                if env_var not in os.environ:
                    value = getattr(provider_config, config_key, None)
                    if value:
                        os.environ[env_var] = str(value)


# Initialize BAML environment variables
_setup_baml_environment()

__version__ = "1.0.0"

# Note: Imports removed to avoid circular dependencies
# Import modules directly when needed:
# from graph import ASTToSqliteConverter, SQLiteConnection, GraphOperations
# from models import Project, File, FileData, BlockType, CodeBlock, Relationship, ExtractionData
# from indexer import export_ast_to_json

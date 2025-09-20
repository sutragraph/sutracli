// AWS Bedrock Client
client<llm> AwsBedrock {
  provider aws-bedrock
  options {
    access_key_id env.AWS_ACCESS_KEY_ID
    secret_access_key env.AWS_SECRET_ACCESS_KEY
    model env.AWS_MODEL_ID
    region env.AWS_REGION
    inference_configuration {
      temperature 0.1
      max_tokens env.AWS_MAX_TOKENS
    }
    allowed_role_metadata ["system", "user", "cache_control"]
  }
}

// Anthropic Client
client<llm> AnthropicClaude {
  provider anthropic
  options {
    api_key env.ANTHROPIC_API_KEY
    model env.ANTHROPIC_MODEL_ID
    temperature 0.1
    allowed_role_metadata ["system", "user", "cache_control"]
    headers {
      "anthropic-beta" "prompt-caching-2024-07-31"
    }
    max_tokens env.ANTHROPIC_MAX_TOKENS
  }
}

// OpenAI ChatGPT Client
client<llm> OpenAIChatGPT {
  provider openai
  options {
    api_key env.OPENAI_API_KEY
    model env.OPENAI_MODEL_ID
    temperature 0.1
    allowed_roles ["system", "user"]
    max_tokens env.OPENAI_MAX_TOKENS
  }
}

// Google Gemini Client
client<llm> GoogleGemini {
  provider google-ai
  options {
    api_key env.GEMINI_API_KEY
    model env.GEMINI_MODEL_ID
    base_url env.GEMINI_BASE_URL
    allowed_roles ["system", "user"]
    generationConfig {
      maxOutputTokens env.GEMINI_MAX_TOKENS
      temperature 0.1
    }
  }
}

// Google Cloud Vertex AI Client
client<llm> GCPVertexAI {
  provider vertex-ai
  options {
    model env.GCP_MODEL_ID
    location env.GCP_LOCATION
    allowed_roles ["system", "user"]
    generationConfig {
      maxOutputTokens env.GEMINI_MAX_TOKENS
      temperature 0.1
    }
  }
}

// Azure OpenAI Client
client<llm> AzureOpenAI {
  provider azure-openai
  options {
    api_key env.AZURE_OPENAI_API_KEY
    base_url env.AZURE_BASE_URL
    api_version env.AZURE_API_VERSION
    temperature 0.1
    allowed_roles ["system", "user"]
    max_tokens env.AZURE_MAX_TOKENS
  }
}

// Azure AI Foundry Client
client<llm> AzureAIFoundry {
  provider "openai-generic"
  options {
    base_url env.AZURE_AIFOUNDRY_BASE_URL
    api_key env.AZURE_AIFOUNDRY_API_KEY
    allowed_roles ["system", "user"]
    max_tokens env.AZURE_AIFOUNDRY_MAX_TOKENS
  }
}

// OpenRouter Client
client<llm> OpenRouter {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    api_key env.OPENROUTER_API_KEY
    model env.OPENROUTER_MODEL_ID
    headers {
      HTTP-Referer env.OPENROUTER_HTTP_REFERER // Optional
      X-Title env.OPENROUTER_X_TITLE // Optional
    }
    allowed_roles ["system", "user"]
    max_tokens env.OPENROUTER_MAX_TOKENS
  }
}

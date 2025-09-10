client<llm> AwsClaudeSonnet4 {
  provider aws-bedrock
  options {
    access_key_id env.AWS_ACCESS_KEY_ID
    secret_access_key env.AWS_SECRET_ACCESS_KEY
    model env.AWS_MODEL_ID
    region env.AWS_REGION
    inference_configuration {
      max_tokens 64000
      temperature 0.1
    }
    allowed_role_metadata ["cache_control"]
  }
}

// Anthropic Client
client<llm> AnthropicClaude {
  provider anthropic
  options {
    api_key env.ANTHROPIC_API_KEY
    model env.ANTHROPIC_MODEL_ID
    max_tokens 64000  
    temperature 0.1
    allowed_role_metadata ["cache_control"]
    headers {
      "anthropic-beta" "prompt-caching-2024-07-31"
    }
  }
}

// OpenAI ChatGPT Client
client<llm> OpenAIChatGPT {
  provider openai
  options {
    api_key env.OPENAI_API_KEY
    model env.OPENAI_MODEL_ID
    temperature 0.1
  }
}

test TestAwsBedrockPackageDiscovery {
  functions [AwsBedrockPackageDiscovery]
  args {
    analysis_query "Analyze the Python packages and dependencies in this project to understand the core functionality and technology stack"
    memory_context "Starting package discovery analysis for a Python CLI project"
    system_info {
      home "/home/user"
      current_dir "/home/user/project"
    }
  }
}

test TestAnthropicClaudePackageDiscovery {
  functions [AnthropicClaudePackageDiscovery]
  args {
    analysis_query "Analyze the Python packages and dependencies in this project to understand the core functionality and technology stack"
    memory_context "Starting package discovery analysis for a Python CLI project"
    system_info {
      home "/home/user"
      current_dir "/home/user/project"
    }
  }
}

test TestAzureOpenAIPackageDiscovery {
  functions [AzureOpenAIPackageDiscovery]
  args {
    analysis_query "Analyze the Python packages and dependencies in this project to understand the core functionality and technology stack"
    memory_context "Starting package discovery analysis for a Python CLI project"
    system_info {
      home "/home/user"
      current_dir "/home/user/project"
    }
  }
}

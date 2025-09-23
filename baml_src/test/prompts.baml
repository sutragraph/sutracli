template_string SutraCliAssistant() #"
You are Sutra CLI Assistant for SutraKit - an intelligent codebase analysis and knowledge management tool that provides AI-powered insights across multi-project ecosystems. SutraKit is a comprehensive orchestrator for AI agents and services focused on complex codebase analysis and management.

Key Features:
- AST-based parsing with Tree-sitter for Python, TypeScript, and JavaScript (full support) with fallback file-based indexing for other languages
- Semantic search using advanced embeddings for code discovery and analysis
- AI-powered Roadmap Agent that processes queries, creates minimal plans across projects, identifies change locations, and refines via feedback
- Cross-indexing service that discovers external connections (APIs, message queues, WebSockets) beyond standard parsing and builds dependency graphs
- Sub-agent orchestration for parallel project updates with dependency handling
- Support for 8 LLM providers: AWS Bedrock, Anthropic Claude, OpenAI, Google AI, Vertex AI, Azure OpenAI, Azure AI Foundry, OpenRouter
- Configuration via ~/.sutra/config/system.config for database paths, storage, embedding models, logging, and LLM settings

Setup: Run 'sutrakit-setup' to initialize environment, Then use 'sutrakit' in project directories for indexing and analysis. Cross-indexing builds ecosystem-wide dependency graphs but should not be run in parallel across projects.

Use Cases: New features, bug fixes, refactoring, repository onboarding in interconnected projects like microservices or full-stack applications.

Provide concise, accurate 1-liner responses about setup, indexing, features, configuration, and troubleshooting.

Answer only questions related to SutraKit. If the question is unrelated to SutraKit, respond with "I'm sorry, I can only assist with questions related to SutraKit."
"#

template_string UserQuestion(question: string) #"
{{ _.role("user") }}
QUESTION: {{question}}
"#

function AwsBedrockSutraCliAssistant(question: string) -> string {
  client AwsBedrock
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}


function AnthropicClaudeSutraCliAssistant(question: string) -> string {
  client AnthropicClaude
  prompt #"
    {{ _.role("system", cache_control={"type": "ephemeral"}) }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

function OpenAIChatGPTSutraCliAssistant(question: string) -> string {
  client OpenAIChatGPT
  prompt #"
    {{ _.role("system") }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

function GoogleGeminiSutraCliAssistant(question: string) -> string {
  client GoogleGemini
  prompt #"
    {{ _.role("system") }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

function GCPVertexAISutraCliAssistant(question: string) -> string {
  client GCPVertexAI
  prompt #"
    {{ _.role("system") }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

function AzureOpenAISutraCliAssistant(question: string) -> string {
  client AzureOpenAI
  prompt #"
    {{ _.role("system") }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

function AzureAIFoundrySutraCliAssistant(question: string) -> string {
  client AzureAIFoundry
  prompt #"
    {{ _.role("system") }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

function OpenRouterSutraCliAssistant(question: string) -> string {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    {{ SutraCliAssistant() }}
    {{ UserQuestion(question) }}
  "#
}

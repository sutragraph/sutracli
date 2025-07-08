
# Sutra Knowledge CLI

An intelligent codebase analysis and knowledge management tool that provides AI-powered insights, semantic search capabilities, and comprehensive project understanding through advanced parsing and embedding technologies.

## Overview

Sutra Knowledge CLI is a powerful command-line application designed to help developers understand, analyze, and interact with codebases using artificial intelligence. It combines semantic search, graph-based analysis, and AI agents to provide deep insights into your projects.

## Key Features

### 🔍 **Intelligent Code Analysis**
- **Single Project Processing**: Analyze individual codebases with detailed parsing and embedding generation
- **Multi-Project Management**: Process and manage multiple projects simultaneously
- **Semantic Search**: Find code patterns and implementations using natural language queries
- **Graph-Based Understanding**: Build knowledge graphs of your codebase for better comprehension

### 🤖 **AI-Powered Assistance**
- **AI Agent Integration**: Interactive AI agent for code understanding and assistance
- **Context-Aware Responses**: Get intelligent answers about your codebase
- **Memory Management**: Persistent conversation context and project knowledge

### 🌐 **Web Integration**
- **Web Search**: Search the web for relevant programming information
- **Web Scraping**: Extract and analyze web content for development insights
- **Authentication**: Secure access to external services and APIs

### 📊 **Project Management**
- **Project Listing**: View and manage all analyzed projects
- **Database Statistics**: Monitor analysis progress and storage metrics
- **Data Management**: Clear and maintain project databases

## Available Commands

| Command | Description |
|---------|-------------|
| `single` | Process a single project for analysis |
| `multi` | Process multiple projects simultaneously |
| `list` | List all analyzed projects |
| `clear` | Clear database data and reset projects |
| `stats` | Display database statistics and metrics |
| `agent` | Start interactive AI agent session |
| `parse` | Parse and analyze code structures |
| `search` | Perform semantic search across codebases |
| `auth` | Manage authentication and API keys |
| `web_search` | Search web for programming resources |
| `web_scrap` | Scrape and analyze web content |

## Quick Start

1. **Installation**: See [install.md](install.md) for detailed installation instructions

2. **Basic Usage**:
   ```bash
   # Analyze a single project
   python main.py single /path/to/your/project

   # Start interactive AI agent
   python main.py agent

   # Search your codebase
   python main.py search "authentication logic"

   # List all projects
   python main.py list
   ```

3. **Configuration**: The tool uses JSON configuration files for project settings and supports various programming languages and frameworks.

## Architecture

Sutra Knowledge CLI is built with a modular architecture:

- **CLI Interface**: User-friendly command-line interface with comprehensive argument parsing
- **Parsing Engine**: Advanced code parsing supporting multiple languages
- **Embedding System**: Semantic embedding generation for intelligent search
- **Graph Processing**: Knowledge graph construction and analysis
- **AI Services**: Integration with language models and AI agents
- **Authentication**: Secure API and service authentication
- **Database Layer**: Efficient storage and retrieval of project data

## Use Cases

- **Code Review**: Understand large codebases quickly
- **Documentation**: Generate insights for better documentation
- **Refactoring**: Identify patterns and relationships for safe refactoring
- **Learning**: Explore unfamiliar codebases with AI assistance
- **Knowledge Management**: Build searchable knowledge bases of your projects

## Requirements

- Python 3.8+
- Required dependencies (see requirements.txt)
- Optional: API keys for enhanced AI features

## Getting Help

- Use `python main.py --help` for command-line help
- Use `python main.py <command> --help` for command-specific help
- Check the documentation in the `docs/` directory (if available)

## Contributing

This project welcomes contributions. Please ensure your code follows the established patterns and includes appropriate tests.

## License

See LICENSE file for details.

---

*Sutra Knowledge CLI - Intelligent codebase understanding through AI-powered analysis*

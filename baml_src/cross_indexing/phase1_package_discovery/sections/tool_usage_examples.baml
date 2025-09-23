template_string ToolUsageExamples_Phase1() #"
====

# TOOL USAGE EXAMPLES

This section provides comprehensive examples of how to use different tools effectively for package discovery and task creation.

1. PROJECT STRUCTURE EXPLORATION (list_files tool)

Example 1: Initial project exploration
  - list_files(path=".", max_depth=2)
  - Purpose: Get overview of project structure and identify package files
  - Look for package configuration files (examples: package.json, requirements.txt)

Example 2: Focused package file search
  - list_files(path=".", pattern="package.json|requirements.txt")
  - Purpose: Find package configuration files in the project
  - Result: List of package files to analyze

2. PACKAGE FILE ANALYSIS (database tool)

Example 1: Node.js package analysis
  - database(query_type="GET_FILE_BY_PATH", file_path="package.json")
  - Purpose: Read package.json to identify connection-related dependencies
  - Look for communication packages (examples: axios, express)

Example 2: Python package analysis
  - database(query_type="GET_FILE_BY_PATH", file_path="requirements.txt")
  - Purpose: Read requirements.txt to identify connection libraries
  - Look for: HTTP client libraries, web frameworks, WebSocket libraries, message queue libraries

Example 3: Java package analysis
  - database(query_type="GET_FILE_BY_PATH", file_path="pom.xml")
  - Purpose: Read pom.xml to identify connection dependencies
  - Look for: HTTP client libraries, web frameworks, WebSocket libraries, message queue libraries

3. TASK CREATION EXAMPLES (sutra memory tasks creation)

Example 1: After finding socket package in requirements.txt
Create task(Add): "Use search_keyword tool with pattern 'import.*socket|from.*socket' and regex=true, case_sensitive=false to find all socket import statements. This networking library is used for low-level network communication between services. Search across all Python files."

Example 2: After finding express package in package.json
Create task(Add): "Use search_keyword tool with pattern 'require.*express|import.*express' and regex=true, case_sensitive=false to find all express import statements. This server framework is used for receiving requests from other services. Search across all JavaScript/TypeScript files."

Example 3: After finding spring-boot package in pom.xml
Create task(Add): "Use search_keyword tool with pattern 'import.*springframework|@SpringBootApplication|@RestController' and regex=true, case_sensitive=false to find all Spring Boot import statements and annotations. This web framework is used for creating REST APIs and handling HTTP requests from other services. Search across all Java files."

4. COMPLETION EXAMPLES (attempt_completion tool)

Example 1: Backend Order Service
attempt_completion(result="Project: OrderService v2.3.1 - Backend microservice for order processing.

Connection Packages Found:
  - HTTP Server: express (REST API endpoints for order management)
  - HTTP Client: axios (calls to payment service, inventory service), node-fetch (external API requests)
  - Message Queue: amqplib (RabbitMQ - publishes order events, receives inventory updates)

Total: 5 connection packages found in package.json.")

5. CRITICAL GUIDELINES

  - Create tasks instantly after analyzing each package file
  - Use specific search patterns with proper regex escaping
  - Include ALL discovered packages in task creation
  - Use specific search patterns with proper regex escaping
  - Create descriptive task names with clear search objectives
"#

template_string ToolGuidelines_Phase1() #"
====

# TOOL GUIDELINES

This section provides specific guidelines for using tools effectively during package discovery.

1. In the `thinking` field, first review your Sutra Memory to understand current package discovery progress, completed discoveries, and previous tool results to avoid redundancy. Then assess what package information you already have and what you need to discover next. also think about what tools you need to use next based on your current package discovery state. Based on package discovery create new tasks for import discovery.

CRITICAL ANALYSIS DECISION PROCESS: In your thinking field, always ask yourself: "Should I track this discovered package information in sutra memory? Will this information be needed for analysis and future reference?" If yes, track it immediately with complete parameter details in history.

ANALYSIS DECISION CRITERIA:
  - Track any communication packages, HTTP clients, server frameworks, WebSocket libraries discovered
  - Track package file analysis results that reveal important connection libraries
  - Track any packages that are related to service-to-service communication
  - Track environment configurations and their resolved values from package files
  - Remember: If information is not tracked in sutra memory, it will not be available for future analysis and reference

Follow the systematic analysis flow and track every single package discovery in Sutra Memory immediately after discovering it with complete parameter details.

First iteration rule:
  - Start with a tool call (list_files) to explore the project structure first

Critical: Update your task list in every iteration based on your thinking:
  - Add new specific tasks discovered during analysis for import pattern discovery
  - Move completed tasks from current to completed status
  - Remove tasks that are no longer relevant

2. TOOL SELECTION STRATEGY

LIST_FILES TOOL
  - Use for initial project structure exploration
  - Look for package configuration files

DATABASE TOOL
  - Use to read package configuration files completely
  - Essential for analyzing dependencies and packages
  - Read entire file content to understand all dependencies
  - Focus on connection-related packages only

2. PACKAGE FILE IDENTIFICATION

Look for package configuration files that define dependencies and packages. Here are common examples by language:

Common Package Files by Language (Examples):
  - JavaScript/Node.js: package.json
  - Python: requirements.txt, setup.py, pyproject.toml, Pipfile, setup.cfg
  - Java: pom.xml, build.gradle, gradle.properties, build.gradle.kts
  - Go: go.mod
  - Ruby: Gemfile, *.gemspec
  - PHP: composer.json
  - C#/.NET: *.csproj, packages.config, Directory.Build.props, Directory.Packages.props
  - Rust: Cargo.toml
  - Swift: Package.swift
  - Kotlin: build.gradle.kts, pom.xml

Note: These are examples of common package configuration files that contain dependency declarations. Different projects may use different build systems, package managers, or custom configuration files. Look for any file that contains dependency declarations or package management information.

3. CONNECTION PACKAGE IDENTIFICATION

Look for packages used for data communication, sending/receiving data, and handling incoming/outgoing connections. Here are some common examples by category:

HTTP Client Libraries (Examples):
  - JavaScript: axios, request, superagent, got, fetch, node-fetch
  - Python: requests, httpx, aiohttp, urllib3, urllib
  - Java: okhttp, retrofit, apache-httpclient, java.net.http
  - Go: resty, fasthttp, net/http
  - C#: HttpClient, RestSharp
  - PHP: Guzzle, cURL

Server Frameworks (Examples):
  - JavaScript: express, koa, fastify, hapi, nest.js
  - Python: flask, django, fastapi, tornado, aiohttp
  - Java: spring-boot, jersey, dropwizard, vertx
  - Go: gin, echo, fiber, gorilla/mux, chi
  - C#: ASP.NET Core, Nancy
  - PHP: Laravel, Symfony, Slim

WebSocket Libraries (Examples):
  - JavaScript: socket.io, ws, websocket, sockjs
  - Python: websockets, socketio, tornado, aiohttp
  - Java: java-websocket, spring-websocket, netty
  - Go: gorilla/websocket, nhooyr/websocket
  - C#: SignalR, WebSocketSharp

Message Queue/Broker Libraries (Examples):
  - Multi-language: rabbitmq, kafka, redis, amqp, mqtt
  - JavaScript: bull, agenda, bee-queue, amqplib
  - Python: celery, rq, kombu, pika
  - Java: spring-kafka, spring-amqp, activemq
  - Go: sarama, amqp091-go

Note: These are examples of common packages. The actual packages in any codebase may vary widely. Look for any package that facilitates communication, data transfer, or network connections between services, or external systems.

4. TASK CREATION GUIDELINES

Task Format Requirements:
  - Include specific search patterns for import discovery
  - Provide clear descriptions of what to search for
  - Add examples of expected import statements
  - Use case_sensitive=false for better coverage

Search Pattern Examples:
  - Node.js: require.*package|import.*package
  - Python: import.*package|from.*package
  - Java: import.*package|@.*package
  - Go: import.*package

5. COMPLETION CRITERIA

When to Use attempt_completion:
  - Your current/pending tasks are completely fulfilled
  - All package files have been analyzed
  - All connection packages have been identified
  - Comprehensive task list has been created

Completion Summary Format:
  - Number of packages discovered
  - Types of connection libraries found
  - Number of tasks created for next analysis
"#

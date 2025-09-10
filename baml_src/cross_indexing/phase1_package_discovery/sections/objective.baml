template_string Objective_Phase1() #"
====

OBJECTIVE

You accomplish focused package discovery to identify all connection-related packages used in the current project. Your goal is to find package configuration files and analyze them to understand which data communication libraries are actually installed and available.

1. Analysis objective:
   Your goal is to discover every single data communication package that is installed and available in the current project. Focus exclusively on packages used to send or receive data between different services, repositories, or applications.

2. Success criteria:
   - Find all package configuration files in the project
   - Identify all data communication packages from these files
   - Create comprehensive task list for subsequent import analysis with complete tool guidance
   - Tasks created here will be executed in subsequent analysis to find import statements
   - Store package information with complete details and search patterns

3. Task creation strategy:
   - Create specific tasks for each data communication package discovered in package files
   - Include exact package names and appropriate search patterns for import analysis
   - Focus on packages that are actually installed and available in the project

4. Data communication package categories to identify:
   - HTTP Client Libraries: Packages that enable making HTTP requests to other services
   - HTTP Server Frameworks: Packages that create HTTP servers to receive requests from other services
   - Real-time Communication Libraries: Packages that enable bidirectional real-time communication
   - Message Queue Libraries: Packages that enable asynchronous message passing between services
   - Custom Communication Wrapper Libraries: User-defined packages that wrap or extend communication functionality

5. Package types to exclude:
   - Database persistence libraries (ORMs, database drivers for data storage)
   - Local file system and storage libraries
   - Utility libraries that don't handle data communication
   - Development and testing dependencies
"#

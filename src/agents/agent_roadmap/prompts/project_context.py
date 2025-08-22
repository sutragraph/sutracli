"""
Project Context Template - Provides a list of relevant projects and their descriptions
"""

PROJECT_CONTEXT = """## Relevant Project Context

Here is a list of projects that are relevant to the current task. Use their descriptions to understand their purpose and how they might be interconnected.

project: datalayer_lburiedflowingv38
path: /home/fishmeister/repos/datalayer
This is a comprehensive Node.js Express-based data service for Neusort, a platform that handles technical interviews and candidate assessments. The service provides REST API endpoints for managing job forms, candidate evaluations, assignment submissions, interview scheduling, admin operations, and various business processes. It includes multiple versioned APIs (v1-v5), supports different user roles (candidates, admins, super admins), handles media servers for interviews, manages assignment pools, processes payments, and integrates with external services through discovery service endpoints. The platform appears to be a complete recruitment and assessment solution with features for creating job forms, conducting technical interviews, managing candidate data, and handling administrative operations.

project: server_xlhiddenflowingv85
path: /home/fishmeister/repos/neusortinterview/server

This project is a comprehensive interview management and assessment platform that facilitates real-time technical interviews. It provides a complete REST API backend with 70+ endpoints for managing job forms, candidate assessments, room operations, and administrative functions. The system includes WebSocket connections for real-time communication with media servers, MediaSoup integration for audio/video streaming, RabbitMQ message queuing for asynchronous processing of assignments and notifications, and integrates with external services like Azure DevOps for repository management, Firebase for authentication, and various data processing services. The platform supports multi-version API endpoints (v1-v5) for backward compatibility and handles everything from candidate onboarding to interview execution and result processing.

"""

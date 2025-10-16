"""
JSON-RPC client for LSP communication.
"""

import json
import threading
import time
from typing import Any, Dict, List, Optional, TextIO

from loguru import logger


class JSONRPCClient:
    """JSON-RPC client for LSP server communication."""

    def __init__(self, stdin: TextIO, stdout: TextIO):
        self.stdin = stdin
        self.stdout = stdout
        self._request_id = 0
        self._lock = threading.Condition()
        self._message_handlers = {}
        self._pending_requests = {}
        self._diagnostics_received = threading.Event()
        self._latest_diagnostics = []
        self._listener_thread = None
        self._running = False

    def _get_next_id(self) -> int:
        """Get next request ID."""
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _send_message(self, message: Dict[str, Any]):
        """Send JSON-RPC message to LSP server."""
        content = json.dumps(message, separators=(",", ":"))
        message_str = f"Content-Length: {len(content)}\r\n\r\n{content}"

        logger.debug(f"Sending message: {message}")
        self.stdin.write(message_str)
        self.stdin.flush()

    def _read_message(self) -> Optional[Dict[str, Any]]:
        """Read JSON-RPC message from LSP server."""
        try:
            # Read headers
            headers = {}
            while True:
                line = self.stdout.readline()
                if not line:
                    logger.debug("Connection closed by server")
                    return None
                line = line.strip()
                logger.debug(f"Read header line: '{line}'")
                if not line:
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()
                    logger.debug(f"Header: {key.strip()} = {value.strip()}")

            # Read content
            content_length = int(headers.get("Content-Length", 0))
            logger.debug(f"Content length: {content_length}")
            if content_length > 0:
                content = self.stdout.read(content_length)
                logger.debug(f"Raw content: {content}")
                parsed_content = json.loads(content)
                logger.debug(f"Received message: {parsed_content}")
                return parsed_content
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return None

    def _message_listener(self):
        """Background thread to listen for messages from LSP server."""
        while True:
            message = self._read_message()
            if message is None:
                logger.debug("Message listener thread exiting")
                break

            method = message.get("method", "")
            msg_id = message.get("id")

            # Handle responses to requests
            if msg_id is not None and method == "":
                with self._lock:
                    if msg_id in self._pending_requests:
                        self._pending_requests[msg_id] = message
                        self._lock.notify()
                continue

            # Handle notifications
            if method == "textDocument/publishDiagnostics":
                diags = message.get("params", {}).get("diagnostics", [])
                with self._lock:
                    # Always update the latest diagnostics
                    self._latest_diagnostics = diags
                    # Always set the event to indicate we've received diagnostics
                    # (even if they're empty)
                    self._diagnostics_received.set()
                    logger.info(f"Received {len(diags)} diagnostic(s)")
                continue

            # Handle other notifications
            if method:
                logger.debug(f"Received notification: {method}")
                continue

            # Handle other requests from server
            if method and msg_id is not None:
                logger.debug(f"Received request: {method}")
                # Default response for unhandled requests
                response = {"jsonrpc": "2.0", "id": msg_id, "result": None}
                self._send_message(response)

    def _start_listener(self):
        """Start the message listener thread."""
        if self._listener_thread is None or not self._listener_thread.is_alive():
            self._running = True
            self._listener_thread = threading.Thread(
                target=self._message_listener, daemon=True
            )
            self._listener_thread.start()
            logger.debug("Started message listener thread")

    def initialize(
        self, workspace_root: str, init_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Initialize LSP server with workspace root and init options."""
        import os

        # Start the message listener
        self._start_listener()

        params = {
            "processId": None,
            "clientInfo": {"name": "lsp-linter", "version": "1.0.0"},
            "capabilities": {
                "textDocument": {"publishDiagnostics": {"versionSupport": True}},
                "workspace": {"configuration": True},
            },
        }

        # Add initialization options if provided
        if init_options:
            params["initializationOptions"] = init_options

        # Add workspace information (always provided)
        workspace_root = os.path.abspath(workspace_root)
        params["rootUri"] = f"file://{workspace_root}"
        params["rootPath"] = workspace_root
        params["workspaceFolders"] = [
            {
                "uri": f"file://{workspace_root}",
                "name": os.path.basename(workspace_root),
            }
        ]

        request_id = self._get_next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": params,
        }

        # Send request and wait for response
        with self._lock:
            self._pending_requests[request_id] = None

        self._send_message(request)
        logger.debug(f"Sent initialize request to LSP server")

        # Wait for response without timeout
        with self._lock:
            self._lock.wait_for(
                lambda: self._pending_requests.get(request_id) is not None
            )
            response = self._pending_requests.pop(request_id, None)

        logger.debug(f"Received response from LSP server: {response}")

        # Send initialized notification
        initialized = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
        self._send_message(initialized)

        return response

    def open_document(self, file_path: str, content: str, language: str):
        """Open document in LSP server."""
        notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": f"file://{file_path}",
                    "languageId": language,
                    "version": 1,
                    "text": content,
                }
            },
        }
        self._send_message(notification)

    def get_diagnostics(
        self,
        file_path: str,
        content: str,
        language: str,
        workspace_config: Dict[str, Any],
    ) -> list:
        """
        Get diagnostics (lint results) for a document.

        This method uses a proper synchronous approach by leveraging the message listener
        thread that handles all incoming messages. It opens the document and waits for
        diagnostics to be published by the LSP server.

        Args:
            file_path: Absolute path to the file
            content: File content to analyze
            language: Language identifier for the LSP server
            workspace_root: Root directory of the workspace
            workspace_config: Optional workspace configuration

        Returns:
            List of diagnostic dictionaries from the LSP server
        """
        # Clear any previous diagnostics
        self._diagnostics_received.clear()
        with self._lock:
            self._latest_diagnostics = []

        # Open document
        self.open_document(file_path, content, language)

        # Send workspace configuration if provided
        if workspace_config:
            config_notification = {
                "jsonrpc": "2.0",
                "method": "workspace/didChangeConfiguration",
                "params": {"settings": workspace_config},
            }
            self._send_message(config_notification)
            logger.debug("Sent workspace configuration")

        # Wait for diagnostics to be received
        # We'll wait for the first batch of diagnostics, even if empty
        # Then check if we have any non-empty diagnostics
        logger.debug("Waiting for diagnostics to be published...")
        self._diagnostics_received.wait()

        # If we received empty diagnostics, wait a bit more for potential updates
        with self._lock:
            if not self._latest_diagnostics:
                logger.debug("Received empty diagnostics, waiting a bit more...")
                # Clear the event to wait again
                self._diagnostics_received.clear()
                # Wait for a short time for any additional diagnostics
                # Use a condition variable with timeout for this case
                self._lock.wait_for(
                    lambda: self._diagnostics_received.is_set(), timeout=2.0
                )

        with self._lock:
            diagnostics = self._latest_diagnostics.copy()
        logger.info(f"Total diagnostics collected: {len(diagnostics)}")
        return diagnostics

    def shutdown(self):
        """Shutdown LSP server."""
        try:
            # Stop the listener thread
            self._running = False
            if self._listener_thread and self._listener_thread.is_alive():
                # Don't wait for thread to join, it might be blocked on I/O
                self._listener_thread.join(timeout=0.1)

            # Send shutdown request
            request = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "shutdown",
                "params": None,
            }
            self._send_message(request)

            # Send exit notification
            exit_notification = {"jsonrpc": "2.0", "method": "exit", "params": None}
            self._send_message(exit_notification)
        except Exception as e:
            logger.debug(f"Error during LSP shutdown: {e}")
            # Don't raise exceptions, just continue

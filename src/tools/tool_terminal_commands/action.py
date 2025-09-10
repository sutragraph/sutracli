import os
import platform
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

from loguru import logger

from models.agent import AgentAction


class DesktopEnvironment:
    """Utility class for detecting desktop environment and available terminals."""

    @staticmethod
    def detect_environment() -> Dict[str, Any]:
        """Detect the current desktop environment."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return {
                "system": "macOS",
                "preferred_terminals": ["Terminal", "iTerm"],
                "supports_foreground": True,
            }
        elif system == "Linux":
            return {
                "system": "Linux",
                "preferred_terminals": ["gnome-terminal", "konsole", "xterm"],
                "supports_foreground": True,
            }
        else:
            return {
                "system": system,
                "preferred_terminals": [],
                "supports_foreground": False,
            }

    @staticmethod
    def get_available_terminals() -> List[str]:
        """Get list of available terminal emulators."""
        env_info = DesktopEnvironment.detect_environment()
        available = []

        for terminal in env_info["preferred_terminals"]:
            if DesktopEnvironment._is_terminal_available(terminal):
                available.append(terminal)

        return available

    @staticmethod
    def _is_terminal_available(terminal: str) -> bool:
        """Check if a terminal emulator is available."""
        if platform.system() == "Darwin":
            # For macOS, check if application exists
            if terminal == "Terminal":
                return os.path.exists("/Applications/Utilities/Terminal.app")
            elif terminal == "iTerm":
                return os.path.exists("/Applications/iTerm.app")
        else:
            # For Linux, check if command exists
            try:
                subprocess.run(["which", terminal], capture_output=True, check=True)
                return True
            except subprocess.CalledProcessError:
                return False
        return False

    @staticmethod
    def supports_foreground_mode() -> bool:
        """Check if the current environment supports foreground terminal mode."""
        env_info = DesktopEnvironment.detect_environment()
        return env_info["supports_foreground"]


class OutputMonitor:
    """Monitor output from a log file with improved error handling."""

    def __init__(self, session_id: str, log_file: str):
        self.session_id = session_id
        self.log_file = log_file
        self.last_position = 0
        self.last_size = 0
        self.last_read_time = time.time()
        self._lock = threading.Lock()
        self._file_handle = None

    def _safe_file_operation(self, operation, retries=3):
        """Safely perform file operations with retries."""
        for attempt in range(retries):
            try:
                return operation()
            except (IOError, OSError) as e:
                if attempt == retries - 1:
                    logger.error(
                        f"File operation failed after {retries} attempts for session {self.session_id}: {e}"
                    )
                    return None
                time.sleep(0.1 * (attempt + 1))  # Progressive backoff

    def _get_file_size(self) -> int:
        """Get current file size safely."""

        def get_size():
            return (
                os.path.getsize(self.log_file) if os.path.exists(self.log_file) else 0
            )

        size = self._safe_file_operation(get_size)
        return size if size is not None else 0

    def has_new_output(self) -> bool:
        """Check if there's new output available without reading it."""
        current_size = self._get_file_size()
        return current_size > self.last_size

    def get_new_output(self) -> str:
        """Get new output since last read."""
        with self._lock:

            def read_operation():
                if not os.path.exists(self.log_file):
                    return ""

                current_size = os.path.getsize(self.log_file)
                if current_size <= self.last_position:
                    return ""

                with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    self.last_position = f.tell()
                    self.last_size = current_size
                    self.last_read_time = time.time()
                    return new_content

            result = self._safe_file_operation(read_operation)
            return result if result is not None else ""

    def get_full_output(self) -> str:
        """Get all output from the beginning."""

        def read_operation():
            if not os.path.exists(self.log_file):
                return ""

            with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        result = self._safe_file_operation(read_operation)
        return result if result is not None else ""

    def wait_for_output(self, timeout: float = 3.0) -> bool:
        """Wait for new output to appear, returns True if output is detected."""
        start_time = time.time()
        initial_size = self._get_file_size()

        # Use smaller sleep intervals for better responsiveness
        while time.time() - start_time < timeout:
            current_size = self._get_file_size()
            if current_size > initial_size:
                # Wait a bit more to ensure we capture complete output
                time.sleep(0.2)
                return True
            time.sleep(0.05)

        return False

    def is_output_active(self, idle_threshold: float = 1.5) -> bool:
        """Check if output is still being actively written using file modification time."""
        current_time = time.time()
        current_size = self._get_file_size()

        # If file size changed recently, consider it active
        if current_size > self.last_size:
            self.last_size = current_size
            self.last_read_time = current_time
            return True

        # Check file modification time as well
        try:
            if os.path.exists(self.log_file):
                mtime = os.path.getmtime(self.log_file)
                if current_time - mtime < idle_threshold:
                    return True
        except OSError:
            pass

        # If no changes within threshold, consider inactive
        return current_time - self.last_read_time < idle_threshold

    def monitor_continuous_output(self, duration: float = 5.0) -> list[str]:
        """Monitor output for a specific duration, useful for long-running processes."""
        start_time = time.time()
        output_lines = []

        while time.time() - start_time < duration:
            new_output = self.get_new_output()
            if new_output:
                lines = new_output.split("\n")
                for line in lines:
                    if line.strip():
                        output_lines.append(line)

            time.sleep(0.2)

        return output_lines

    def detect_command_completion(
        self, command: str, timeout: float = 30.0
    ) -> tuple[bool, list[str]]:
        """
        Detect when a command has completed by monitoring output patterns naturally.
        Returns (completed, output_lines).
        """
        start_time = time.time()
        output_lines = []
        last_output_time = start_time
        min_execution_time = 0.3  # Minimum time for any command

        # Wait for initial output
        if self.wait_for_output(timeout=min(3.0, timeout / 10)):
            last_output_time = time.time()

        while time.time() - start_time < timeout:
            new_output = self.get_new_output()
            if new_output:
                last_output_time = time.time()
                lines = new_output.split("\n")
                for line in lines:
                    if line.strip():
                        output_lines.append(line)

            current_time = time.time()
            time_since_start = current_time - start_time
            time_since_output = current_time - last_output_time

            # Command completion logic:
            # 1. Minimum execution time has passed
            # 2. No new output for reasonable time OR output is inactive
            # 3. Special handling for quick commands (like mkdir, cp)
            if time_since_start >= min_execution_time:
                # For commands that typically don't produce output
                no_output_commands = ["mkdir", "cp", "mv", "rm", "touch", "chmod"]
                is_quiet_command = any(
                    command.strip().startswith(cmd) for cmd in no_output_commands
                )

                if is_quiet_command and time_since_start >= 1.0:
                    return True, output_lines
                elif time_since_output >= 1.5 or not self.is_output_active():
                    return True, output_lines

            time.sleep(0.1)

        # Timeout reached
        return False, output_lines

    def cleanup(self) -> None:
        """Clean up the log file."""

        def cleanup_operation():
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                logger.debug(f"Cleaned up log file: {self.log_file}")

        self._safe_file_operation(cleanup_operation)


class MacOSTerminalHandler:
    """Handler for macOS terminal operations."""

    @staticmethod
    def spawn_terminal(session_id: str, cwd: str, log_file: str) -> Optional[str]:
        """Spawn a new Terminal.app window with logging."""
        try:
            # Create AppleScript to open Terminal with logging
            applescript = f"""
            tell application "Terminal"
                activate
                set newWindow to do script "cd '{cwd}' && exec > >(tee '{log_file}') 2>&1 && exec bash"
                set custom title of newWindow to "Agent Session {session_id}"
                return id of newWindow
            end tell
            """

            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                window_id = result.stdout.strip()
                print(
                    f"Spawned macOS Terminal window {window_id} for session {session_id}"
                )
                return window_id
            else:
                logger.error(f"Failed to spawn macOS Terminal: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error spawning macOS Terminal for session {session_id}: {e}")
            return None

    @staticmethod
    def send_command(window_id: str, command: str) -> bool:
        """Send command to Terminal.app window."""
        try:
            escaped_command = command.replace('"', '\\"').replace("'", "\\'")
            applescript = f"""
            tell application "Terminal"
                do script "{escaped_command}" in window id {window_id}
            end tell
            """

            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0
        except Exception as e:
            logger.error(
                f"Error sending command to macOS Terminal window {window_id}: {e}"
            )
            return False

    @staticmethod
    def close_terminal(window_id: str) -> bool:
        """Close Terminal.app window."""
        try:
            applescript = f"""
            tell application "Terminal"
                close window id {window_id}
            end tell
            """

            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error closing macOS Terminal window {window_id}: {e}")
            return False


class LinuxTerminalHandler:
    """Handler for Linux terminal operations."""

    @staticmethod
    def spawn_terminal(
        session_id: str, cwd: str, log_file: str
    ) -> Optional[subprocess.Popen]:
        """Spawn a new terminal window with tmux session."""
        try:
            tmux_session = f"agent_session_{session_id}"
            available_terminals = DesktopEnvironment.get_available_terminals()

            if not available_terminals:
                logger.error("No terminal emulators available")
                return None

            # Start tmux session with simple bash and logging
            tmux_cmd = [
                "tmux",
                "new-session",
                "-d",
                "-s",
                tmux_session,
                "-c",
                cwd,
                "bash",
            ]

            logger.debug("Starting tmux session: %s", " ".join(tmux_cmd))
            result = subprocess.run(tmux_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to create tmux session: {result.stderr}")
                return None

            # Set up logging in the session
            log_setup_cmd = [
                "tmux",
                "send-keys",
                "-t",
                tmux_session,
                f"exec > >(tee '{log_file}') 2>&1",
                "Enter",
            ]
            subprocess.run(log_setup_cmd, capture_output=True, text=True)

            # Wait for session to be ready
            time.sleep(0.5)

            # Verify session was created
            verify_cmd = ["tmux", "has-session", "-t", tmux_session]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
            if verify_result.returncode != 0:
                logger.error(
                    f"Tmux session {tmux_session} was not created successfully"
                )
                return None

            # Launch terminal with tmux attach and keep it alive
            terminal_cmd = None
            terminal = available_terminals[0]

            if terminal == "gnome-terminal":
                terminal_cmd = [
                    "gnome-terminal",
                    "--title",
                    f"Agent Session {session_id}",
                    "--",
                    "tmux",
                    "attach-session",
                    "-t",
                    tmux_session,
                ]
            elif terminal == "konsole":
                terminal_cmd = [
                    "konsole",
                    "--title",
                    f"Agent Session {session_id}",
                    "-e",
                    "tmux",
                    "attach-session",
                    "-t",
                    tmux_session,
                ]
            elif terminal == "xterm":
                terminal_cmd = [
                    "xterm",
                    "-title",
                    f"Agent Session {session_id}",
                    "-e",
                    "tmux",
                    "attach-session",
                    "-t",
                    tmux_session,
                ]

            if terminal_cmd:
                try:
                    process = subprocess.Popen(
                        terminal_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    # Give the terminal time to start and attach to tmux
                    time.sleep(1.5)
                    print(
                        f"Spawned {terminal} terminal with tmux session {tmux_session}"
                    )
                    return process
                except Exception as e:
                    logger.error(f"Failed to spawn terminal {terminal}: {e}")
                    return None
            else:
                logger.error(f"Unsupported terminal: {terminal}")
                return None

        except Exception as e:
            logger.error(f"Error spawning Linux terminal for session {session_id}: {e}")
            return None

    @staticmethod
    def send_command(session_id: str, command: str) -> bool:
        """Send command to tmux session."""
        try:
            tmux_session = f"agent_session_{session_id}"

            # First check if tmux session exists
            check_result = subprocess.run(
                ["tmux", "has-session", "-t", tmux_session],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if check_result.returncode != 0:
                logger.error(f"Tmux session {tmux_session} does not exist")
                return False

            # Send the command
            result = subprocess.run(
                ["tmux", "send-keys", "-t", tmux_session, command, "Enter"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.error(f"Failed to send command to tmux session: {result.stderr}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error sending command to tmux session {session_id}: {e}")
            return False

    @staticmethod
    def close_terminal(session_id: str) -> bool:
        """Close tmux session."""
        try:
            tmux_session = f"agent_session_{session_id}"

            # Send exit command first to gracefully close
            subprocess.run(
                ["tmux", "send-keys", "-t", tmux_session, "exit", "Enter"],
                capture_output=True,
                text=True,
                timeout=3,
            )

            # Wait a moment for graceful exit
            time.sleep(0.5)

            # Then kill the session
            result = subprocess.run(
                ["tmux", "kill-session", "-t", tmux_session],
                capture_output=True,
                text=True,
            )

            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error closing tmux session {session_id}: {e}")
            return False


class TerminalSession:
    """Represents a foreground terminal session."""

    def __init__(
        self, session_id: str, cwd: Optional[str] = None, description: str = ""
    ):
        self.session_id = session_id
        self.cwd = cwd if cwd is not None else os.getcwd()
        self.description = description or "General terminal session"
        self.created_at = time.time()
        self.last_used = time.time()
        self.has_running_task = False
        self._lock = threading.Lock()

        # Terminal attributes
        self.terminal_process: Optional[subprocess.Popen] = None
        self.terminal_window_id: Optional[str] = None
        self.log_file: Optional[str] = None
        self.output_monitor: Optional[OutputMonitor] = None

    def start(self) -> bool:
        """Start the terminal session."""
        logger.debug(f"Starting foreground terminal session {self.session_id}")
        try:
            # Create log file for output capture
            self.log_file = f"/tmp/terminal_session_{self.session_id}.log"
            logger.debug(f"Creating log file: {self.log_file}")

            # Initialize output monitor
            self.output_monitor = OutputMonitor(self.session_id, self.log_file)

            # Spawn terminal based on platform
            platform_name = platform.system()
            logger.debug(f"Spawning terminal for {platform_name} platform")

            if platform_name == "Darwin":
                result = MacOSTerminalHandler.spawn_terminal(
                    self.session_id, self.cwd, self.log_file
                )
                if isinstance(result, str):
                    self.terminal_window_id = result
                    success = True
                else:
                    success = False
            else:  # Linux
                self.terminal_process = LinuxTerminalHandler.spawn_terminal(
                    self.session_id, self.cwd, self.log_file
                )
                success = self.terminal_process is not None

            if success:
                print(f"Started foreground terminal session {self.session_id}")
                return True
            else:
                logger.error(
                    f"Failed to start foreground terminal session {self.session_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Failed to start foreground terminal session {self.session_id}: {e}"
            )
            return False

    def execute_command(
        self, command: str, timeout: int = 1200, is_long_running: bool = False
    ) -> Dict[str, Any]:
        """Execute a command in the terminal session.

        Args:
            command: The command to execute
            timeout: Maximum time to wait for command completion (seconds)
            is_long_running: If True, the command is expected to run indefinitely
                           (e.g., servers, watchers). The function will wait for
                           startup output and return success without waiting for
                           command completion.

        Returns:
            Dict containing status, output, error, cwd, session_id, exit_code,
            and is_long_running flag.
        """
        with self._lock:
            self.last_used = time.time()

            if is_long_running:
                self.has_running_task = True
                print(
                    f"Detected long-running command in session {self.session_id}: {command[:50]}..."
                )
            else:
                self.has_running_task = True

            try:
                # Ensure session is still alive
                if not self.is_alive():
                    logger.warning(
                        f"Session {self.session_id} appears dead, attempting to restart"
                    )
                    if not self.start():
                        return {
                            "status": "error",
                            "error": "Failed to restart terminal session",
                            "cwd": self.cwd,
                            "session_id": self.session_id,
                        }

                # Send command to terminal without any artificial markers
                success = self._send_command_to_terminal(command)
                if not success:
                    return {
                        "status": "error",
                        "error": "Failed to send command to terminal",
                        "cwd": self.cwd,
                        "session_id": self.session_id,
                    }

                # Use different completion detection for long-running vs regular commands
                if self.output_monitor:
                    if is_long_running:
                        (
                            command_completed,
                            output_lines,
                        ) = self._handle_long_running_command(command, timeout)
                    else:
                        (
                            command_completed,
                            output_lines,
                        ) = self.output_monitor.detect_command_completion(
                            command, timeout
                        )

                    if command_completed:
                        status = "success"
                        error = ""
                        output = "\n".join(output_lines) if output_lines else ""
                    else:
                        if is_long_running:
                            # For long-running commands, timeout doesn't mean failure
                            status = "success"
                            error = ""
                            output = "\n".join(output_lines) if output_lines else ""
                        else:
                            status = "error"
                            error = f"Command timed out after {timeout} seconds"
                            output = "\n".join(output_lines) if output_lines else ""
                else:
                    # Fallback if no output monitor
                    status = "error"
                    error = "No output monitor available"
                    output = ""

                # Update working directory for non-long-running commands
                if not is_long_running:
                    self._send_command_to_terminal("pwd")
                    time.sleep(0.5)
                    if self.output_monitor:
                        pwd_output = self.output_monitor.get_new_output()
                        if pwd_output:
                            lines = pwd_output.strip().split("\n")
                            for line in lines:
                                line = line.strip()
                                # Look for valid directory paths, excluding shell prompts
                                if (
                                    line.startswith("/")
                                    and not "@"
                                    in line  # Exclude prompts like "user@host:/path$"
                                    and not line.endswith("$")
                                    and not line.endswith("#")
                                ):
                                    self.cwd = line
                                    break

                return {
                    "status": status,
                    "output": output,
                    "error": error,
                    "cwd": self.cwd,
                    "session_id": self.session_id,
                    "exit_code": 0 if status == "success" else 1,
                    "is_long_running": is_long_running,
                }

            except Exception as e:
                logger.error(
                    f"Command execution failed in session {self.session_id}: {e}"
                )
                return {
                    "status": "error",
                    "error": f"Command execution failed: {str(e)}",
                    "cwd": self.cwd,
                    "session_id": self.session_id,
                }
            finally:
                # Only clear running task flag for non-long-running commands
                if not is_long_running:
                    self.has_running_task = False

    def _send_command_to_terminal(self, command: str) -> bool:
        """Send command to the terminal."""
        try:
            platform_name = platform.system()

            if platform_name == "Darwin" and self.terminal_window_id:
                return MacOSTerminalHandler.send_command(
                    self.terminal_window_id, command
                )
            elif platform_name != "Darwin":
                return LinuxTerminalHandler.send_command(self.session_id, command)
            else:
                return False
        except Exception as e:
            logger.error(f"Failed to send command to terminal: {e}")
            return False

    def get_new_output(self) -> str:
        """Get new output from the terminal."""
        if self.output_monitor:
            return self.output_monitor.get_new_output()
        return ""

    def get_full_output(self) -> str:
        """Get full output from the terminal."""
        if self.output_monitor:
            return self.output_monitor.get_full_output()
        return ""

    def close(self) -> bool:
        """Close the terminal session."""
        try:
            success = True
            platform_name = platform.system()

            if platform_name == "Darwin" and self.terminal_window_id:
                success = MacOSTerminalHandler.close_terminal(self.terminal_window_id)
            elif platform_name != "Darwin":
                success = LinuxTerminalHandler.close_terminal(self.session_id)

            # Cleanup output monitor
            if self.output_monitor:
                self.output_monitor.cleanup()
                self.output_monitor = None

            # Close terminal process if exists
            if self.terminal_process:
                try:
                    self.terminal_process.terminate()
                except:
                    pass
                self.terminal_process = None

            return success
        except Exception as e:
            logger.error(f"Error closing terminal session {self.session_id}: {e}")
            return False

    def is_alive(self) -> bool:
        """Check if the terminal session is still alive."""
        try:
            platform_name = platform.system()

            if platform_name == "Darwin":
                # For macOS, check if window still exists
                if self.terminal_window_id:
                    applescript = f"""
                    tell application "Terminal"
                        return exists window id {self.terminal_window_id}
                    end tell
                    """
                    result = subprocess.run(
                        ["osascript", "-e", applescript],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    return result.returncode == 0 and "true" in result.stdout.lower()
                return False
            else:
                # For Linux, check if tmux session exists
                tmux_session = f"agent_session_{self.session_id}"
                result = subprocess.run(
                    ["tmux", "has-session", "-t", tmux_session],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                return result.returncode == 0

        except Exception as e:
            logger.debug(f"Error checking if session {self.session_id} is alive: {e}")
            return False

    def is_compatible_for_reuse(self, cwd: str) -> bool:
        """Check if this session can be reused for the given cwd."""
        # Basic compatibility checks
        if self.has_running_task:
            logger.debug(f"Session {self.session_id} has running task, not compatible")
            return False

        if self.cwd != cwd:
            logger.debug(f"Session {self.session_id} cwd mismatch: {self.cwd} != {cwd}")
            return False

        if not self.is_alive():
            logger.debug(f"Session {self.session_id} is not alive, not compatible")
            return False

        # Additional validation: check if we can send a simple command
        try:
            # Use a minimal test that doesn't produce output
            test_success = self._send_command_to_terminal(":")  # : is a no-op command
            if not test_success:
                logger.debug(
                    f"Session {self.session_id} failed command test, not compatible"
                )
                return False
        except Exception as e:
            logger.debug(f"Session {self.session_id} command test exception: {e}")
            return False

        # Check session age - don't reuse very old sessions
        current_time = time.time()
        session_age = current_time - self.created_at
        if session_age > 3600:  # 1 hour
            logger.debug(
                f"Session {self.session_id} too old ({session_age}s), not compatible"
            )
            return False

        logger.debug(f"Session {self.session_id} is compatible for reuse")
        return True

    def _handle_long_running_command(
        self, command: str, timeout: int
    ) -> tuple[bool, list[str]]:
        """Handle long-running commands with special monitoring."""
        if not self.output_monitor:
            return False, []

        # For long-running commands, wait for startup output then return
        output_lines = []

        # Wait for initial startup output
        if self.output_monitor.wait_for_output(timeout=3.0):
            # Give it time to produce startup messages
            time.sleep(2.0)

            # Collect startup output
            startup_output = self.output_monitor.get_new_output()
            if startup_output:
                lines = startup_output.split("\n")
                for line in lines:
                    if line.strip():
                        output_lines.append(line)

            # If we got startup output, consider the process as started
            if startup_output.strip():
                print(
                    f"Long-running process appears to have started successfully in session {self.session_id}"
                )
                return True, output_lines

        # Wait a bit more for any delayed startup messages
        time.sleep(3.0)
        additional_output = self.output_monitor.get_new_output()
        if additional_output:
            lines = additional_output.split("\n")
            for line in lines:
                if line.strip():
                    output_lines.append(line)

        # Consider it successful if we got any output (process started)
        return len(output_lines) > 0, output_lines

    def clear_running_task_flag(self):
        """Manually clear the running task flag (for external management)."""
        with self._lock:
            self.has_running_task = False
            logger.debug(f"Cleared running task flag for session {self.session_id}")


class TerminalSessionManager:
    """Manages terminal sessions with reuse logic."""

    _sessions: Dict[str, TerminalSession] = {}
    _lock = threading.Lock()
    _initialized = False

    @classmethod
    def _ensure_initialized(cls):
        """Ensure the session manager is initialized."""
        if not cls._initialized:
            cls._initialized = True
            logger.debug("Terminal session manager initialized")

    @classmethod
    def create_session(cls, cwd: Optional[str] = None, description: str = "") -> str:
        """Create a new terminal session."""
        cls._ensure_initialized()

        session_id = str(uuid.uuid4())
        logger.debug(
            f"Creating new foreground terminal session {session_id} in {cwd} - {description}"
        )
        session = TerminalSession(session_id, cwd, description)

        with cls._lock:
            cls._sessions[session_id] = session
            logger.debug(f"Added session {session_id} to session manager")

        if session.start():
            print(f"Created foreground terminal session {session_id}")
            # Give the terminal and tmux session time to fully initialize
            time.sleep(2.0)
            return session_id
        else:
            logger.error(f"Failed to start foreground terminal session {session_id}")
            cls._sessions.pop(session_id, None)
            raise Exception("Failed to create terminal session")

    @classmethod
    def get_or_create_session(
        cls, cwd: Optional[str] = None, description: str = ""
    ) -> str:
        """Get an existing compatible session or create a new one."""
        cls._ensure_initialized()

        if cwd is None:
            cwd = os.getcwd()

        # Clean up dead sessions first
        dead_sessions = []
        with cls._lock:
            for session_id, session in cls._sessions.items():
                if not session.is_alive():
                    dead_sessions.append(session_id)
                    logger.debug(f"Marking dead session {session_id} for cleanup")

        # Remove dead sessions
        for session_id in dead_sessions:
            cls.close_session(session_id)

        # Look for compatible existing session
        with cls._lock:
            for session_id, session in cls._sessions.items():
                if session.is_compatible_for_reuse(cwd):
                    print(f"Reusing existing session {session_id} for cwd {cwd}")
                    session.last_used = time.time()
                    session.description = description or session.description
                    return session_id

        # No compatible session found, create new one
        print(f"No compatible session found for cwd {cwd}, creating new session")
        return cls.create_session(cwd, description)

    @classmethod
    def get_session(cls, session_id: str) -> Optional[TerminalSession]:
        """Get a session by ID with validation."""
        with cls._lock:
            session = cls._sessions.get(session_id)
            if session and not session.is_alive():
                logger.warning(
                    f"Session {session_id} found but not alive, removing from registry"
                )
                cls._sessions.pop(session_id, None)
                try:
                    session.close()
                except Exception as e:
                    logger.error(f"Error closing dead session {session_id}: {e}")
                return None
            return session

    @classmethod
    def close_session(cls, session_id: str) -> bool:
        """Close a specific session."""
        with cls._lock:
            session = cls._sessions.pop(session_id, None)
            if session:
                success = session.close()
                print(f"Closed terminal session {session_id}")
                return success
            return False

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """List all active sessions."""
        with cls._lock:
            sessions = []
            for session_id, session in cls._sessions.items():
                sessions.append(
                    {
                        "session_id": session_id,
                        "cwd": session.cwd,
                        "description": session.description,
                        "created_at": session.created_at,
                        "last_used": session.last_used,
                        "has_running_task": session.has_running_task,
                        "is_alive": session.is_alive(),
                    }
                )
            return sessions

    @classmethod
    def close_all_sessions(cls) -> None:
        """Close all sessions."""
        with cls._lock:
            for session in cls._sessions.values():
                try:
                    session.close()
                except Exception as e:
                    logger.error(f"Error closing session {session.session_id}: {e}")
            cls._sessions.clear()
            print("Closed all terminal sessions")

    @classmethod
    def get_session_output(
        cls, session_id: str, output_type: str = "new"
    ) -> Dict[str, Any]:
        """Get output from a session."""
        session = cls.get_session(session_id)
        if not session:
            return {"status": "error", "error": f"Session {session_id} not found"}

        try:
            if output_type == "full":
                output = session.get_full_output()
            else:
                output = session.get_new_output()

            return {
                "status": "success",
                "output": output,
                "session_id": session_id,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get output: {str(e)}",
                "session_id": session_id,
            }

    @classmethod
    def monitor_session_output(
        cls, session_id: str, duration: float = 5.0
    ) -> Dict[str, Any]:
        """Monitor output from a session for a specific duration (useful for long-running processes)."""
        session = cls.get_session(session_id)
        if not session:
            return {"status": "error", "error": f"Session {session_id} not found"}

        try:
            if session.output_monitor:
                output_lines = session.output_monitor.monitor_continuous_output(
                    duration
                )
                return {
                    "status": "success",
                    "output": "\n".join(output_lines) if output_lines else "",
                    "session_id": session_id,
                    "duration": duration,
                    "lines_captured": len(output_lines),
                }
            else:
                return {
                    "status": "error",
                    "error": "No output monitor available for this session",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to monitor session output: {str(e)}",
            }

    @classmethod
    def get_running_processes(cls) -> List[Dict[str, Any]]:
        """Get list of sessions with long-running processes."""
        running_processes = []
        with cls._lock:
            for session_id, session in cls._sessions.items():
                if session.has_running_task and session.is_alive():
                    running_processes.append(
                        {
                            "session_id": session_id,
                            "description": session.description,
                            "cwd": session.cwd,
                            "created_at": session.created_at,
                            "last_used": session.last_used,
                            "uptime": time.time() - session.created_at,
                        }
                    )
        return running_processes

    @classmethod
    def clear_session_running_flag(cls, session_id: str) -> bool:
        """Manually clear the running task flag for a session."""
        session = cls.get_session(session_id)
        if session:
            session.clear_running_task_flag()
            return True
        return False

    @classmethod
    def get_session_stats(cls) -> Dict[str, Any]:
        """Get comprehensive statistics about all sessions."""
        with cls._lock:
            total_sessions = len(cls._sessions)
            alive_sessions = sum(1 for s in cls._sessions.values() if s.is_alive())
            running_tasks = sum(1 for s in cls._sessions.values() if s.has_running_task)

            session_ages = [time.time() - s.created_at for s in cls._sessions.values()]
            avg_age = sum(session_ages) / len(session_ages) if session_ages else 0

            return {
                "total_sessions": total_sessions,
                "alive_sessions": alive_sessions,
                "running_tasks": running_tasks,
                "dead_sessions": total_sessions - alive_sessions,
                "average_session_age": avg_age,
                "oldest_session": max(session_ages) if session_ages else 0,
            }

    @classmethod
    def get_desktop_info(cls) -> Dict[str, Any]:
        """Get desktop environment information."""
        return DesktopEnvironment.detect_environment()


def _handle_create_session(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle create_session action."""
    cwd = parameters.get("cwd", os.getcwd())
    description = parameters.get("description", "")
    logger.debug(f"Creating session with cwd={cwd}, description={description}")
    try:
        session_id = TerminalSessionManager.create_session(cwd, description)
        session = TerminalSessionManager.get_session(session_id)
        if session:
            yield {
                "type": "tool_use",
                "tool_name": "terminal",
                "status": "success",
                "action": "create_session",
                "session_id": session_id,
                "cwd": cwd,
                "message": f"Created new foreground terminal session: {session_id}",
            }
        else:
            yield {
                "type": "tool_use",
                "tool_name": "terminal",
                "status": "error",
                "action": "create_session",
                "error": f"Failed to retrieve created session {session_id}",
            }
    except Exception as e:
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "action": "create_session",
            "error": str(e),
        }


def _handle_close_session(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle close_session action."""
    session_id = parameters.get("session_id")
    logger.debug(f"Closing session {session_id}")

    if not session_id:
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "action": "close_session",
            "error": "session_id parameter is required for close_session",
        }
        return

    success = TerminalSessionManager.close_session(session_id)
    yield {
        "type": "tool_use",
        "tool_name": "terminal",
        "status": "success" if success else "error",
        "action": "close_session",
        "session_id": session_id,
        "message": f"Session {session_id} {'closed' if success else 'not found or failed to close'}",
    }


def _handle_list_sessions(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle list_sessions action."""
    sessions = TerminalSessionManager.list_sessions()
    yield {
        "type": "tool_use",
        "tool_name": "terminal",
        "status": "success",
        "action": "list_sessions",
        "sessions": sessions,
        "message": f"Found {len(sessions)} active sessions",
    }


def _handle_get_output(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle get_output action."""
    session_id = parameters.get("session_id")
    output_type = parameters.get("output_type", "new")

    if not session_id:
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "action": "get_output",
            "error": "session_id parameter is required for get_output",
        }
        return

    result = TerminalSessionManager.get_session_output(session_id, output_type)
    result.update(
        {
            "type": "tool_use",
            "tool_name": "terminal",
            "action": "get_output",
        }
    )
    yield result


def _handle_monitor_output(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle monitor_output action for long-running processes."""
    session_id = parameters.get("session_id")
    duration = float(parameters.get("duration", 5.0))

    if not session_id:
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "action": "monitor_output",
            "error": "session_id parameter is required for monitor_output",
        }
        return

    result = TerminalSessionManager.monitor_session_output(session_id, duration)
    result.update(
        {
            "type": "tool_use",
            "tool_name": "terminal",
            "action": "monitor_output",
        }
    )
    yield result


def _handle_get_running_processes(
    parameters: Dict[str, Any],
) -> Iterator[Dict[str, Any]]:
    """Handle get_running_processes action."""
    running_processes = TerminalSessionManager.get_running_processes()
    yield {
        "type": "tool_use",
        "tool_name": "terminal",
        "status": "success",
        "action": "get_running_processes",
        "running_processes": running_processes,
        "count": len(running_processes),
        "message": f"Found {len(running_processes)} running processes",
    }


def _handle_get_session_stats(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle get_session_stats action."""
    stats = TerminalSessionManager.get_session_stats()
    yield {
        "type": "tool_use",
        "tool_name": "terminal",
        "status": "success",
        "action": "get_session_stats",
        "stats": stats,
        "message": "Retrieved session statistics",
    }


def _handle_get_desktop_info(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle get_desktop_info action."""
    desktop_info = TerminalSessionManager.get_desktop_info()
    yield {
        "type": "tool_use",
        "tool_name": "terminal",
        "status": "success",
        "action": "get_desktop_info",
        "desktop_info": desktop_info,
        "message": "Retrieved desktop environment information",
    }


def _handle_execute_command(parameters: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """Handle execute command action.

    Parameters:
        command (str): The command to execute
        session_id (str, optional): Specific session ID to use
        cwd (str, optional): Working directory for the command
        description (str, optional): Description for session reuse logic
        is_long_running (bool, optional): Whether this is a long-running command
                                        that won't terminate on its own (default: False)
        timeout (int, optional): Maximum time to wait for completion (default: 30)
    """
    command = parameters.get("command")
    if not command:
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "error": "command parameter is required",
        }
        return

    session_id = parameters.get("session_id")
    cwd = parameters.get("cwd", os.getcwd())
    description = parameters.get("description", "")
    is_long_running = parameters.get("is_long_running", False)
    timeout = parameters.get("timeout", 30)

    logger.debug("Executing command: %s", command)

    # Get or create session - use reuse logic if no specific session_id provided
    if not session_id:
        logger.debug("No session_id provided, using session reuse logic")
        try:
            session_id = TerminalSessionManager.get_or_create_session(cwd, description)
            logger.debug(f"Using session {session_id}")
        except Exception as e:
            logger.error(f"Failed to get or create terminal session: {e}")
            yield {
                "type": "tool_use",
                "tool_name": "terminal",
                "status": "error",
                "error": f"Failed to get or create terminal session: {str(e)}",
            }
            return
    else:
        logger.debug(f"Using specified session {session_id}")

    # Get session with validation
    session = TerminalSessionManager.get_session(session_id)
    if not session:
        logger.error(f"Session {session_id} not found")
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "error": f"Session {session_id} not found",
        }
        return

    # Execute command
    logger.debug(f"Executing command in foreground session {session_id}: {command}")
    result = session.execute_command(
        command, timeout=timeout, is_long_running=is_long_running
    )

    # Add session info to result
    result.update(
        {
            "type": "tool_use",
            "tool_name": "terminal",
            "command": command,
            "session_id": session_id,
        }
    )

    yield result


def execute_terminal_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """
    Execute terminal command action with session management and reuse.

    Args:
        action: AgentAction containing terminal command parameters

    Parameters:
        - command: The command to execute
        - cwd: Working directory (optional)
        - session_id: Existing session ID (optional)
        - description: Description of what this session is used for (optional)
        - action_type: Action type - 'execute', 'create_session', 'close_session', 'list_sessions', 'get_output', 'get_desktop_info'

    Yields:
        Dictionary containing the results of the terminal command execution.
    """
    try:
        action_type = action.parameters.get("action_type", "execute")

        action_handlers = {
            "create_session": _handle_create_session,
            "close_session": _handle_close_session,
            "list_sessions": _handle_list_sessions,
            "get_output": _handle_get_output,
            "monitor_output": _handle_monitor_output,
            "get_running_processes": _handle_get_running_processes,
            "get_session_stats": _handle_get_session_stats,
            "get_desktop_info": _handle_get_desktop_info,
            "execute": _handle_execute_command,
        }

        handler = action_handlers.get(action_type)
        if handler:
            yield from handler(action.parameters)
        else:
            yield {
                "type": "tool_use",
                "tool_name": "terminal",
                "status": "error",
                "error": f"Unknown action_type: {action_type}",
            }

    except Exception as e:
        logger.error(f"Terminal action execution failed: {e}")
        yield {
            "type": "tool_use",
            "tool_name": "terminal",
            "status": "error",
            "error": f"Terminal execution failed: {str(e)}",
        }


def cleanup_all_sessions():
    """Cleanup function for all terminal sessions."""
    TerminalSessionManager.close_all_sessions()

"""
Terminal executor for handling terminal command actions with session management.
Supports both background and foreground terminal modes with interactive capabilities.
"""

import subprocess
import os
import uuid
import signal
import threading
import time
import atexit
import weakref
import select
import platform
import shutil
from typing import Iterator, Dict, Any, Optional, ClassVar, List
from loguru import logger
from src.services.agent.agentic_core import AgentAction


class DesktopEnvironment:
    """Utility class for detecting desktop environment and available terminals."""

    @staticmethod
    def detect_environment() -> Dict[str, Any]:
        """Detect the current desktop environment."""
        system = platform.system()

        if system == "Darwin":  # macOS
            return {
                "system": "macOS",
                "desktop": "Aqua",
                "has_gui": True,
                "preferred_terminals": ["Terminal", "iTerm"],
            }
        elif system == "Linux":
            # Check for desktop environment
            desktop_env = os.environ.get("DESKTOP_SESSION", "").lower()
            xdg_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

            has_gui = bool(
                os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
            )

            return {
                "system": "Linux",
                "desktop": desktop_env or xdg_desktop or "unknown",
                "has_gui": has_gui,
                "preferred_terminals": [
                    "gnome-terminal",
                    "konsole",
                    "xfce4-terminal",
                    "xterm",
                ],
            }
        else:
            return {
                "system": system,
                "desktop": "unknown",
                "has_gui": False,
                "preferred_terminals": [],
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
            return shutil.which(terminal) is not None

        return False

    @staticmethod
    def supports_foreground_mode() -> bool:
        """Check if foreground terminal mode is supported."""
        env_info = DesktopEnvironment.detect_environment()
        return (
            env_info["has_gui"]
            and len(DesktopEnvironment.get_available_terminals()) > 0
        )


class OutputMonitor:
    """Monitor terminal output from log files."""

    def __init__(self, session_id: str, log_file: str):
        self.session_id = session_id
        self.log_file = log_file
        self.last_position = 0
        self._lock = threading.Lock()
        self._initial_wait_done = False

    def get_new_output(self) -> str:
        """Get output since last check."""
        with self._lock:
            if not os.path.exists(self.log_file):
                # Small delay on first check to allow log file creation
                if not self._initial_wait_done:
                    time.sleep(0.05)
                    self._initial_wait_done = True
                    if not os.path.exists(self.log_file):
                        return ""
                else:
                    return ""

            try:
                with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self.last_position)
                    new_content = f.read()
                    self.last_position = f.tell()
                    return new_content
            except Exception as e:
                logger.warning(f"Error reading log file {self.log_file}: {e}")
                return ""

    def get_full_output(self) -> str:
        """Get complete session output."""
        with self._lock:
            if not os.path.exists(self.log_file):
                return ""

            try:
                with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Error reading log file {self.log_file}: {e}")
                return ""

    def cleanup(self):
        """Clean up log file."""
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                logger.debug(f"Cleaned up log file: {self.log_file}")
        except Exception as e:
            logger.warning(f"Error cleaning up log file {self.log_file}: {e}")


class MacOSTerminalHandler:
    """Handler for macOS terminal operations."""

    @staticmethod
    def spawn_terminal(
        session_id: str, cwd: str, log_file: str
    ) -> Optional[str]:
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
                logger.info(
                    f"Created Terminal.app window {window_id} for session {session_id}"
                )
                return window_id
            else:
                logger.error(f"Failed to create Terminal.app window: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error spawning macOS terminal: {e}")
            return None

    @staticmethod
    def send_command(window_id: str, command: str) -> bool:
        """Send command to Terminal.app window."""
        try:
            # Escape single quotes in command
            escaped_command = command.replace("'", "\\'")

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
            logger.error(f"Error sending command to Terminal.app: {e}")
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
            logger.error(f"Error closing Terminal.app window: {e}")
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

            terminal_cmd = available_terminals[0]

            # Create tmux session with logging
            tmux_create_cmd = [
                "tmux",
                "new-session",
                "-d",
                "-s",
                tmux_session,
                "-c",
                cwd,
                f"script -f {log_file} -c $SHELL",
            ]

            tmux_result = subprocess.run(
                tmux_create_cmd, capture_output=True, text=True
            )
            if tmux_result.returncode != 0:
                logger.error(f"Failed to create tmux session: {tmux_result.stderr}")
                return None

            # Wait for session to fully initialize and startup message to be written
            time.sleep(0.2)

            # Launch terminal window attached to tmux session
            if terminal_cmd == "gnome-terminal":
                terminal_process = subprocess.Popen(
                    [
                        "gnome-terminal",
                        "--title",
                        f"Agent Session {session_id}",
                        "--",
                        "tmux",
                        "attach-session",
                        "-t",
                        tmux_session,
                    ]
                )
            elif terminal_cmd == "konsole":
                terminal_process = subprocess.Popen(
                    [
                        "konsole",
                        "--title",
                        f"Agent Session {session_id}",
                        "-e",
                        "tmux",
                        "attach-session",
                        "-t",
                        tmux_session,
                    ]
                )
            elif terminal_cmd == "xfce4-terminal":
                terminal_process = subprocess.Popen(
                    [
                        "xfce4-terminal",
                        "--title",
                        f"Agent Session {session_id}",
                        "-e",
                        f"tmux attach-session -t {tmux_session}",
                    ]
                )
            else:  # xterm fallback
                terminal_process = subprocess.Popen(
                    [
                        "xterm",
                        "-title",
                        f"Agent Session {session_id}",
                        "-e",
                        f"tmux attach-session -t {tmux_session}",
                    ]
                )

            logger.info(f"Created {terminal_cmd} window for session {session_id}")
            return terminal_process

        except Exception as e:
            logger.error(f"Error spawning Linux terminal: {e}")
            return None

    @staticmethod
    def send_command(session_id: str, command: str) -> bool:
        """Send command to tmux session."""
        try:
            tmux_session = f"agent_session_{session_id}"

            result = subprocess.run(
                ["tmux", "send-keys", "-t", tmux_session, command, "Enter"],
                capture_output=True,
                text=True,
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error sending command to tmux session: {e}")
            return False

    @staticmethod
    def close_terminal(session_id: str) -> bool:
        """Close tmux session."""
        try:
            tmux_session = f"agent_session_{session_id}"

            result = subprocess.run(
                ["tmux", "kill-session", "-t", tmux_session],
                capture_output=True,
                text=True,
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Error closing tmux session: {e}")
            return False


class TerminalSession:
    """Represents a terminal session with support for both background and foreground modes."""

    def __init__(self, session_id: str, cwd: Optional[str] = None, mode: str = "background", description: str = "", auto_close: bool = False):
        self.session_id = session_id
        self.cwd = cwd if cwd is not None else os.getcwd()
        self.mode = mode  # "background" or "foreground"
        self.description = description or "General terminal session"
        self.auto_close = auto_close  # Whether this session should be automatically cleaned up
        self.created_at = time.time()
        self.last_used = time.time()
        self._lock = threading.Lock()

        # Background mode attributes
        self.process: Optional[subprocess.Popen] = None

        # Foreground mode attributes
        self.terminal_process: Optional[subprocess.Popen] = None
        self.terminal_window_id: Optional[str] = None
        self.log_file: Optional[str] = None
        self.output_monitor: Optional[OutputMonitor] = None

    def start(self) -> bool:
        """Start the terminal session."""
        logger.debug(f"Starting {self.mode} terminal session {self.session_id}")
        if self.mode == "background":
            return self._start_background_terminal()
        else:
            return self._start_foreground_terminal()

    def _start_background_terminal(self) -> bool:
        """Start background terminal (existing implementation)."""
        try:
            if self.process and self.process.poll() is None:
                logger.debug(f"Background terminal session {self.session_id} already running")
                return True  # Already running

            # Clean up any dead process first
            if self.process and self.process.poll() is not None:
                logger.debug(f"Cleaning up dead process for session {self.session_id}")
                try:
                    TerminalSessionManager._unregister_process_for_cleanup(self.process)
                except:
                    pass
                self.process = None

            # Determine shell command
            shell_cmd = self._get_shell_command()
            logger.debug(f"Starting background terminal with command: {shell_cmd}")

            # Create process with better error handling
            self.process = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd,
                start_new_session=True,
                bufsize=1,  # Line buffered
            )

            # Give process a moment to start
            time.sleep(0.1)

            # Check if process started successfully
            if self.process.poll() is not None:
                logger.error(f"Process for session {self.session_id} died immediately after start")
                return False

            # Register this process for cleanup on main process exit
            TerminalSessionManager._register_process_for_cleanup(self.process)

            # Change to the desired directory with error handling
            if self.cwd != os.getcwd() and self.process and self.process.stdin:
                try:
                    cd_command = f'cd "{self.cwd}"\n'
                    self.process.stdin.write(cd_command)
                    self.process.stdin.flush()

                    # Give the cd command time to execute
                    time.sleep(0.1)

                    # Check if process is still alive after cd
                    if self.process.poll() is not None:
                        logger.error(f"Process died after cd command in session {self.session_id}")
                        return False
                except (BrokenPipeError, OSError) as e:
                    logger.error(f"Failed to change directory in session {self.session_id}: {e}")
                    return False

            logger.info(
                f"Started background terminal session {self.session_id} with PID {self.process.pid}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to start background terminal session {self.session_id}: {e}"
            )
            if self.process:
                try:
                    self.process.terminate()
                except:
                    pass
                self.process = None
            return False

    def _start_foreground_terminal(self) -> bool:
        """Start foreground terminal session."""
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
                logger.info(f"Started foreground terminal session {self.session_id}")
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

    def _get_shell_command(self):
        """Get the appropriate shell command with robust error handling."""
        # Try to use bash first, fallback to sh, then other common shells
        shells_to_try = [
            ("bash", ["which", "bash"]),
            ("sh", ["/bin/sh"]),
            ("zsh", ["which", "zsh"]),
            ("fish", ["which", "fish"]),
        ]

        for shell_name, shell_cmd in shells_to_try:
            try:
                if shell_name == "sh":
                    # For sh, just check if the file exists
                    if os.path.exists("/bin/sh") and os.access("/bin/sh", os.X_OK):
                        logger.debug(f"Using shell: {shell_cmd[0]}")
                        return shell_cmd
                else:
                    # For other shells, use which command
                    result = subprocess.run(
                        shell_cmd, capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        shell_path = result.stdout.strip()
                        if shell_path and os.path.exists(shell_path) and os.access(shell_path, os.X_OK):
                            logger.debug(f"Using shell: {shell_path}")
                            return [shell_path]
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
                logger.debug(f"Failed to check for {shell_name}: {e}")
                continue

        # Ultimate fallback - try common shell locations
        fallback_shells = ["/bin/bash", "/usr/bin/bash", "/bin/sh", "/usr/bin/sh"]
        for shell_path in fallback_shells:
            if os.path.exists(shell_path) and os.access(shell_path, os.X_OK):
                logger.warning(f"Using fallback shell: {shell_path}")
                return [shell_path]

        # If all else fails, raise an error
        raise RuntimeError("No suitable shell found on this system")

    def execute_command(self, command: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute a command in the terminal session."""
        if self.mode == "foreground":
            return self._execute_command_foreground(command, timeout)
        else:
            return self._execute_command_background(command, timeout)

    def _execute_command_background(
        self, command: str, timeout: int = 10
    ) -> Dict[str, Any]:
        """Execute command in background terminal (existing implementation)."""
        # Check if process exists and is still alive
        if not self.process:
            logger.debug(f"No process for session {self.session_id}, starting new one")
            if not self.start():
                return {"status": "error", "error": "Failed to start terminal session"}

        # Double-check process is still alive after potential restart
        if not self.process or self.process.poll() is not None:
            logger.debug(f"Process for session {self.session_id} died, restarting")
            if not self.start():
                return {"status": "error", "error": "Failed to restart terminal session"}

        try:
            with self._lock:
                self.last_used = time.time()

                # Verify process is still alive before sending command
                if self.process and self.process.poll() is not None:
                    logger.error(f"Process died before command execution in session {self.session_id}")
                    return {"status": "error", "error": "Terminal process died unexpectedly"}
                elif not self.process:
                    logger.error(f"No process available for session {self.session_id}")
                    return {"status": "error", "error": "No terminal process available"}

                # Add command delimiter to help parse output
                delimiter = f"__CMD_END_{uuid.uuid4().hex[:8]}__"
                full_command = (
                    f"{command}; echo '__EXIT_CODE__'$? >&2; echo '{delimiter}' >&2\n"
                )

                logger.debug(f"Sending command to process {self.process.pid}: {repr(command)}")

                # Send command with error handling
                try:
                    if self.process and self.process.stdin:
                        self.process.stdin.write(full_command)
                        self.process.stdin.flush()
                    else:
                        return {"status": "error", "error": "Process stdin not available"}
                except (BrokenPipeError, OSError) as e:
                    logger.error(f"Failed to send command to process {self.process.pid if self.process else 'unknown'}: {e}")
                    return {"status": "error", "error": f"Failed to send command: {str(e)}"}

                # Read output with timeout
                output_lines = []
                error_lines = []
                start_time = time.time()
                exit_code = 0
                command_finished = False

                while time.time() - start_time < timeout and not command_finished:
                    # Check if process is still alive
                    if not self.process or self.process.poll() is not None:
                        logger.warning(f"Process {self.process.pid if self.process else 'unknown'} died during command execution")
                        break

                    # Read stderr to check for delimiter and exit code
                    try:
                        if self.process and self.process.stderr:
                            ready, _, _ = select.select([self.process.stderr], [], [], 0.1)
                            if ready:
                                line = self.process.stderr.readline()
                                if line:
                                    line_str = line.rstrip()
                                    if delimiter in line_str:
                                        # Command finished
                                        command_finished = True
                                        break
                                    elif "__EXIT_CODE__" in line_str:
                                        # Extract exit code
                                        try:
                                            exit_code = int(
                                                line_str.replace("__EXIT_CODE__", "")
                                            )
                                        except ValueError:
                                            exit_code = 1
                                    else:
                                        error_lines.append(line_str)
                        else:
                            continue
                    except (OSError, ValueError) as e:
                        logger.debug(f"Error reading stderr: {e}")
                        break

                    # Read stdout
                    try:
                        if self.process and self.process.stdout:
                            ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                            if ready:
                                line = self.process.stdout.readline()
                                if line:
                                    output_lines.append(line.rstrip())
                        else:
                            continue
                    except (OSError, ValueError) as e:
                        logger.debug(f"Error reading stdout: {e}")
                        break

                output = "\n".join(output_lines) if output_lines else ""
                error = "\n".join(error_lines) if error_lines else ""

                # Only get current working directory if process is still alive
                if self.process and self.process.poll() is None:
                    try:
                        if self.process.stdin:
                            self.process.stdin.write("pwd\n")
                            self.process.stdin.flush()
                            time.sleep(0.1)  # Small delay to ensure command executes

                        if self.process.stdout:
                            ready, _, _ = select.select([self.process.stdout], [], [], 1)
                            if ready:
                                cwd_line = self.process.stdout.readline()
                                if cwd_line:
                                    self.cwd = cwd_line.strip()
                    except (BrokenPipeError, OSError):
                        # Process died, keep current cwd
                        pass

                # Determine status based on exit code and process state
                if not command_finished and time.time() - start_time >= timeout:
                    status = "error"
                    error = f"Command timed out after {timeout} seconds"
                elif self.process and self.process.poll() is not None and not command_finished:
                    status = "error"
                    error = "Terminal process died during command execution"
                else:
                    status = "success" if exit_code == 0 else "error"

                result = {
                    "status": status,
                    "output": output,
                    "error": error,
                    "cwd": self.cwd,
                    "session_id": self.session_id,
                    "pid": self.process.pid if self.process else None,
                    "mode": self.mode,
                    "exit_code": exit_code,
                }

                if status == "error" and not error:
                    result["error"] = f"Command failed with exit code {exit_code}"

                return result

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"Command timed out after {timeout} seconds: {command}",
                "cwd": self.cwd,
                "session_id": self.session_id,
                "mode": self.mode,
                "exit_code": 124,
            }
        except Exception as e:
            logger.error(f"Command execution failed in session {self.session_id}: {e}")
            return {"status": "error", "error": f"Command execution failed: {str(e)}"}

    def _execute_command_foreground(
        self, command: str, timeout: int = 10
    ) -> Dict[str, Any]:
        """Execute command in the actual foreground terminal window."""
        try:
            with self._lock:
                self.last_used = time.time()

                logger.debug(f"Sending command to terminal window: {repr(command)}")

                # Get initial log file size to track new output
                initial_log_size = 0
                if self.log_file and os.path.exists(self.log_file):
                    try:
                        initial_log_size = os.path.getsize(self.log_file)
                    except OSError:
                        initial_log_size = 0

                # Send command to terminal window with small delay to ensure proper ordering
                time.sleep(0.1)  # Ensure session startup is complete
                command_sent = self._send_command_to_terminal(command)
                if not command_sent:
                    logger.warning(f"Failed to send command to terminal window, falling back to direct execution")
                    return self._execute_directly_fallback(command, timeout)

                logger.debug(f"Command sent to terminal window successfully")

                # Monitor output from log file with improved detection
                start_time = time.time()
                output_lines = []
                command_likely_completed = False
                no_output_commands = ['mv', 'cp', 'rm', 'mkdir', 'chmod', 'chown', 'touch', 'ln']
                is_no_output_cmd = any(command.strip().startswith(cmd) for cmd in no_output_commands)

                # Use shorter timeout for commands that typically don't produce output
                effective_timeout = min(3, timeout) if is_no_output_cmd else timeout

                while time.time() - start_time < effective_timeout:
                    if self.output_monitor:
                        new_output = self.output_monitor.get_new_output()
                        if new_output:
                            output_lines.extend(new_output.split('\n'))
                            command_likely_completed = True

                    # Also check log file directly
                    if self.log_file and os.path.exists(self.log_file):
                        try:
                            current_size = os.path.getsize(self.log_file)
                            if current_size > initial_log_size:
                                with open(self.log_file, 'r') as f:
                                    f.seek(initial_log_size)
                                    new_content = f.read()
                                    if new_content:
                                        output_lines.extend(new_content.split('\n'))
                                        initial_log_size = current_size
                                        command_likely_completed = True

                                        # If we got substantial output, we can break early
                                        if len(new_content.strip()) > 10:
                                            break
                        except (OSError, IOError):
                            pass

                    # For no-output commands, break early if we've waited a reasonable time
                    if is_no_output_cmd and time.time() - start_time > 1:
                        command_likely_completed = True
                        break

                    time.sleep(0.1)  # Small delay to avoid busy waiting

                # Clean up output
                output = '\n'.join(line for line in output_lines if line.strip())

                # Determine status based on command type and output
                if command_likely_completed or is_no_output_cmd:
                    status = "success"
                    exit_code = 0
                elif time.time() - start_time >= effective_timeout:
                    # Command might have timed out, but for some commands this is OK
                    if is_no_output_cmd:
                        status = "success"
                        exit_code = 0
                    else:
                        status = "error"
                        exit_code = 124
                        if not output:
                            output = f"Command may have timed out after {effective_timeout}s"
                else:
                    status = "success"
                    exit_code = 0

                logger.debug(f"Command completed in terminal window (status: {status}, timeout: {effective_timeout}s)")
                logger.debug(f"Output: {repr(output[:200])}")

                response = {
                    "status": status,
                    "output": output,
                    "error": "",
                    "cwd": self.cwd,
                    "session_id": self.session_id,
                    "mode": self.mode,
                    "exit_code": exit_code,
                }

                # Add debug info for commands with no output
                if not output and status == "success":
                    if is_no_output_cmd:
                        response["output"] = f"Command '{command.split()[0]}' completed successfully (no output expected)"
                    else:
                        response["output"] = "Command completed successfully"

                return response

        except Exception as e:
            logger.error(f"Command execution failed in session {self.session_id}: {e}")
            # Fallback to direct subprocess execution
            try:
                logger.debug(f"Exception occurred, trying direct subprocess as fallback")
                return self._execute_directly_fallback(command, timeout)
            except Exception as fallback_e:
                logger.error(f"Fallback also failed: {fallback_e}")
                return {
                    "status": "error",
                    "error": f"Command execution failed: {str(e)}",
                    "cwd": self.cwd,
                    "session_id": self.session_id,
                    "mode": self.mode,
                    "exit_code": 1,
                }

    def _execute_directly_fallback(self, command: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute command directly using subprocess as fallback."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Get clean output and error
            output = result.stdout
            error = result.stderr
            exit_code = result.returncode

            logger.debug(f"Fallback command completed with exit code: {exit_code}")
            logger.debug(f"Fallback output: {repr(output[:200])}")

            status = "success" if exit_code == 0 else "error"

            response = {
                "status": status,
                "output": output,
                "error": error,
                "cwd": self.cwd,
                "session_id": self.session_id,
                "mode": self.mode,
                "exit_code": exit_code,
            }

            if status == "error" and not error:
                response["error"] = f"Command failed with exit code {exit_code}"

            return response

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"Command timed out after {timeout} seconds",
                "cwd": self.cwd,
                "session_id": self.session_id,
                "mode": self.mode,
                "exit_code": 124,
            }



    def _send_command_to_terminal(self, command: str) -> bool:
        """Send command to foreground terminal."""
        if platform.system() == "Darwin":
            if self.terminal_window_id:
                return MacOSTerminalHandler.send_command(self.terminal_window_id, command)
            else:
                logger.error(f"No terminal window ID available for session {self.session_id}")
                return False
        else:
            return LinuxTerminalHandler.send_command(self.session_id, command)



    def get_new_output(self) -> str:
        """Get new output from foreground terminal."""
        if self.mode == "foreground" and self.output_monitor:
            return self.output_monitor.get_new_output()
        return ""

    def get_full_output(self) -> str:
        """Get full output from foreground terminal."""
        if self.mode == "foreground" and self.output_monitor:
            return self.output_monitor.get_full_output()
        return ""

    def close(self) -> bool:
        """Close the terminal session."""
        try:
            # Clean up output monitor first
            if hasattr(self, 'output_monitor') and self.output_monitor:
                self.output_monitor.cleanup()

            with self._lock:
                if self.mode == "foreground":
                    return self._close_foreground_terminal()
                else:
                    return self._close_background_terminal()
        except Exception as e:
            logger.error(f"Failed to close terminal session {self.session_id}: {e}")
            return False

    def _close_background_terminal(self) -> bool:
        """Close background terminal (existing implementation)."""
        if self.process and self.process.poll() is None:
            # Unregister from cleanup tracking
            TerminalSessionManager._unregister_process_for_cleanup(self.process)

            # Send exit command
            try:
                if self.process.stdin:
                    exit_command = "exit\n"
                    self.process.stdin.write(exit_command)
                    self.process.stdin.flush()
                else:
                    # If stdin is not available, skip graceful shutdown
                    self._force_kill_process()
                    return True

                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill the process
                    self._force_kill_process()
            except (BrokenPipeError, OSError):
                # If stdin is closed, just kill the process
                if self.process.poll() is None:
                    self._force_kill_process()

        logger.info(f"Closed background terminal session {self.session_id}")
        return True

    def _close_foreground_terminal(self) -> bool:
        """Close foreground terminal."""
        success = False

        # Close terminal window
        if platform.system() == "Darwin":
            if self.terminal_window_id:
                success = MacOSTerminalHandler.close_terminal(self.terminal_window_id)
        else:
            success = LinuxTerminalHandler.close_terminal(self.session_id)
            if self.terminal_process:
                try:
                    self.terminal_process.terminate()
                    self.terminal_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.terminal_process.kill()
                except:
                    pass

        # Cleanup output monitor
        if self.output_monitor:
            self.output_monitor.cleanup()

        logger.info(f"Closed foreground terminal session {self.session_id}")
        return success

    def _force_kill_process(self):
        """Force kill the process using process group."""
        if not self.process:
            logger.debug("No process to kill")
            return

        try:
            # Try to kill process group
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                # Fallback to killing just the process
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        except Exception as e:
            logger.debug(f"Error in force kill: {e}")

    def is_alive(self) -> bool:
        """Check if the terminal session is still alive."""
        try:
            if self.mode == "background":
                # Check both process existence and poll status
                if self.process is None:
                    return False

                poll_result = self.process.poll()
                if poll_result is not None:
                    logger.debug(f"Background process for session {self.session_id} exited with code {poll_result}")
                    return False

                # Additional check: try to get process info
                try:
                    # Check if we can still send signals to the process
                    os.kill(self.process.pid, 0)
                    return True
                except (OSError, ProcessLookupError):
                    logger.debug(f"Process {self.process.pid if self.process else 'unknown'} for session {self.session_id} is not accessible")
                    return False

            else:  # foreground mode
                # For foreground terminals, check multiple indicators
                if self.terminal_process:
                    if self.terminal_process.poll() is None:
                        return True

                # For foreground sessions using direct subprocess execution,
                # check if the session has been used recently
                current_time = time.time()
                time_since_last_use = current_time - self.last_used

                # Consider session alive if used within last 30 minutes
                if time_since_last_use < 1800:  # 30 minutes
                    return True

                # Also check log file if available (for terminal-based sessions)
                if self.log_file and os.path.exists(self.log_file):
                    try:
                        # Check if the log file has been modified recently
                        mtime = os.path.getmtime(self.log_file)
                        # More lenient timeout - 10 minutes instead of 5
                        return time.time() - mtime < 600
                    except OSError:
                        return False

                return False

        except Exception as e:
            logger.error(f"Error checking if session {self.session_id} is alive: {e}")
            return False


class TerminalSessionManager:
    """Static class for managing multiple terminal sessions."""

    # Class variables for session management
    _sessions: ClassVar[Dict[str, TerminalSession]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _cleanup_thread: ClassVar[Optional[threading.Thread]] = None
    _initialized: ClassVar[bool] = False

    # Global process tracking for cleanup
    _tracked_processes: ClassVar[weakref.WeakSet] = weakref.WeakSet()
    _process_lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def _ensure_initialized(cls):
        """Ensure the session manager is initialized."""
        if not cls._initialized:
            cls._setup_signal_handlers()
            cls._start_cleanup_thread()
            cls._initialized = True

    @classmethod
    def _setup_signal_handlers(cls):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, cleaning up terminal sessions...")
            cls._cleanup_all_processes()
            cls.close_all_sessions()
            # Re-raise the signal to allow normal shutdown
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

        # Register atexit handler as fallback
        atexit.register(cls._cleanup_all_processes)

    @classmethod
    def _register_process_for_cleanup(cls, process: subprocess.Popen):
        """Register a process for cleanup when main process exits."""
        with cls._process_lock:
            cls._tracked_processes.add(process)

    @classmethod
    def _unregister_process_for_cleanup(cls, process: subprocess.Popen):
        """Unregister a process from cleanup tracking."""
        with cls._process_lock:
            cls._tracked_processes.discard(process)

    @classmethod
    def _cleanup_all_processes(cls):
        """Cleanup function called on main process exit."""
        logger.info("Cleaning up all terminal processes...")

        with cls._process_lock:
            processes = list(cls._tracked_processes)

        for process in processes:
            try:
                if hasattr(process, 'poll') and process.poll() is None:  # Process still running
                    logger.debug(f"Terminating process {getattr(process, 'pid', 'unknown')}")

                    # Try graceful shutdown first, but be more patient
                    try:
                        if hasattr(process, 'stdin') and process.stdin and not process.stdin.closed:
                            process.stdin.write("exit\n")
                            process.stdin.flush()
                            if hasattr(process, 'wait'):
                                process.wait(timeout=3)  # Give more time
                        else:
                            # stdin is closed, skip graceful shutdown
                            raise subprocess.TimeoutExpired(["dummy"], 0)
                    except (BrokenPipeError, OSError):
                        # Process stdin is broken, skip graceful shutdown
                        pass
                    except subprocess.TimeoutExpired:
                        # Graceful shutdown failed, try SIGTERM
                        try:
                            # Try to terminate the process group first
                            try:
                                if hasattr(process, 'pid') and process.pid:
                                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                            except (ProcessLookupError, OSError):
                                # If process group doesn't exist, just terminate the process
                                if hasattr(process, 'terminate'):
                                    process.terminate()

                            # Wait for termination
                            if hasattr(process, 'wait'):
                                process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            # SIGTERM failed, use SIGKILL
                            logger.warning(f"Process {getattr(process, 'pid', 'unknown')} didn't respond to SIGTERM, using SIGKILL")
                            try:
                                if hasattr(process, 'pid') and process.pid:
                                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            except (ProcessLookupError, OSError):
                                if hasattr(process, 'kill'):
                                    process.kill()
                        except (ProcessLookupError, OSError):
                            # Process already dead
                            pass
                else:
                    logger.debug(f"Process {getattr(process, 'pid', 'unknown')} already terminated")
            except Exception as e:
                logger.error(f"Error cleaning up process {getattr(process, 'pid', 'unknown')}: {e}")

    @classmethod
    def _start_cleanup_thread(cls):
        """Start background cleanup thread."""

        def cleanup_worker():
            while True:
                try:
                    cls._cleanup_old_sessions()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")

        cls._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cls._cleanup_thread.start()

    @classmethod
    def _cleanup_old_sessions(cls):
        """Clean up old or dead sessions."""
        current_time = time.time()
        sessions_to_remove = []

        with cls._lock:
            for session_id, session in cls._sessions.items():
                # Only clean up sessions that have auto_close enabled
                if session.auto_close:
                    # Remove sessions older than 1 hour or dead processes
                    if current_time - session.last_used > 3600 or not session.is_alive():
                        sessions_to_remove.append(session_id)
                        logger.debug(f"Marking session {session_id} for cleanup (auto_close=True)")

        for session_id in sessions_to_remove:
            cls.close_session(session_id)

        # Clean up orphaned log files
        cls._cleanup_old_log_files()

    @classmethod
    def create_session(cls, cwd: Optional[str] = None, mode: str = "auto", description: str = "", auto_close: bool = False) -> str:
        """Create a new terminal session."""
        cls._ensure_initialized()

        # Auto-detect mode
        if mode == "auto":
            # Force background mode if auto_close=True to avoid creating terminal windows that immediately close
            if auto_close:
                mode = "background"
                logger.info("Forcing background mode because close_after=True - avoiding terminal window that would immediately close")
            else:
                mode = (
                    "foreground"
                    if DesktopEnvironment.supports_foreground_mode()
                    else "background"
                )

        # Override explicit foreground mode if auto_close=True for better UX
        if mode == "foreground" and auto_close:
            mode = "background"
            logger.warning(f"Overriding explicit foreground mode to background because close_after=True - terminal window would close immediately, providing poor UX")

        session_id = str(uuid.uuid4())
        logger.debug(f"Creating new {mode} terminal session {session_id} in {cwd} - {description} (auto_close={auto_close})")
        session = TerminalSession(session_id, cwd, mode, description, auto_close)

        with cls._lock:
            cls._sessions[session_id] = session
            logger.debug(f"Added session {session_id} to session manager")

        if session.start():
            logger.info(f"Created {mode} terminal session {session_id}")
            return session_id
        else:
            logger.error(f"Failed to start {mode} terminal session {session_id}")
            cls._sessions.pop(session_id, None)
            raise Exception(f"Failed to create terminal session")

    @classmethod
    def _cleanup_old_log_files(cls):
        """Clean up old terminal session log files from /tmp/."""
        try:
            import glob
            import time

            # Find all terminal session log files
            log_pattern = "/tmp/terminal_session_*.log"
            log_files = glob.glob(log_pattern)

            current_time = time.time()
            cleaned_count = 0

            for log_file in log_files:
                try:
                    # Get file modification time
                    mtime = os.path.getmtime(log_file)
                    # Remove files older than 2 hours
                    if current_time - mtime > 7200:
                        os.remove(log_file)
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    logger.debug(f"Failed to clean up log file {log_file}: {e}")

            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} old log files")

        except Exception as e:
            logger.debug(f"Error during log file cleanup: {e}")

    @classmethod
    def get_session(cls, session_id: str) -> Optional[TerminalSession]:
        """Get a terminal session by ID."""
        cls._ensure_initialized()

        with cls._lock:
            return cls._sessions.get(session_id)

    @classmethod
    def close_session(cls, session_id: str) -> bool:
        """Close a terminal session."""
        cls._ensure_initialized()

        with cls._lock:
            session = cls._sessions.pop(session_id, None)

        if session:
            return session.close()
        return False

    @classmethod
    def list_sessions(cls) -> Dict[str, Dict[str, Any]]:
        """List all active sessions."""
        cls._ensure_initialized()

        with cls._lock:
            return {
                session_id: {
                    "session_id": session_id,
                    "cwd": session.cwd,
                    "mode": session.mode,
                    "description": session.description,
                    "pid": session.process.pid if session.process else None,
                    "terminal_pid": (
                        session.terminal_process.pid
                        if session.terminal_process
                        else None
                    ),
                    "window_id": (
                        session.terminal_window_id
                        if hasattr(session, "terminal_window_id")
                        else None
                    ),
                    "created_at": session.created_at,
                    "last_used": session.last_used,
                    "is_alive": session.is_alive(),
                }
                for session_id, session in cls._sessions.items()
            }

    @classmethod
    def close_all_sessions(cls):
        """Close all terminal sessions."""
        cls._ensure_initialized()

        with cls._lock:
            session_ids = list(cls._sessions.keys())

        for session_id in session_ids:
            cls.close_session(session_id)

    @classmethod
    def cleanup_all_sessions(cls):
        """Cleanup function to close all sessions (call on application shutdown)."""
        cls.close_all_sessions()

    @classmethod
    def get_session_output(
        cls, session_id: str, output_type: str = "new"
    ) -> Dict[str, Any]:
        """Get output from a foreground terminal session."""
        cls._ensure_initialized()

        session = cls.get_session(session_id)
        if not session:
            return {"status": "error", "error": f"Session {session_id} not found"}

        if session.mode != "foreground":
            return {
                "status": "error",
                "error": "Output retrieval only supported for foreground sessions",
            }

        try:
            if output_type == "new":
                output = session.get_new_output()
            elif output_type == "full":
                output = session.get_full_output()
            else:
                return {
                    "status": "error",
                    "error": "Invalid output_type. Use 'new' or 'full'",
                }

            return {
                "status": "success",
                "session_id": session_id,
                "output": output,
                "output_type": output_type,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @classmethod
    def get_desktop_info(cls) -> Dict[str, Any]:
        """Get desktop environment information."""
        return {
            "desktop_environment": DesktopEnvironment.detect_environment(),
            "available_terminals": DesktopEnvironment.get_available_terminals(),
            "supports_foreground": DesktopEnvironment.supports_foreground_mode(),
        }


def execute_terminal_action(action: AgentAction) -> Iterator[Dict[str, Any]]:
    """
    Execute terminal command action with session management.
    Enhanced version supporting both background and foreground modes.

    Args:
        action: AgentAction containing terminal command parameters

    Parameters:
        - command: The command to execute
        - cwd: Working directory (optional)
        - session_id: Existing session ID (optional)
        - mode: Terminal mode - "auto", "background", "foreground" (optional)
        - description: Description of what this session is used for (optional)
        - close_after: Close session automatically after command execution (optional, default: false)
        - action_type: Action type - 'execute', 'create_session', 'close_session', 'list_sessions', 'get_output', 'get_desktop_info'

    Yields:
        Dictionary containing the results of the terminal command execution.
    """
    try:
        parameters = action.parameters or {}
        action_type = parameters.get("action_type", "execute")

        if action_type == "create_session":
            cwd = parameters.get("cwd", os.getcwd())
            mode = parameters.get("mode", "auto")
            description = parameters.get("description", "")
            logger.debug(f"Creating session with cwd={cwd}, mode={mode}, description={description}")
            try:
                session_id = TerminalSessionManager.create_session(cwd, mode, description, auto_close=False)
                session = TerminalSessionManager.get_session(session_id)
                if session:
                    yield {
                        "type": "tool_use",
                        "tool_name": "terminal",
                        "status": "success",
                        "action": "create_session",
                        "session_id": session_id,
                        "cwd": cwd,
                        "mode": session.mode,
                        "message": f"Created new {session.mode} terminal session: {session_id}",
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
            return

        elif action_type == "close_session":
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
            return

        elif action_type == "list_sessions":
            sessions = TerminalSessionManager.list_sessions()
            yield {
                "type": "tool_use",
                "tool_name": "terminal",
                "status": "success",
                "action": "list_sessions",
                "sessions": sessions,
                "message": f"Found {len(sessions)} active sessions",
            }
            return

        elif action_type == "get_output":
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
            return

        elif action_type == "get_desktop_info":
            desktop_info = TerminalSessionManager.get_desktop_info()
            yield {
                "type": "tool_use",
                "tool_name": "terminal",
                "status": "success",
                "action": "get_desktop_info",
                "desktop_info": desktop_info,
                "message": "Retrieved desktop environment information",
            }
            return

        elif action_type == "execute":
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
            mode = parameters.get("mode", "auto")
            description = parameters.get("description", "")
            close_after = parameters.get("close_after", False)

            logger.debug(f"Executing command: {command}, close_after: {close_after}")

            # Create new session if none provided
            if not session_id:
                logger.debug(f"No session_id provided, creating new session")
                try:
                    session_id = TerminalSessionManager.create_session(cwd, mode, description, auto_close=close_after)
                    logger.debug(f"Auto-created session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to create terminal session: {e}")
                    yield {
                        "type": "tool_use",
                        "tool_name": "terminal",
                        "status": "error",
                        "error": f"Failed to create terminal session: {str(e)}",
                    }
                    return
            else:
                logger.debug(f"Using existing session {session_id}")

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

            # Additional validation - check if session is functional
            if not session.is_alive():
                logger.warning(f"Session {session_id} appears to be inactive, attempting to restart if needed")
                # Don't immediately fail - let the execute_command method handle the restart

            # Execute command
            logger.debug(
                f"Executing command in {session.mode} session {session_id}: {command}"
            )
            result = session.execute_command(command)

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

            # Close session automatically if close_after is True
            if close_after and session_id:
                logger.debug(f"Auto-closing session {session_id} after command execution")
                try:
                    # Validate session exists before attempting to close
                    if TerminalSessionManager.get_session(session_id):
                        success = TerminalSessionManager.close_session(session_id)
                        if success:
                            logger.debug(f"Successfully closed session {session_id}")
                        else:
                            logger.warning(f"Failed to close session {session_id} - session may not exist")
                    else:
                        logger.debug(f"Session {session_id} already closed or doesn't exist")
                except Exception as e:
                    logger.error(f"Failed to auto-close session {session_id}: {e}")
                    # Don't let close_after failures affect the main result
                    # The command execution was successful, closing is just cleanup

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
    """Cleanup function to close all sessions (call on application shutdown)."""
    TerminalSessionManager.cleanup_all_sessions()

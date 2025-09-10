"""Integrated session management for agent conversations, state persistence, and task tracking."""

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from config import config
from services.agent.memory_management.memory_formatter import clean_sutra_memory_content


class SessionManager:
    """Manages agent session persistence and Sutra memory."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.sessions_dir = Path(config.storage.sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.session_file = self.sessions_dir / f"{self.session_id}.json"

        # Session data - replaced conversation_history with sutra_memory
        self.sutra_memory: str = ""
        self.session_data: List[Dict[str, Any]] = []
        self.problem_context: str = ""
        self.current_query_id: Optional[str] = None
        self.task_progress_history: List[str] = []  # Track progress across iterations

        # Load existing session if it exists
        self._load_session()

    def _load_session(self) -> None:
        """Load session data from file if it exists."""
        try:
            if self.session_file.exists():
                with open(self.session_file, "r") as f:
                    session_data = json.load(f)

                # Load sutra_memory
                self.sutra_memory = session_data.get("sutra_memory", "")

                self.problem_context = session_data.get("problem_context", "")
                self.session_data = session_data.get("session_data", [])
                self.current_query_id = session_data.get("current_query_id")
                self.task_progress_history = session_data.get(
                    "task_progress_history", []
                )

                print(f"🧠 Loaded session {self.session_id} with Sutra memory")
            else:
                print(f"🆕 Created new session {self.session_id}")
        except Exception as e:
            logger.warning(f"Failed to load session {self.session_id}: {e}")
            # Continue with empty session data

    def save_session(self) -> None:
        """Save current session data to file."""
        try:
            session_data = {
                "session_id": self.session_id,
                "sutra_memory": self.sutra_memory,
                "problem_context": self.problem_context,
                "session_data": self.session_data,
                "current_query_id": self.current_query_id,
                "task_progress_history": self.task_progress_history,
                "last_updated": time.time(),
            }

            with open(self.session_file, "w") as f:
                json.dump(session_data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save session {self.session_id}: {e}")

    def start_new_query(self, query: str) -> str:
        """Start a new query within the existing session and return the query ID."""
        query_id = str(uuid.uuid4())
        self.current_query_id = query_id

        # Note: We don't use conversation history anymore
        # The LLM manages its own memory through sutra_memory updates

        # Save session after setting query
        self.save_session()

        return query_id

    def set_problem_context(self, context: str) -> None:
        """Set the problem context."""
        self.problem_context = context
        self.save_session()

    def update_sutra_memory(self, memory_content: str) -> None:
        """Update the Sutra memory with new content."""
        # Clean the memory content to remove escaped characters
        self.sutra_memory = clean_sutra_memory_content(memory_content)
        self.save_session()

    def get_sutra_memory(self) -> str:
        """Get the current Sutra memory content (already cleaned)."""
        return self.sutra_memory

    def get_task_progress_history(self) -> str:
        """Get formatted task progress history for prompt inclusion."""
        if not self.task_progress_history:
            return ""

        history_lines = []
        for i, progress in enumerate(self.task_progress_history, 1):
            history_lines.append(f"Iteration {i}: {progress}")

        return "\n".join(history_lines)

    def clear_session(self) -> None:
        """Clear Sutra memory and reset session."""
        self.sutra_memory = ""
        self.session_data = []
        self.problem_context = ""
        self.current_query_id = None
        self.task_progress_history = []

        # Remove session file
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            logger.debug(f"🗑️  Cleared session {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to clear session file: {e}")

    def clear_session_data_for_current_query(self) -> None:
        """Clear session data (action records) for the current query to reset tool state."""
        if not self.current_query_id:
            return

        # Remove all session data entries for the current query
        original_count = len(self.session_data)
        self.session_data = [
            item
            for item in self.session_data
            if item.get("query_id") != self.current_query_id
        ]

        cleared_count = original_count - len(self.session_data)
        if cleared_count > 0:
            logger.debug(
                f"🗑️  Cleared {cleared_count} session data entries for query {self.current_query_id}"
            )
            self.save_session()

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current session with Sutra memory."""
        return {
            "session_id": self.session_id,
            "sutra_memory_length": len(self.sutra_memory),
            "sutra_memory_preview": (
                self.sutra_memory[:200] + "..."
                if len(self.sutra_memory) > 200
                else self.sutra_memory
            ),
            "problem_context": self.problem_context,
            "current_query_id": self.current_query_id,
            "session_file": str(self.session_file),
        }

    @classmethod
    def get_or_create_session(
        cls, session_id: Optional[str] = None
    ) -> "SessionManager":
        """Get existing session or create new one."""
        if session_id:
            # Check if session exists
            session_file = Path(config.storage.sessions_dir) / f"{session_id}.json"
            if session_file.exists():
                return cls(session_id=session_id)

        # Create new session
        return cls()

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        """List all available sessions."""
        sessions_dir = Path(config.storage.sessions_dir)
        if not sessions_dir.exists():
            return []

        sessions = []
        for session_file in sessions_dir.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    session_data = json.load(f)

                sessions.append(
                    {
                        "session_id": session_data.get("session_id"),
                        "last_updated": session_data.get("last_updated"),
                        "memory_length": len(session_data.get("sutra_memory", "")),
                        "problem_context": (
                            session_data.get("problem_context", "")[:100] + "..."
                            if len(session_data.get("problem_context", "")) > 100
                            else session_data.get("problem_context", "")
                        ),
                        "current_query_id": session_data.get("current_query_id"),
                        "file_path": str(session_file),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to read session file {session_file}: {e}")

        return sorted(sessions, key=lambda x: x.get("last_updated") or 0, reverse=True)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save session before closing."""
        self.save_session()

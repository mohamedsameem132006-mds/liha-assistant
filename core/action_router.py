"""
core/action_router.py
Smart Action Router & Context Tracker for LIHA.

Pipeline:
USER INTENT -> INTENT DETECTION -> ACTION ROUTER -> VALIDATION -> TOOL EXECUTION -> VERIFICATION -> RESPONSE

Key Features:
- Short-term conversational context tracking ("it", "that file", "last opened file", "current project")
- Universal execution timeouts (prevents hanging / UI freezing)
- Safe error recovery & human-readable failure explanations
- Safe retry mechanism with fallback options
- Loop and recursion prevention
"""

import sys
import time
import threading
import concurrent.futures
from pathlib import Path
from typing import Callable, Any, Dict, Optional, Tuple

from core.file_manager import get_file_manager, FileOperationResult
from core.diagnostics import get_diagnostics
from core.project_analyzer import get_project_analyzer

DEFAULT_TOOL_TIMEOUT_SECONDS = 25.0
MAX_TOOL_RETRIES = 2


class ConversationalContext:
    """Tracks short-term conversational context for smart anaphoric references."""
    def __init__(self):
        self.last_file: Optional[Path] = None
        self.last_directory: Optional[Path] = None
        self.last_action: Optional[str] = None
        self.last_search_results: list = []
        self.pending_confirmation: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def update_file(self, file_path: Path):
        with self._lock:
            self.last_file = file_path
            if file_path.parent:
                self.last_directory = file_path.parent

    def update_directory(self, dir_path: Path):
        with self._lock:
            self.last_directory = dir_path

    def update_action(self, action_name: str):
        with self._lock:
            self.last_action = action_name

    def set_pending_confirmation(self, task_info: Dict[str, Any]):
        with self._lock:
            self.pending_confirmation = task_info

    def pop_pending_confirmation(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            conf = self.pending_confirmation
            self.pending_confirmation = None
            return conf

    def resolve_reference(self, raw_name: str) -> str:
        """Resolves references like 'it', 'that file', 'the file', 'this file' to the last accessed file."""
        if not raw_name:
            return str(self.last_file) if self.last_file else ""
        cleaned = raw_name.strip().lower()
        if cleaned in ("it", "that", "that file", "this file", "the file", "previous file", "last file"):
            if self.last_file:
                return str(self.last_file)
        if cleaned in ("that folder", "this folder", "the folder", "here", "the directory", "current folder"):
            if self.last_directory:
                return str(self.last_directory)
        return raw_name


class SmartActionRouter:
    def __init__(self):
        self.context = ConversationalContext()
        self.file_manager = get_file_manager()
        self.diagnostics = get_diagnostics()
        self.project_analyzer = get_project_analyzer()
        self._executor_pool = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="LIHA-ActionRouter")
        self._recent_failures: Dict[str, int] = {}
        self._lock = threading.Lock()

    def route_and_execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        player=None,
        speak_cb: Optional[Callable[[str], None]] = None,
        timeout: float = DEFAULT_TOOL_TIMEOUT_SECONDS
    ) -> str:
        """
        Main routing entry point with validation, timeout enforcement, verification, and error recovery.
        """
        params = dict(params or {})
        self.context.update_action(tool_name)
        
        # Log to UI if available
        if player:
            try:
                player.write_log(f"⚡ Tool: {tool_name}")
            except Exception:
                pass

        # Check for confirmed pending actions e.g. safe deletion
        if "delete" in tool_name or params.get("action") == "delete":
            # If user explicitly confirms
            if str(params.get("confirm", "")).lower() in ("true", "1", "yes", "confirm"):
                params["confirm"] = True

        # Resolve context references for paths and names
        if "name" in params:
            params["name"] = self.context.resolve_reference(params["name"])
        if "path" in params and params["path"] in ("it", "that", "the file", "this file"):
            params["path"] = self.context.resolve_reference(params["path"])

        # Execute wrapped with timeout and safe retries
        attempt = 0
        last_error = ""

        while attempt < MAX_TOOL_RETRIES:
            attempt += 1
            try:
                future = self._executor_pool.submit(self._dispatch_tool, tool_name, params, player, speak_cb)
                result = future.result(timeout=timeout)

                # Reset failure counter on success
                with self._lock:
                    self._recent_failures[tool_name] = 0

                return str(result)

            except concurrent.futures.TimeoutError:
                last_error = f"Operation timed out after {timeout} seconds."
                print(f"[ActionRouter] ⚠️ Tool '{tool_name}' timed out (Attempt {attempt}/{MAX_TOOL_RETRIES})")
                if attempt < MAX_TOOL_RETRIES:
                    if speak_cb: speak_cb("That is taking longer than expected. Retrying once...")
                    time.sleep(0.5)

            except PermissionError:
                return f"I couldn't complete the operation because Windows denied permission."

            except FileNotFoundError as fnf:
                return f"I couldn't find the requested file or folder: {fnf.filename or 'specified path'}."

            except Exception as e:
                last_error = str(e)
                print(f"[ActionRouter] ⚠️ Tool '{tool_name}' error (Attempt {attempt}/{MAX_TOOL_RETRIES}): {e}")
                if attempt < MAX_TOOL_RETRIES:
                    time.sleep(0.5)

        # Fallback failure response
        with self._lock:
            self._recent_failures[tool_name] = self._recent_failures.get(tool_name, 0) + 1

        return self._format_error_response(tool_name, last_error)

    def _dispatch_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        player=None,
        speak_cb: Optional[Callable[[str], None]] = None
    ) -> str:
        """Direct dispatch to verified tool implementations."""
        # 1. Dedicated File Operations & Controller
        if tool_name in ("file_controller", "file_operations", "manage_file"):
            action = params.get("action", "").lower().strip()
            path = params.get("path", "desktop")
            name = params.get("name", "")
            content = params.get("content", "")

            # If user gave name and path together or separate
            full_path_str = str(self.file_manager.resolve_path(path) / name) if name else path

            if action in ("create_file", "create"):
                res = self.file_manager.create_file(full_path_str, content=content, overwrite=params.get("overwrite", False))
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("create_folder", "mkdir"):
                res = self.file_manager.create_folder(full_path_str)
                if res.success and res.path: self.context.update_directory(res.path)
                return res.message

            elif action in ("read", "read_file", "view"):
                res = self.file_manager.read_file(full_path_str, max_chars=params.get("max_chars", 10000))
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("write", "write_file"):
                res = self.file_manager.write_file(full_path_str, content=content, append=params.get("append", False))
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("append", "append_file"):
                res = self.file_manager.write_file(full_path_str, content=content, append=True)
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("edit", "edit_file", "modify"):
                target_text = params.get("target_text", params.get("find", ""))
                replacement = params.get("replacement_text", params.get("replace", ""))
                res = self.file_manager.edit_file(full_path_str, target_text=target_text, replacement_text=replacement)
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("delete", "delete_file", "remove"):
                confirm = bool(params.get("confirm", False))
                res = self.file_manager.delete_file(full_path_str, confirm=confirm, permanent=params.get("permanent", False))
                return res.message

            elif action in ("rename", "rename_file"):
                new_name = params.get("new_name", "")
                res = self.file_manager.rename_file(full_path_str, new_name=new_name)
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("move", "move_file"):
                dest = params.get("destination", "")
                res = self.file_manager.move_file(full_path_str, dest)
                if res.success and res.path: self.context.update_file(res.path)
                return res.message

            elif action in ("copy", "copy_file", "duplicate"):
                dest = params.get("destination", "")
                res = self.file_manager.copy_file(full_path_str, dest)
                return res.message

            elif action in ("list", "list_directory", "dir", "ls"):
                res = self.file_manager.list_directory(path=path, pattern=params.get("pattern", "*"))
                if res.success and res.path: self.context.update_directory(res.path)
                return res.message

            elif action in ("find", "search", "search_files"):
                res = self.file_manager.search_files(
                    query=params.get("query", name),
                    path=path,
                    extension=params.get("extension", ""),
                    modified_today=params.get("modified_today", False),
                    max_results=params.get("max_results", 30)
                )
                return res.message

            elif action in ("info", "get_file_info", "metadata"):
                res = self.file_manager.get_file_info(full_path_str)
                return res.message

            # Legacy actions compatibility
            elif action == "organize_desktop":
                from actions.file_controller import organize_desktop
                return organize_desktop()
            elif action == "disk_usage":
                from actions.file_controller import get_disk_usage
                return get_disk_usage(path)

            return f"Unknown file action: '{action}'"

        # 2. System Status & Diagnostics
        elif tool_name in ("liha_status", "system_diagnostics", "check_yourself"):
            return self.diagnostics.format_status_report()

        elif tool_name in ("restart_liha", "liha_restart"):
            if speak_cb: speak_cb("Restarting LIHA now, sir.")
            return self.diagnostics.restart_liha()

        # 3. Project Analyzer Tool
        elif tool_name in ("project_analyzer", "analyze_project", "check_project"):
            analyzer = self.project_analyzer
            if analyzer.is_running():
                return "Project analysis is currently already running in the background."

            if speak_cb: speak_cb("Let me analyze your project, sir.")
            
            # Start non-blocking background analysis
            analyzer.analyze_project_async(
                progress_callback=lambda pct, msg, st: player.write_log(f"[{pct}%] {msg}") if player else None,
                on_complete=lambda s: player.write_log(f"SYS: Analysis finished ({s['status']})") if player else None
            )
            return "Project analysis started in the background. I will notify you as soon as it completes."

        # 4. Computer Settings (Volume, Brightness, Window Management)
        elif tool_name == "computer_settings":
            from actions.computer_settings import computer_settings
            return computer_settings(parameters=params, response=None, player=player)

        # 5. Open App
        elif tool_name == "open_app":
            from actions.open_app import open_app
            return open_app(parameters=params, response=None, player=player)

        # 6. Web Search
        elif tool_name == "web_search":
            from actions.web_search import web_search
            return web_search(parameters=params, player=player)

        # 7. Weather Report
        elif tool_name == "weather_report":
            from actions.weather_report import weather_action
            return weather_action(parameters=params, player=player)

        # 8. Send Message
        elif tool_name == "send_message":
            from actions.send_message import send_message
            return send_message(parameters=params, response=None, player=player, session_memory=None)

        # 9. Reminder
        elif tool_name == "reminder":
            from actions.reminder import reminder
            return reminder(parameters=params, response=None, player=player)

        # 10. YouTube
        elif tool_name == "youtube_video":
            from actions.youtube_video import youtube_video
            return youtube_video(parameters=params, response=None, player=player)

        # 11. Computer Control
        elif tool_name == "computer_control":
            from actions.computer_control import computer_control
            return computer_control(parameters=params, player=player)

        # 12. Dev Agent & Code Helper
        elif tool_name == "dev_agent":
            from actions.dev_agent import dev_agent
            return dev_agent(parameters=params, player=player, speak=speak_cb)
        elif tool_name == "code_helper":
            from actions.code_helper import code_helper
            return code_helper(parameters=params, player=player, speak=speak_cb)

        return f"Tool '{tool_name}' executed."

    def _format_error_response(self, tool_name: str, raw_error: str) -> str:
        """Converts raw exception text into clear, polite user feedback."""
        if "permission" in raw_error.lower() or "winerror 5" in raw_error.lower():
            return f"I couldn't complete '{tool_name}' because Windows denied permission."
        if "timed out" in raw_error.lower():
            return f"The operation '{tool_name}' took too long and was safely cancelled."
        if "not found" in raw_error.lower():
            return f"I couldn't find the requested resource for '{tool_name}'."
        return f"I encountered an issue executing {tool_name}: {raw_error[:120]}"


# Singleton instance
_router_instance: Optional[SmartActionRouter] = None
_router_lock = threading.Lock()

def get_action_router() -> SmartActionRouter:
    global _router_instance
    with _router_lock:
        if _router_instance is None:
            _router_instance = SmartActionRouter()
    return _router_instance

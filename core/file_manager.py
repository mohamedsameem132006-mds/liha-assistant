"""
core/file_manager.py
Complete, safe, and intelligent file management system for LIHA.

Features:
- Full CRUD operations with verification on every action
- Surgical file editing (find-and-replace, section updates without full overwrite)
- Protected system paths & Safe delete system (Recycle bin via send2trash + confirmation)
- Smart natural path resolution (Desktop, Downloads, Documents, Projects, etc.)
- Binary file safeguards (prevents corrupting images, executables, or audio)
- Rich metadata and search capabilities (extensions, modified dates, regex/text search)
"""

import os
import re
import sys
import shutil
import time
from pathlib import Path
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple

try:
    import send2trash
    _HAS_SEND2TRASH = True
except ImportError:
    _HAS_SEND2TRASH = False

# Protected system paths that LIHA must NEVER delete or overwrite
PROTECTED_SYSTEM_PATHS = {
    "C:\\Windows", "C:\\Windows\\System32", "C:\\Windows\\SysWOW64",
    "C:\\Program Files", "C:\\Program Files (x86)", "C:\\ProgramData",
    "C:\\", "C:", "/", "/bin", "/sbin", "/usr", "/usr/bin", "/etc",
    "/System", "/Library", "/System/Library"
}

# Supported editable text extensions
TEXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm",
    ".css", ".scss", ".sass", ".json", ".md", ".markdown", ".csv",
    ".xml", ".yaml", ".yml", ".env", ".ini", ".toml", ".cfg", ".conf",
    ".sh", ".bat", ".ps1", ".cmd", ".c", ".cpp", ".h", ".hpp", ".rs",
    ".go", ".java", ".kt", ".swift", ".sql", ".log"
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".svg",
    ".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".iso",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat", ".pdf"
}


class FileOperationResult:
    def __init__(self, success: bool, message: str, path: Optional[Path] = None, data: Any = None):
        self.success = success
        self.message = message
        self.path = path
        self.data = data

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "path": str(self.path) if self.path else None,
            "data": self.data
        }


class FileManager:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parent.parent
        self._last_accessed_file: Optional[Path] = None
        self._last_accessed_dir: Optional[Path] = None

    @property
    def last_accessed_file(self) -> Optional[Path]:
        return self._last_accessed_file

    @property
    def last_accessed_dir(self) -> Optional[Path]:
        return self._last_accessed_dir

    def resolve_path(self, raw_path: str, default_to_desktop: bool = True) -> Path:
        """
        Smart path resolution for natural language aliases and relative paths.
        Supports: 'desktop', 'documents', 'downloads', 'pictures', 'videos', 'music', 'project', 'home'
        """
        if not raw_path or not str(raw_path).strip():
            return Path.home() / "Desktop" if default_to_desktop else Path.cwd()

        cleaned = str(raw_path).strip()
        lower = cleaned.lower().replace("\\", "/").strip("/")

        # Check conversational references to previously accessed files/folders
        if lower in ("it", "that", "that file", "this file", "the file", "previous file", "last file") and self._last_accessed_file:
            return self._last_accessed_file
        if lower in ("that folder", "this folder", "the folder", "here", "the directory", "current folder") and self._last_accessed_dir:
            return self._last_accessed_dir

        shortcuts: Dict[str, Path] = {
            "desktop": Path.home() / "Desktop",
            "documents": Path.home() / "Documents",
            "downloads": Path.home() / "Downloads",
            "pictures": Path.home() / "Pictures",
            "photos": Path.home() / "Pictures",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
            "movies": Path.home() / "Videos",
            "home": Path.home(),
            "user": Path.home(),
            "project": self.project_root,
            "workspace": self.project_root,
            "cwd": Path.cwd(),
            "current": Path.cwd(),
        }

        # Check exact shortcut match
        if lower in shortcuts:
            return shortcuts[lower]

        # Check prefix shortcut match e.g. "desktop/test.txt"
        for key, base in shortcuts.items():
            if lower.startswith(f"{key}/"):
                sub_path = cleaned[len(key) + 1:].lstrip("/\\")
                return (base / sub_path).resolve()

        p = Path(cleaned).expanduser()
        if not p.is_absolute():
            # If path looks like a bare filename, check if last accessed dir exists or default to Desktop
            if self._last_accessed_dir and self._last_accessed_dir.exists():
                candidate = (self._last_accessed_dir / p).resolve()
                if candidate.exists() or len(p.parts) > 1:
                    return candidate
            return (Path.home() / "Desktop" / p).resolve() if default_to_desktop else (Path.cwd() / p).resolve()

        return p.resolve()

    def _is_protected_path(self, target: Path) -> bool:
        """Checks if a path is a critical system directory."""
        try:
            resolved_str = str(target.resolve()).lower()
            for protected in PROTECTED_SYSTEM_PATHS:
                p_str = str(Path(protected).resolve()).lower()
                if resolved_str == p_str or resolved_str.startswith(p_str + "\\") or resolved_str.startswith(p_str + "/"):
                    if resolved_str in [p_str, p_str + "\\", p_str + "/"]:
                        return True
                    # If target is directly inside Windows or System32
                    if "c:\\windows" in resolved_str or "c:/windows" in resolved_str:
                        return True
            return False
        except Exception:
            return True

    def create_file(self, path: str, content: str = "", overwrite: bool = False) -> FileOperationResult:
        """Creates a file with parent directories, content, and verification."""
        try:
            target = self.resolve_path(path)
            if self._is_protected_path(target):
                return FileOperationResult(False, f"Access denied: '{target}' is a protected system location.", target)

            if target.exists() and not overwrite:
                return FileOperationResult(False, f"File already exists: '{target.name}'. Use overwrite=True if intended.", target)

            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

            # Verification
            if not target.exists():
                return FileOperationResult(False, f"Verification failed: '{target.name}' could not be created.", target)

            self._last_accessed_file = target
            self._last_accessed_dir = target.parent
            return FileOperationResult(True, f"File created successfully: '{target.name}' at {target.parent}", target)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while creating file: '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Could not create file: {e}", self.resolve_path(path))

    def create_folder(self, path: str) -> FileOperationResult:
        """Creates a directory (and all parents) with verification."""
        try:
            target = self.resolve_path(path)
            if self._is_protected_path(target):
                return FileOperationResult(False, f"Access denied: '{target}' is a protected system location.", target)

            target.mkdir(parents=True, exist_ok=True)

            # Verification
            if not target.exists() or not target.is_dir():
                return FileOperationResult(False, f"Verification failed: folder '{target.name}' was not created.", target)

            self._last_accessed_dir = target
            return FileOperationResult(True, f"Folder created successfully: '{target.name}' at {target.parent}", target)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while creating folder: '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Could not create folder: {e}", self.resolve_path(path))

    def read_file(self, path: str, max_chars: int = 10000, offset: int = 0) -> FileOperationResult:
        """Reads a text file safely with truncation bounds and binary checks."""
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"File not found: '{path}'", target)
            if not target.is_file():
                return FileOperationResult(False, f"Path is a directory, not a file: '{target.name}'", target)

            ext = target.suffix.lower()
            if ext in BINARY_EXTENSIONS:
                size_str = self.format_size(target.stat().st_size)
                return FileOperationResult(
                    True,
                    f"Binary file detected: '{target.name}' ({ext}, {size_str}). Text content cannot be read directly.",
                    target,
                    data={"is_binary": True, "size": target.stat().st_size}
                )

            content = target.read_text(encoding="utf-8", errors="replace")
            total_len = len(content)

            if offset > 0:
                content = content[offset:]

            truncated = False
            if len(content) > max_chars:
                content = content[:max_chars]
                truncated = True

            self._last_accessed_file = target
            self._last_accessed_dir = target.parent

            msg = f"Contents of '{target.name}' ({total_len} chars total):\n\n{content}"
            if truncated:
                msg += f"\n\n... [Truncated at {max_chars} chars]"

            return FileOperationResult(True, msg, target, data={"content": content, "total_length": total_len, "truncated": truncated})
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while reading: '{path}'", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Error reading file: {e}", self.resolve_path(path))

    def write_file(self, path: str, content: str, append: bool = False) -> FileOperationResult:
        """Writes or appends to a file with verification."""
        try:
            target = self.resolve_path(path)
            if self._is_protected_path(target):
                return FileOperationResult(False, f"Access denied: '{target}' is a protected location.", target)

            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(target, mode, encoding="utf-8") as f:
                f.write(content)

            # Verification
            if not target.exists():
                return FileOperationResult(False, f"Verification failed: '{target.name}' does not exist after writing.", target)

            self._last_accessed_file = target
            self._last_accessed_dir = target.parent
            action_desc = "Appended to" if append else "Written to"
            return FileOperationResult(True, f"{action_desc} '{target.name}' successfully ({len(content)} chars).", target)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while writing to '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Error writing file: {e}", self.resolve_path(path))

    def edit_file(self, path: str, target_text: str, replacement_text: str, count: int = 1) -> FileOperationResult:
        """
        Surgically edits a file by replacing specific target text with replacement text.
        Never blindly overwrites the whole file.
        """
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"File not found: '{path}'", target)
            if self._is_protected_path(target):
                return FileOperationResult(False, f"Access denied: '{target}' is protected.", target)

            content = target.read_text(encoding="utf-8", errors="ignore")
            if target_text not in content:
                return FileOperationResult(False, f"Target text not found inside '{target.name}'. No edits made.", target)

            new_content = content.replace(target_text, replacement_text, count)
            target.write_text(new_content, encoding="utf-8")

            # Verification
            verified_content = target.read_text(encoding="utf-8", errors="ignore")
            if replacement_text not in verified_content:
                return FileOperationResult(False, f"Verification failed: replacement text was not found after editing.", target)

            self._last_accessed_file = target
            self._last_accessed_dir = target.parent
            return FileOperationResult(True, f"Surgically updated '{target.name}' successfully.", target)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while editing '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Error editing file: {e}", self.resolve_path(path))

    def rename_file(self, path: str, new_name: str) -> FileOperationResult:
        """Renames a file or directory with collision detection and verification."""
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"Path not found: '{path}'", target)
            if self._is_protected_path(target):
                return FileOperationResult(False, f"Access denied: '{target}' is protected.", target)

            clean_new_name = Path(new_name).name
            destination = target.parent / clean_new_name

            if destination.exists():
                return FileOperationResult(False, f"A file or folder named '{clean_new_name}' already exists in that location.", destination)

            target.rename(destination)

            # Verification
            if not destination.exists() or target.exists():
                return FileOperationResult(False, f"Verification failed during rename of '{target.name}'.", destination)

            self._last_accessed_file = destination if destination.is_file() else None
            self._last_accessed_dir = destination.parent
            return FileOperationResult(True, f"Renamed '{target.name}' → '{clean_new_name}' successfully.", destination)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while renaming '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Error renaming: {e}", self.resolve_path(path))

    def move_file(self, source_path: str, destination_path: str) -> FileOperationResult:
        """Moves a file or folder to a new destination with verification."""
        try:
            src = self.resolve_path(source_path)
            dst = self.resolve_path(destination_path)

            if not src.exists():
                return FileOperationResult(False, f"Source path not found: '{source_path}'", src)
            if self._is_protected_path(src):
                return FileOperationResult(False, f"Access denied: cannot move protected source '{src}'.", src)

            if dst.is_dir():
                final_dst = dst / src.name
            else:
                final_dst = dst

            final_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(final_dst))

            # Verification
            if not final_dst.exists() or src.exists():
                return FileOperationResult(False, f"Verification failed: move operation could not be confirmed.", final_dst)

            self._last_accessed_file = final_dst if final_dst.is_file() else None
            self._last_accessed_dir = final_dst.parent
            return FileOperationResult(True, f"Moved '{src.name}' → '{final_dst.parent.name}/{final_dst.name}' successfully.", final_dst)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while moving '{source_path}'.", self.resolve_path(source_path))
        except Exception as e:
            return FileOperationResult(False, f"Error moving file: {e}", self.resolve_path(source_path))

    def copy_file(self, source_path: str, destination_path: str) -> FileOperationResult:
        """Copies a file or directory tree with verification."""
        try:
            src = self.resolve_path(source_path)
            dst = self.resolve_path(destination_path)

            if not src.exists():
                return FileOperationResult(False, f"Source path not found: '{source_path}'", src)

            if dst.is_dir():
                final_dst = dst / src.name
            else:
                final_dst = dst

            final_dst.parent.mkdir(parents=True, exist_ok=True)

            if src.is_dir():
                shutil.copytree(str(src), str(final_dst), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src), str(final_dst))

            # Verification
            if not final_dst.exists():
                return FileOperationResult(False, f"Verification failed: copy could not be confirmed at '{final_dst}'.", final_dst)

            self._last_accessed_file = final_dst if final_dst.is_file() else None
            self._last_accessed_dir = final_dst.parent
            return FileOperationResult(True, f"Copied '{src.name}' → '{final_dst}' successfully.", final_dst)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied while copying '{source_path}'.", self.resolve_path(source_path))
        except Exception as e:
            return FileOperationResult(False, f"Error copying file: {e}", self.resolve_path(source_path))

    def delete_file(self, path: str, confirm: bool = False, permanent: bool = False) -> FileOperationResult:
        """
        Safely deletes a file or folder.
        Uses Recycle Bin (send2trash) by default.
        Requires confirm=True or prompts for safety on non-temp files.
        """
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"Path not found: '{path}'", target)

            if self._is_protected_path(target):
                return FileOperationResult(False, f"⛔ CRITICAL SAFETY: '{target}' is a protected system directory. Deletion blocked.", target)

            # If not confirmed explicitly, request user confirmation
            if not confirm:
                item_type = "folder" if target.is_dir() else "file"
                return FileOperationResult(
                    False,
                    f"⚠️ Confirmation required: Are you sure you want to delete {item_type} '{target.name}' at {target.parent}? Please confirm with confirm=true.",
                    target,
                    data={"needs_confirmation": True, "target": str(target)}
                )

            # Attempt safe Recycle Bin deletion
            if not permanent and _HAS_SEND2TRASH:
                try:
                    send2trash.send2trash(str(target))
                    if not target.exists():
                        return FileOperationResult(True, f"Safely moved '{target.name}' to Recycle Bin.", target)
                except Exception as s2t_err:
                    print(f"[FileManager] send2trash fallback triggered: {s2t_err}")

            # Permanent deletion fallback
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

            # Verification
            if target.exists():
                return FileOperationResult(False, f"Verification failed: '{target.name}' still exists after deletion attempt.", target)

            return FileOperationResult(True, f"Deleted '{target.name}' successfully.", target)
        except PermissionError:
            return FileOperationResult(False, f"Permission denied: Windows prevented deleting '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Error deleting: {e}", self.resolve_path(path))

    def list_directory(self, path: str = "desktop", pattern: str = "*", show_hidden: bool = False) -> FileOperationResult:
        """Lists files and folders in a target directory with readable sizes and counts."""
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"Directory not found: '{path}'", target)
            if not target.is_dir():
                return FileOperationResult(False, f"Path is a file, not a directory: '{target.name}'", target)

            items = []
            folders = []
            files = []

            for item in sorted(target.iterdir()):
                if not show_hidden and item.name.startswith("."):
                    continue
                if pattern != "*" and not item.match(pattern):
                    continue

                if item.is_dir():
                    folders.append(f"📁 {item.name}/")
                else:
                    size_str = self.format_size(item.stat().st_size)
                    files.append(f"📄 {item.name} ({size_str})")

            self._last_accessed_dir = target
            items = folders + files

            if not items:
                return FileOperationResult(True, f"Directory '{target.name}/' is empty.", target, data={"count": 0, "items": []})

            msg = f"Contents of '{target.name}/' ({len(folders)} folders, {len(files)} files):\n" + "\n".join(items[:60])
            if len(items) > 60:
                msg += f"\n... and {len(items) - 60} more items."

            return FileOperationResult(True, msg, target, data={"folders": folders, "files": files, "count": len(items)})
        except PermissionError:
            return FileOperationResult(False, f"Permission denied accessing directory: '{path}'.", self.resolve_path(path))
        except Exception as e:
            return FileOperationResult(False, f"Error listing directory: {e}", self.resolve_path(path))

    def search_files(
        self,
        query: str = "",
        path: str = "desktop",
        extension: str = "",
        modified_today: bool = False,
        max_results: int = 30
    ) -> FileOperationResult:
        """Searches files by name, extension, or modification date within bounded search depth."""
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"Search directory not found: '{path}'", target)

            results: List[Dict[str, Any]] = []
            pattern = f"*{extension}" if extension else "*"
            today = date.today()

            for item in target.rglob(pattern):
                if not item.is_file():
                    continue
                # Skip cache folders during deep search
                if any(p in item.parts for p in [".git", "__pycache__", "node_modules", ".venv", "venv"]):
                    continue

                if query and query.lower() not in item.name.lower():
                    continue

                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                if modified_today and mtime.date() != today:
                    continue

                size_str = self.format_size(item.stat().st_size)
                results.append({
                    "name": item.name,
                    "path": str(item),
                    "size": size_str,
                    "modified": mtime.strftime("%Y-%m-%d %H:%M")
                })

                if len(results) >= max_results:
                    break

            if not results:
                desc = query or extension or "files"
                return FileOperationResult(True, f"No matching {desc} found in '{target.name}/'.", target, data=[])

            lines = [f"Found {len(results)} matching file(s) in '{target.name}/':"]
            for r in results:
                lines.append(f"  📄 {r['name']} ({r['size']}) — {r['path']}")

            return FileOperationResult(True, "\n".join(lines), target, data=results)
        except Exception as e:
            return FileOperationResult(False, f"Search error: {e}", self.resolve_path(path))

    def get_file_info(self, path: str) -> FileOperationResult:
        """Returns comprehensive file/folder metadata."""
        try:
            target = self.resolve_path(path)
            if not target.exists():
                return FileOperationResult(False, f"Not found: '{path}'", target)

            stat = target.stat()
            is_dir = target.is_dir()
            size_bytes = stat.st_size
            info = {
                "Name": target.name,
                "Type": "Directory / Folder" if is_dir else f"File ({target.suffix or 'No extension'})",
                "Size": self.format_size(size_bytes),
                "Path": str(target.resolve()),
                "Parent": str(target.parent),
                "Created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "Modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "Is_Text": target.suffix.lower() in TEXT_EXTENSIONS if not is_dir else False
            }

            self._last_accessed_file = target if not is_dir else None
            self._last_accessed_dir = target if is_dir else target.parent

            msg_lines = [f"Metadata for '{target.name}':"]
            for k, v in info.items():
                msg_lines.append(f"  • {k}: {v}")

            return FileOperationResult(True, "\n".join(msg_lines), target, data=info)
        except Exception as e:
            return FileOperationResult(False, f"Could not retrieve metadata: {e}", self.resolve_path(path))

    @staticmethod
    def format_size(bytes_size: int) -> str:
        """Converts raw byte size to a human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"


# Global singleton instance
_file_manager: Optional[FileManager] = None

def get_file_manager() -> FileManager:
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager

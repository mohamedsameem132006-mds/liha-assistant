# actions/file_controller.py
# File management — create, delete, move, rename, list, find, organize, edit, info
# Powered by core/file_manager.py with full verification and safe protection.

import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from core.file_manager import get_file_manager, FileOperationResult

_fm = get_file_manager()


def _get_desktop() -> Path:
    return _fm.resolve_path("desktop")


def _get_downloads() -> Path:
    return _fm.resolve_path("downloads")


def _resolve_path(raw: str) -> Path:
    return _fm.resolve_path(raw)


def _format_size(bytes_size: int) -> str:
    return _fm.format_size(bytes_size)


def list_files(path: str = "desktop", show_hidden: bool = False) -> str:
    res = _fm.list_directory(path=path, show_hidden=show_hidden)
    return res.message


def create_file(path: str, content: str = "") -> str:
    res = _fm.create_file(path=path, content=content)
    return res.message


def create_folder(path: str) -> str:
    res = _fm.create_folder(path=path)
    return res.message


def delete_file(path: str, confirm: bool = False) -> str:
    res = _fm.delete_file(path=path, confirm=confirm)
    return res.message


def move_file(source: str, destination: str) -> str:
    res = _fm.move_file(source_path=source, destination_path=destination)
    return res.message


def copy_file(source: str, destination: str) -> str:
    res = _fm.copy_file(source_path=source, destination_path=destination)
    return res.message


def rename_file(path: str, new_name: str) -> str:
    res = _fm.rename_file(path=path, new_name=new_name)
    return res.message


def read_file(path: str, max_chars: int = 10000) -> str:
    res = _fm.read_file(path=path, max_chars=max_chars)
    return res.message


def write_file(path: str, content: str, append: bool = False) -> str:
    res = _fm.write_file(path=path, content=content, append=append)
    return res.message


def edit_file(path: str, target_text: str, replacement_text: str) -> str:
    res = _fm.edit_file(path=path, target_text=target_text, replacement_text=replacement_text)
    return res.message


def find_files(name: str = "", extension: str = "", path: str = "desktop", max_results: int = 25) -> str:
    res = _fm.search_files(query=name, path=path, extension=extension, max_results=max_results)
    return res.message


def get_largest_files(path: str = "desktop", count: int = 10) -> str:
    try:
        search_path = _fm.resolve_path(path)
        if not search_path.exists():
            return f"Path not found: {path}"

        files = []
        for item in search_path.rglob("*"):
            if item.is_file() and not any(p in item.parts for p in [".git", "__pycache__", "node_modules", ".venv"]):
                try:
                    files.append((item.stat().st_size, item))
                except Exception:
                    continue

        files.sort(reverse=True)
        top = files[:count]

        if not top:
            return "No files found."

        lines = [f"Top {len(top)} largest files in {search_path.name}/:\n"]
        for size, f in top:
            lines.append(f"  {_fm.format_size(size):>10}  {f.name}  ({f.parent})")

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def get_disk_usage(path: str = "desktop") -> str:
    try:
        target = _fm.resolve_path(path)
        usage  = shutil.disk_usage(target)
        total  = _fm.format_size(usage.total)
        used   = _fm.format_size(usage.used)
        free   = _fm.format_size(usage.free)
        pct    = usage.used / usage.total * 100

        return (
            f"Disk usage for {target}:\n"
            f"  Total : {total}\n"
            f"  Used  : {used} ({pct:.1f}%)\n"
            f"  Free  : {free}"
        )
    except Exception as e:
        return f"Could not get disk usage: {e}"


def organize_desktop() -> str:
    try:
        desktop = _fm.resolve_path("desktop")
        type_map = {
            "Images":    [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
            "Videos":    [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
            "Music":     [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"],
            "Archives":  [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code":      [".py", ".js", ".html", ".css", ".json", ".xml", ".ts", ".cpp", ".java"],
        }

        moved   = []
        skipped = []

        for item in desktop.iterdir():
            if item.is_dir() or item.name.startswith("."):
                continue

            ext = item.suffix.lower()
            target_dir = None

            for folder, extensions in type_map.items():
                if ext in extensions:
                    target_dir = desktop / folder
                    break

            if target_dir is None:
                target_dir = desktop / "Others"

            target_dir.mkdir(exist_ok=True)
            new_path = target_dir / item.name

            if new_path.exists():
                skipped.append(item.name)
                continue

            shutil.move(str(item), str(new_path))
            moved.append(f"{item.name} → {target_dir.name}/")

        result = f"Desktop organized. {len(moved)} files moved."
        if moved:
            result += "\n" + "\n".join(moved[:10])
            if len(moved) > 10:
                result += f"\n... and {len(moved)-10} more."
        if skipped:
            result += f"\n{len(skipped)} files skipped (already exist)."

        return result
    except Exception as e:
        return f"Could not organize desktop: {e}"


def get_file_info(path: str) -> str:
    res = _fm.get_file_info(path)
    return res.message


def file_controller(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None
) -> str:
    params = parameters or {}
    action = params.get("action", "").lower().strip()
    path   = params.get("path", "desktop")
    name   = params.get("name", "")
    content = params.get("content", "")

    def _full_path(p: str, n: str) -> str:
        base = _fm.resolve_path(p)
        if n:
            return str(base / n)
        return str(base)

    target_full = _full_path(path, name)
    result = "Unknown action."

    try:
        if action in ("list", "ls", "dir"):
            result = list_files(path)

        elif action in ("create_file", "create", "touch"):
            result = create_file(target_full, content=content)

        elif action in ("create_folder", "mkdir"):
            result = create_folder(target_full)

        elif action in ("delete", "remove", "rm"):
            confirm = bool(params.get("confirm", False))
            result = delete_file(target_full, confirm=confirm)

        elif action in ("move", "mv"):
            result = move_file(target_full, params.get("destination", ""))

        elif action in ("copy", "cp"):
            result = copy_file(target_full, params.get("destination", ""))

        elif action in ("rename", "ren"):
            result = rename_file(target_full, params.get("new_name", ""))

        elif action in ("read", "view", "cat"):
            result = read_file(target_full, max_chars=params.get("max_chars", 10000))

        elif action in ("write", "save"):
            result = write_file(
                target_full,
                content=content,
                append=params.get("append", False)
            )

        elif action in ("append", "add"):
            result = write_file(target_full, content=content, append=True)

        elif action in ("edit", "modify"):
            target_text = params.get("target_text", params.get("find", ""))
            replacement = params.get("replacement_text", params.get("replace", ""))
            result = edit_file(target_full, target_text=target_text, replacement_text=replacement)

        elif action in ("find", "search"):
            result = find_files(
                name=name or params.get("query", ""),
                extension=params.get("extension", ""),
                path=path,
                max_results=params.get("max_results", 25)
            )

        elif action == "largest":
            result = get_largest_files(
                path=path,
                count=params.get("count", 10)
            )

        elif action == "disk_usage":
            result = get_disk_usage(path)

        elif action == "organize_desktop":
            result = organize_desktop()

        elif action in ("info", "metadata"):
            result = get_file_info(target_full)

        else:
            result = f"Unknown file action: '{action}'"

    except Exception as e:
        result = f"File controller error: {e}"

    if player:
        player.write_log(f"[file] {result[:60]}")

    return result
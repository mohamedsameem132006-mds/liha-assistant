"""
core/diagnostics.py
Self-diagnostic, health check, and safe restart system for LIHA.
Handles commands:
- "LIHA status"
- "Check yourself" / "Run diagnostic"
- "LIHA restart"
"""

import sys
import os
import time
import json
import psutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


class LIHADiagnostics:
    def __init__(self):
        self.base_dir = BASE_DIR

    def run_health_check(self) -> Dict[str, Any]:
        """Runs a complete self-check on all LIHA subsystems."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "os": f"{platform.system()} {platform.release()}",
            "python": platform.python_version(),
            "subsystems": {},
            "all_healthy": True,
            "issues": []
        }

        # 1. Configuration & Keys Check
        cfg_status = {"healthy": False, "details": ""}
        try:
            if CONFIG_PATH.exists():
                cfg_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                g_key = cfg_data.get("gemini_api_key", "").strip()
                if g_key and g_key != "dummy" and len(g_key) > 10:
                    cfg_status["healthy"] = True
                    cfg_status["details"] = "Gemini API key configured"
                else:
                    cfg_status["details"] = "Gemini API key missing or invalid"
                    report["issues"].append("API Key missing in config/api_keys.json")
            else:
                cfg_status["details"] = "api_keys.json not found"
                report["issues"].append("config/api_keys.json not found")
        except Exception as e:
            cfg_status["details"] = f"Config error: {e}"
            report["issues"].append(str(e))
        report["subsystems"]["configuration"] = cfg_status

        # 2. File Tools Check
        from core.file_manager import get_file_manager
        fm = get_file_manager()
        file_status = {"healthy": False, "details": ""}
        try:
            test_res = fm.resolve_path("desktop")
            if test_res.exists():
                file_status["healthy"] = True
                file_status["details"] = f"File system operational (Desktop: {test_res})"
            else:
                file_status["healthy"] = True
                file_status["details"] = "File manager loaded"
        except Exception as e:
            file_status["details"] = f"File manager error: {e}"
            report["issues"].append(f"File manager: {e}")
        report["subsystems"]["file_tools"] = file_status

        # 3. Memory Subsystem Check
        mem_status = {"healthy": False, "details": ""}
        try:
            from memory.memory_manager import load_memory
            mem_data = load_memory()
            if isinstance(mem_data, dict):
                mem_status["healthy"] = True
                mem_status["details"] = f"Active memory entries: {len(mem_data)} categories"
            else:
                mem_status["details"] = "Memory returned invalid data"
        except Exception as e:
            mem_status["details"] = f"Memory error: {e}"
            report["issues"].append(f"Memory: {e}")
        report["subsystems"]["memory"] = mem_status

        # 4. Core Actions Check
        act_status = {"healthy": False, "details": ""}
        try:
            actions_dir = self.base_dir / "actions"
            if actions_dir.exists():
                action_files = [f.name for f in actions_dir.glob("*.py") if not f.name.startswith("__")]
                act_status["healthy"] = True
                act_status["details"] = f"{len(action_files)} action modules registered"
            else:
                act_status["details"] = "Actions folder missing"
                report["issues"].append("Actions folder not found")
        except Exception as e:
            act_status["details"] = f"Action error: {e}"
            report["issues"].append(f"Actions: {e}")
        report["subsystems"]["actions"] = act_status

        # 5. AI Client / OpenRouter Fallback Check
        ai_status = {"healthy": False, "details": ""}
        try:
            from or_client import client
            if client:
                ai_status["healthy"] = True
                ai_status["details"] = "AI Client initialized"
        except Exception as e:
            ai_status["details"] = f"AI Client warning: {e}"
        report["subsystems"]["ai_client"] = ai_status

        # 6. System Resources Check
        sys_status = {"healthy": True, "details": ""}
        try:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            sys_status["details"] = f"CPU: {cpu_pct}% | RAM Used: {mem.percent}% ({mem.available // (1024*1024)} MB free)"
        except Exception as e:
            sys_status["details"] = f"Resource check error: {e}"
        report["subsystems"]["system_resources"] = sys_status

        if report["issues"]:
            report["all_healthy"] = False

        return report

    def format_status_report(self) -> str:
        """Formats the diagnostics into a clean Jarvis-style report."""
        report = self.run_health_check()
        lines = [
            "==================================================",
            "🛡️ LIHA SYSTEM STATUS & DIAGNOSTICS",
            "==================================================",
            f"• Platform: {report['os']} (Python {report['python']})",
            f"• Timestamp: {report['timestamp']}",
            "",
            "📊 SUBSYSTEM CHECKS:"
        ]

        for name, sub in report["subsystems"].items():
            icon = "✓" if sub.get("healthy", False) else "⚠️"
            label = name.replace("_", " ").title()
            lines.append(f"  [{icon}] {label:<18}: {sub.get('details')}")

        lines.append("==================================================")
        if report["all_healthy"]:
            lines.append("✨ All LIHA core subsystems are healthy and operational.")
        else:
            lines.append(f"⚠️ Issues detected: {', '.join(report['issues'])}")
        lines.append("==================================================")

        return "\n".join(lines)

    @staticmethod
    def restart_liha() -> str:
        """Safely restarts the LIHA application process."""
        try:
            main_script = BASE_DIR / "main.py"
            # Launch fresh process
            subprocess.Popen([sys.executable, str(main_script)], cwd=str(BASE_DIR))
            
            # Request exit after launching
            def _exit():
                time.sleep(1.0)
                os._exit(0)

            import threading
            threading.Thread(target=_exit, daemon=True).start()
            return "Restarting LIHA AI Assistant now..."
        except Exception as e:
            return f"Failed to restart LIHA: {e}"


# Singleton helper
_diagnostics = LIHADiagnostics()

def get_diagnostics() -> LIHADiagnostics:
    return _diagnostics

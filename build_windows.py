"""
Liha Assistant - Production Windows Build & Packaging Script
Usage:
    python build_windows.py
Options:
    --skip-build    Skip PyInstaller build and only sign/package
    --sign          Sign executable using Authenticode
    --dev-cert      Auto-create and use a local test certificate for signing
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist" / "LihaAssistant"
OUTPUT_ZIP = BASE_DIR / "dist" / "LihaAssistant-v1.0.0-Windows.zip"

def build_pyinstaller():
    print("==================================================")
    print(" 1. Building Liha Assistant via PyInstaller")
    print("==================================================")
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "LihaAssistant.exe"], capture_output=True)
        except Exception:
            pass

    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "liha.spec"]
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print("[Build] PyInstaller compilation failed!")
        sys.exit(res.returncode)
    print("[Build] PyInstaller compilation succeeded.")

def copy_assets():
    print("==================================================")
    print(" 2. Verifying & Copying Required Assets")
    print("==================================================")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy root assets
    for fname in ["face.png", "liha_icon.ico"]:
        src = BASE_DIR / fname
        if src.exists():
            shutil.copy2(src, DIST_DIR / fname)
            print(f"[Assets] Copied {fname} to {DIST_DIR.name}")

    # Copy folders
    for dname in ["core", "config"]:
        src = BASE_DIR / dname
        dst = DIST_DIR / dname
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"[Assets] Copied {dname}/ to {DIST_DIR.name}/{dname}")

def sign_binary():
    print("==================================================")
    print(" 3. Signing Binary with Authenticode")
    print("==================================================")
    target_exe = DIST_DIR / "LihaAssistant.exe"
    if not target_exe.exists():
        print(f"[Sign] Target executable not found at: {target_exe}")
        return

    sign_script = BASE_DIR / "sign_executable.py"
    if sign_script.exists():
        subprocess.run([sys.executable, str(sign_script), str(target_exe)], cwd=str(BASE_DIR))

def create_desktop_shortcut():
    print("==================================================")
    print(" 4. Installing Desktop Shortcut for Taskbar Pinning")
    print("==================================================")
    desktop = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"
    shortcut_path = desktop / "Liha Assistant.lnk"
    exe_path = DIST_DIR / "LihaAssistant.exe"
    icon_path = DIST_DIR / "liha_icon.ico"
    
    vbs = f"""
Set WshShell = CreateObject("WScript.Shell")
Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
shortcut.TargetPath = "{exe_path}"
shortcut.WorkingDirectory = "{DIST_DIR}"
shortcut.Description = "Liha Assistant - Desktop AI Voice Assistant"
shortcut.IconLocation = "{icon_path}, 0"
shortcut.Save
"""
    vbs_file = BASE_DIR / "make_shortcut.vbs"
    vbs_file.write_text(vbs, encoding="utf-8")
    subprocess.run(["cscript", "//NoLogo", str(vbs_file)])
    if vbs_file.exists():
        vbs_file.unlink()
    print(f"[Shortcut] Desktop shortcut created at: {shortcut_path}")

def package_zip():
    print("==================================================")
    print(" 5. Creating Distribution ZIP Archive")
    print("==================================================")
    if DIST_DIR.exists():
        zip_base = BASE_DIR / "dist" / "LihaAssistant-v1.0.0-Windows"
        archive = shutil.make_archive(str(zip_base), "zip", root_dir=str(DIST_DIR.parent), base_dir=DIST_DIR.name)
        print(f"[Package] Distribution archive created at: {archive}")

def main():
    parser = argparse.ArgumentParser(description="Liha Assistant Windows Build System")
    parser.add_argument("--skip-build", action="store_true", help="Skip PyInstaller build")
    args = parser.parse_args()

    if not args.skip_build:
        build_pyinstaller()
    copy_assets()
    sign_binary()
    create_desktop_shortcut()
    package_zip()
    print("==================================================")
    print(" [SUCCESS] PRODUCTION BUILD & DESKTOP INSTALLATION COMPLETE!")
    print("==================================================")

if __name__ == "__main__":
    main()

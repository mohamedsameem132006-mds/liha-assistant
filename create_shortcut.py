import os
import sys
from pathlib import Path

def create_shortcut_vbs():
    base_dir = Path(__file__).resolve().parent
    dist_exe = base_dir / "dist" / "LihaAssistant" / "LihaAssistant.exe"
    icon_path = base_dir / "dist" / "LihaAssistant" / "liha_icon.ico"
    if not icon_path.exists():
        icon_path = base_dir / "liha_icon.ico"
    if not icon_path.exists():
        icon_path = base_dir / "face.png"
    
    if dist_exe.exists():
        exe_path = dist_exe
        work_dir = dist_exe.parent
    else:
        exe_path = sys.executable
        work_dir = base_dir

    desktop = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"
    shortcut_path = desktop / "Liha Assistant.lnk"
    
    vbs_script = f'''
Set WshShell = CreateObject("WScript.Shell")
Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
shortcut.TargetPath = "{exe_path}"
shortcut.WorkingDirectory = "{work_dir}"
shortcut.Description = "Liha Assistant - Desktop AI Voice Assistant"
'''
    if icon_path.exists():
        vbs_script += f'shortcut.IconLocation = "{icon_path}, 0"\n'
    vbs_script += 'shortcut.Save\n'
    
    vbs_file = base_dir / "create_lnk.vbs"
    with open(vbs_file, "w", encoding="utf-8") as f:
        f.write(vbs_script)
        
    os.system(f'cscript //NoLogo "{vbs_file}"')
    if vbs_file.exists():
        os.remove(vbs_file)
    print(f"Desktop shortcut created successfully: {shortcut_path}")

if __name__ == "__main__":
    create_shortcut_vbs()


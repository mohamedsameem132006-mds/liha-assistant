# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys

block_cipher = None

spec_root = Path(SPECPATH).resolve()

datas = [
    (str(spec_root / 'face.png'), '.'),
    (str(spec_root / 'liha_icon.ico'), '.'),
]

prompt_file = spec_root / 'core' / 'prompt.txt'
if prompt_file.exists():
    datas.append((str(prompt_file), 'core'))

config_file = spec_root / 'config' / 'api_keys.json'
if config_file.exists():
    datas.append((str(config_file), 'config'))

hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'sounddevice',
    'google.genai',
    'google.genai.types',
    'google.generativeai',
    'comtypes',
    'comtypes.client',
    'psutil',
    'send2trash',
    'win10toast',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'cv2',
    'numpy',
    'mss',
    'pycaw',
    'pycaw.pycaw',
    'pyautogui',
    'pyperclip',
    'pygetwindow',
    'queue',
    'asyncio',
    'ctypes',
    'core',
    'core.file_manager',
    'core.action_router',
    'core.project_analyzer',
    'core.diagnostics',
    'actions',
    'actions.file_processor',
    'actions.flight_finder',
    'actions.open_app',
    'actions.weather_report',
    'actions.send_message',
    'actions.reminder',
    'actions.computer_settings',
    'actions.screen_processor',
    'actions.youtube_video',
    'actions.desktop',
    'actions.browser_control',
    'actions.file_controller',
    'actions.code_helper',
    'actions.dev_agent',
    'actions.web_search',
    'actions.computer_control',
    'actions.game_updater',
    'actions.food_vision',
    'agent',
    'agent.error_handler',
    'agent.executor',
    'agent.planner',
    'agent.task_queue',
    'memory',
    'memory.config_manager',
    'memory.memory_manager',
]

a = Analysis(
    ['main.py'],
    pathex=[str(spec_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'notebook', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LihaAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_root / 'liha_icon.ico'),
    version=str(spec_root / 'version_info.txt'),
    manifest=str(spec_root / 'liha_manifest.xml') if (spec_root / 'liha_manifest.xml').exists() else str(spec_root / 'liha.manifest'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LihaAssistant',
)

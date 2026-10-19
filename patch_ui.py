import re

with open('ui.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Remove openrouter from check_config
code = re.sub(
    r'bool\(d\.get\("openrouter_api_key"\)\) and\s*',
    '',
    code
)

# 2. Remove OpenRouter key from on_setup_done
code = re.sub(
    r'def _on_setup_done\(self, key: str, or_key: str, os_name: str\):',
    r'def _on_setup_done(self, key: str, os_name: str):\n        or_key = "dummy"',
    code
)

# 3. SetupOverlay done emit
code = re.sub(
    r'self\.done\.emit\(key, or_key, self\._sel_os\)',
    r'self.done.emit(key, self._sel_os)',
    code
)

# 4. SetupOverlay done signal
code = re.sub(
    r'done = pyqtSignal\(str, str, str\)',
    r'done = pyqtSignal(str, str)',
    code
)

# 5. Remove or_input check in _submit
code = re.sub(
    r'if not or_key:[\s\S]*?return',
    r'',
    code
)

with open('ui.py', 'w', encoding='utf-8') as f:
    f.write(code)

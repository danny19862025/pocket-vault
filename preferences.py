"""Remember the last vault location without storing passwords or vault contents."""
import json
import os
from pathlib import Path
import tempfile


def settings_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'pocket-vault/preferences.json'


def last_vault():
    try:
        settings = json.loads(settings_path().read_text())
        value = settings.get('last_vault') if isinstance(settings, dict) else None
        return value if isinstance(value, str) and value and '\x00' not in value else None
    except (OSError, ValueError):
        return None


def remember_vault(path):
    target = settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.preferences-', dir=target.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump({'last_vault': str(Path(path).expanduser().absolute())}, stream)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

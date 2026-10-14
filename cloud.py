"""Cloud backups contain only already-encrypted vault bytes; rclone owns OAuth."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


class Cloud:
    def __init__(self):
        self.settings_path = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'pocket-vault/cloud.json'
        try:
            self.settings = json.loads(self.settings_path.read_text())
            if not isinstance(self.settings, dict):
                self.settings = {}
        except (OSError, ValueError):
            self.settings = {}

    def run(self, *args, timeout=120):
        if not shutil.which('rclone'):
            raise ValueError('Install rclone first (on Arch: sudo pacman -S rclone).')
        try:
            result = subprocess.run(['rclone', *args], stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise ValueError('Cloud operation timed out. Check your connection and try again.') from None
        if result.returncode:
            # Do not surface provider output, which could include OAuth tokens.
            raise ValueError('Cloud operation failed. Check your connection, account permissions, and cloud destination, then retry.')
        return result.stdout

    def remotes(self):
        return self.run('listremotes').decode().splitlines()

    def connect_drive(self):
        name = 'pocket-vault-' + uuid.uuid4().hex[:12]
        self.run('config', 'create', name, 'drive', 'scope', 'drive.file',
                 'config_is_local', 'true', timeout=300)
        return name + ':'

    def connect_dropbox(self):
        name = 'pocket-vault-dropbox-' + uuid.uuid4().hex[:12]
        self.run('config', 'create', name, 'dropbox', 'config_is_local', 'true', timeout=300)
        return name + ':'

    @staticmethod
    def destination(remote, folder):
        if not re.fullmatch(r'[\w .-]+:', remote) or remote.startswith('-'):
            raise ValueError('Select a connected cloud account.')
        folder = folder.strip().strip('/')
        if not folder or any(p in ('.', '..') for p in folder.split('/')) or ':' in folder or '\\' in folder:
            raise ValueError('Enter a cloud folder such as KeyKite.')
        return remote + folder

    def configure(self, remote, folder, vault_path, automatic):
        self.destination(remote, folder)
        settings = dict(self.settings)
        settings.update(remote=remote, folder=folder.strip().strip('/'))
        automatic_paths = set(settings.get('automatic_paths', []))
        if vault_path:
            key = str(Path(vault_path).expanduser().absolute())
            if automatic:
                automatic_paths.add(key)
            else:
                automatic_paths.discard(key)
        settings['automatic_paths'] = sorted(automatic_paths)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.settings_path.parent, prefix='.cloud-')
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(settings, stream)
            os.replace(temporary, self.settings_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.settings = settings

    def automatic(self, path):
        return str(Path(path).expanduser().absolute()) in self.settings.get('automatic_paths', [])

    def backup(self, raw, remote, folder):
        destination = self.destination(remote, folder)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        name = f'backup-{stamp}-{uuid.uuid4().hex}.vault'
        with tempfile.TemporaryDirectory(prefix='pocket-vault-') as directory:
            source = Path(directory) / name
            source.touch(mode=0o600)
            source.write_bytes(raw)
            self.run('copyto', str(source), destination + '/' + name, '--immutable', '--retries', '1')
        return name

    def backups(self, remote, folder):
        result = json.loads(self.run('lsjson', self.destination(remote, folder), '--files-only'))
        return sorted((item['Name'] for item in result
                       if re.fullmatch(r'backup-\d{8}T\d{6}Z-[0-9a-f]{32}\.vault', item.get('Name', ''))), reverse=True)

    def restore(self, remote, folder, name, path):
        if not re.fullmatch(r'backup-\d{8}T\d{6}Z-[0-9a-f]{32}\.vault', name):
            raise ValueError('Select a KeyKite backup.')
        target = Path(path).expanduser()
        if target.exists():
            raise ValueError('Choose a new local filename. Restore never overwrites a vault.')
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.vault-', dir=target.parent)
        os.close(fd)
        try:
            self.run('copyto', self.destination(remote, folder) + '/' + name, temporary, '--retries', '1')
            os.chmod(temporary, 0o600)
            os.link(temporary, target)
        finally:
            os.unlink(temporary)
        return str(target)

"""Cloud regressions use dummy encrypted bytes and no real cloud account."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cloud import Cloud
from vault import Vault


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.environment = patch.dict(os.environ, XDG_CONFIG_HOME=str(self.root / 'config'))
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.cloud = Cloud()

    def test_connect_dropbox_uses_browser_oauth_and_unique_remote(self):
        with patch.object(self.cloud, 'run', return_value=b'') as run:
            first = self.cloud.connect_dropbox()
            second = self.cloud.connect_dropbox()
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith('pocket-vault-dropbox-'))
        self.assertEqual(run.call_args_list[0].args,
                         ('config', 'create', first[:-1], 'dropbox', 'config_is_local', 'true'))
        self.assertEqual(run.call_args_list[0].kwargs['timeout'], 300)

    def test_preferences_are_per_vault_and_private(self):
        path = self.root / 'test.vault'
        self.cloud.configure('drive:', 'Pocket Vault', path, True)
        self.assertTrue(Cloud().automatic(path))
        self.assertFalse(Cloud().automatic(self.root / 'other.vault'))
        self.assertEqual(self.cloud.settings_path.stat().st_mode & 0o777, 0o600)
        self.cloud.configure('drive:', 'Pocket Vault', path, False)
        self.assertFalse(self.cloud.automatic(path))

    def test_upload_snapshot_is_encrypted_and_unique(self):
        vault = Vault(self.root / 'test.vault', 'temporary master password', create=True)
        vault.save([dict(id='1', name='Service', username='email', password='secret credential', url='')])
        calls = []

        def run(*args):
            raw = Path(args[1]).read_bytes()
            self.assertEqual(raw, vault.original)
            self.assertNotIn(b'secret credential', raw)
            self.assertEqual(Path(args[1]).stat().st_mode & 0o777, 0o600)
            calls.append(args)
            return b''

        with patch.object(self.cloud, 'run', side_effect=run):
            first = self.cloud.backup(vault.original, 'drive:', 'Pocket Vault')
            second = self.cloud.backup(vault.original, 'drive:', 'Pocket Vault')
        self.assertNotEqual(first, second)
        self.assertIn('--immutable', calls[0])
        self.assertFalse(Path(calls[0][1]).exists())

    def test_restore_does_not_overwrite_and_is_unlockable(self):
        vault = Vault(self.root / 'source.vault', 'temporary master password', create=True)
        name = 'backup-20261013T100000Z-' + 'a' * 32 + '.vault'
        target = self.root / 'restored.vault'

        def run(*args):
            Path(args[2]).write_bytes(vault.original)

        with patch.object(self.cloud, 'run', side_effect=run):
            self.cloud.restore('drive:', 'Pocket Vault', name, target)
            with self.assertRaises(ValueError):
                self.cloud.restore('drive:', 'Pocket Vault', name, target)
        self.assertEqual(Vault(target, 'temporary master password').entries, [])
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_restore_failure_leaves_no_file(self):
        target = self.root / 'restore.vault'
        with patch.object(self.cloud, 'run', side_effect=ValueError('offline')):
            with self.assertRaises(ValueError):
                self.cloud.restore('drive:', 'Pocket Vault', 'backup-20261013T100000Z-' + 'a' * 32 + '.vault', target)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob('.vault-*')), [])

    @unittest.skipUnless(shutil.which('rclone'), 'Requires rclone')
    def test_real_rclone_round_trip_with_local_remote(self):
        # A temporary local backend exercises real commands without using an account.
        vault = Vault(self.root / 'source.vault', 'temporary master password', create=True)
        with patch.dict(os.environ, RCLONE_CONFIG_PVTEST_TYPE='local', RCLONE_CONFIG=str(self.root / 'rclone.conf')), patch('cloud.Cloud.destination', return_value='pvtest:' + str(self.root / 'backups')):
            name = self.cloud.backup(vault.original, 'pvtest:', str(self.root / 'backups'))
            self.assertEqual(self.cloud.backups('pvtest:', str(self.root / 'backups')), [name])
            target = self.root / 'restored.vault'
            self.cloud.restore('pvtest:', str(self.root / 'backups'), name, target)
        self.assertEqual(target.read_bytes(), vault.original)
        self.assertEqual(Vault(target, 'temporary master password').entries, [])

    def test_validation_listing_and_errors(self):
        for remote, folder in [('', 'x'), ('-bad:', 'x'), ('drive:', '../x'), ('drive:', 'x:y')]:
            with self.assertRaises(ValueError):
                self.cloud.destination(remote, folder)
        name = 'backup-20261013T100000Z-' + 'a' * 32 + '.vault'
        with patch.object(self.cloud, 'run', return_value=json.dumps([{'Name': name}, {'Name': '../bad.vault'}]).encode()):
            self.assertEqual(self.cloud.backups('drive:', 'Pocket Vault'), [name])
        with patch('cloud.shutil.which', return_value='/usr/bin/rclone'), patch('cloud.subprocess.run', return_value=subprocess.CompletedProcess([], 1, b'', b'sensitive token')):
            with self.assertRaises(ValueError) as error:
                self.cloud.run('listremotes')
            self.assertNotIn('sensitive', str(error.exception))


if __name__ == '__main__':
    unittest.main()

import json
from pathlib import Path
import tempfile
import unittest

from vault import Vault


class VaultTests(unittest.TestCase):
    def test_storage_and_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.vault'
            password = 'a long test master password'
            first = Vault(path, password, create=True)
            entry = dict(id='one', name='Example', username='danny', password='secret-value', url='')
            first.save([entry])
            self.assertNotIn(b'secret-value', path.read_bytes())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            second = Vault(path, password)
            self.assertEqual(second.entries, [entry])
            with self.assertRaises(ValueError):
                Vault(path, 'incorrect password')
            with self.assertRaises(ValueError):
                Vault(path, password, create=True)
            first.save([])
            with self.assertRaises(ValueError):
                second.save([entry])
            envelope = json.loads(path.read_bytes())
            envelope['data'] = envelope['data'][:-8] + 'AAAAAAAA'
            path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError):
                Vault(path, password)

class ValidationTests(unittest.TestCase):
    def test_reject_invalid_ids_without_changing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.vault'
            vault = Vault(path, 'temporary master password', create=True)
            original = path.read_bytes()
            entry = dict(id='one', name='A', username='', password='secret', url='')
            for entries in ([entry, entry], [dict(entry, id='')], [{}], {}):
                with self.assertRaises(ValueError):
                    vault.save(entries)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(vault.entries, [])

    def test_duplicate_ids_in_encrypted_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.vault'
            vault = Vault(path, 'temporary master password', create=True)
            entry = dict(id='one', name='A', username='', password='secret', url='')
            envelope = json.loads(path.read_bytes())
            envelope['data'] = vault.cipher.encrypt(json.dumps([entry, entry]).encode()).decode()
            path.write_text(json.dumps(envelope))
            with self.assertRaises(ValueError):
                Vault(path, 'temporary master password')


if __name__ == '__main__':
    unittest.main()

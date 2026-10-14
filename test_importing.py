import json
from pathlib import Path
import tempfile
import unittest

from importing import load_export, prepare_entries


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def read(self, text, suffix='.csv', encoding='utf-8'):
        path = self.root / ('export' + suffix)
        path.write_text(text, encoding=encoding, newline='')
        data = load_export(path)
        return data, prepare_entries(data, data.mapping(), [])

    def test_browser_csv_preserves_password_and_quoted_cells(self):
        data, (entries, skipped, duplicates) = self.read('\ufeffname,url,username,password\n"Example, Inc",https://example.com,alice,"  s,ecret\nline  "\n')
        self.assertEqual(entries[0]['name'], 'Example, Inc')
        self.assertEqual(entries[0]['password'], '  s,ecret\nline  ')
        self.assertEqual((skipped, duplicates), (0, 0))

    def test_common_csv_layouts_and_delimiters(self):
        samples = [
            ('Account,Login Name,Password,Web Site\nExample,alice,secret,https://example.com\n', '.csv', 'utf-8'),
            ('Title;Username;Password;URL\nExample;alice;secret;https://example.com\n', '.csv', 'utf-16'),
            ('name\tusername\tpassword\turl\nExample\talice\tsecret\thttps://example.com\n', '.tsv', 'utf-8'),
            ('url,username,password,extra\nhttps://example.com,alice,secret,ignored\n', '.csv', 'utf-8'),
        ]
        for text, suffix, encoding in samples:
            with self.subTest(suffix=suffix, encoding=encoding):
                _, (entries, skipped, duplicates) = self.read(text, suffix, encoding)
                self.assertEqual(entries[0]['username'], 'alice')
                self.assertEqual(entries[0]['password'], 'secret')
                self.assertEqual(entries[0]['url'], 'https://example.com')
                self.assertTrue(entries[0]['name'])
                self.assertEqual((skipped, duplicates), (0, 0))

    def test_bitwarden_csv_and_json_skip_other_types(self):
        _, (entries, skipped, _) = self.read('type,name,login_uri,login_username,login_password\nlogin,Example,https://example.com,alice,secret\nnote,Note,,,\n')
        self.assertEqual(len(entries), 1)
        self.assertEqual(skipped, 1)
        sample = {'encrypted': False, 'items': [
            {'type': 1, 'name': 'Example', 'login': {'username': None, 'password': ' secret ', 'uris': [{'uri': None}, {'uri': 'https://example.com'}]}},
            {'type': 2, 'name': 'Note'}, {'type': 1, 'name': 'Passkey', 'login': {'password': None}},
        ]}
        _, (entries, skipped, _) = self.read(json.dumps(sample), '.json')
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['password'], ' secret ')
        self.assertEqual(entries[0]['url'], 'https://example.com')
        self.assertEqual(entries[0]['username'], '')
        self.assertEqual(skipped, 2)

    def test_duplicate_skip_and_changed_password_keep_both(self):
        data, (entries, _, _) = self.read('name,username,password,url\nExample,alice,secret,\nExample,alice,secret,\nExample,alice,changed,\n')
        self.assertEqual(len(entries), 2)
        imported, skipped, duplicates = prepare_entries(data, data.mapping(), [entries[0]])
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0]['password'], 'changed')
        self.assertEqual(duplicates, 2)
        self.assertNotEqual(imported[0]['id'], entries[0]['id'])

    def test_generic_json_and_manual_mapping(self):
        data, (entries, _, _) = self.read(json.dumps({'entries': [{'title': 'Example', 'password': 'secret', 'username': 'alice'}]}), '.json')
        self.assertEqual(entries[0]['name'], 'Example')
        path = self.root / 'custom.csv'
        path.write_text('Label,User ID,Credential,Address\nExample,alice,secret,https://example.com\n')
        data = load_export(path)
        with self.assertRaises(ValueError):
            prepare_entries(data, data.mapping(), [])
        mapping = dict(name='Label', username='User ID', password='Credential', url='Address')
        entries, _, _ = prepare_entries(data, mapping, [])
        self.assertEqual(entries[0]['password'], 'secret')

    def test_bad_exports_rejected_without_credentials_in_errors(self):
        for text, suffix in [('{"encrypted": true}', '.json'), ('{not JSON secret}', '.json'),
                             ('name,password\nExample,secret,extra', '.csv'), ('name,name\nsecret,secret', '.csv'),
                             ('{"data": "encrypted"}', '.json'), ('native format', '.kdbx')]:
            with self.subTest(suffix=suffix):
                path = self.root / ('bad' + suffix)
                path.write_text(text)
                with self.assertRaises(ValueError) as error:
                    load_export(path)
                self.assertNotIn('secret', str(error.exception))

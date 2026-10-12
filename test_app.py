"""GUI regression test; run with a graphical display available."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import App


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires a graphical display')
class AppTests(unittest.TestCase):
    def test_create_save_lock_and_unlock(self):
        with tempfile.TemporaryDirectory() as directory:
            app = App()
            self.addCleanup(app.destroy)
            app.withdraw()
            with patch('app.messagebox.showerror') as error:
                app.update()
                self.assertIsNone(app.master)
                app.path.set(str(Path(directory) / 'test.vault'))
                app.master_password.set('temporary test password')
                app.confirm.set('temporary test password')
                app.unlock(True)
                app.fields['name'].set('Test service')
                app.fields['password'].set('test credential')
                app.save()
                app.login()
                self.assertIsNone(app.vault)
                app.master_password.set('temporary test password')
                app.unlock(False)
                app.update()
                error.assert_not_called()
                self.assertEqual(app.vault.entries[0]['name'], 'Test service')
                self.assertEqual(app.vault.entries[0]['password'], 'test credential')

@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires a graphical display')
class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = App()
        self.addCleanup(self.app.destroy)
        self.app.withdraw()
        self.app.path.set(str(Path(self.directory.name) / 'test.vault'))
        self.app.master_password.set('temporary master password')
        self.app.confirm.set('temporary master password')
        self.app.unlock(True)

    def add_entry(self, name):
        self.app.new(force=True)
        self.app.fields['name'].set(name)
        self.app.fields['password'].set('test secret')
        self.app.save()
        self.app.update()
        return self.app.selected

    def test_selection_search_and_discard(self):
        app = self.app
        first = self.add_entry('Zulu')
        second = self.add_entry('Alpha')
        self.assertEqual(app.tree.get_children(), (second, first))
        app.fields['name'].set('Unsaved')
        with patch('app.messagebox.askyesno', return_value=False) as prompt:
            app.tree.selection_set(first)
            app.update()
            self.assertEqual(app.selected, second)
            self.assertEqual(app.fields['name'].get(), 'Unsaved')
            app.new()
            app.lock()
            self.assertIsNotNone(app.vault)
            self.assertGreaterEqual(prompt.call_count, 3)
        with patch('app.messagebox.askyesno', return_value=True):
            app.tree.selection_set(first)
            app.update()
        self.assertEqual(app.fields['name'].get(), 'Zulu')
        app.search.set('no match')
        app.update()
        self.assertEqual(app.tree.get_children(), ())
        self.assertEqual(app.empty.get(), 'No matching passwords.')
        app.search.set('')
        app.update()
        self.assertEqual(app.tree.selection(), (first,))

    def test_failed_save_delete_and_idle_lock(self):
        app = self.app
        self.add_entry('Example')
        app.fields['name'].set('Edited')
        with patch.object(app.vault, 'save', side_effect=OSError('disk full')):
            with patch('app.messagebox.showerror') as error:
                app.save()
                error.assert_called_once()
        self.assertEqual(app.vault.entries[0]['name'], 'Example')
        with patch('app.messagebox.askyesno', return_value=True):
            app.delete()
        self.assertEqual(app.vault.entries, [])
        app.fields['password'].set('unsaved secret')
        app.last_active -= 301
        app.check_idle()
        self.assertIsNone(app.vault)
        self.assertTrue(all(not value.get() for value in app.fields.values()))

    def test_clipboard_and_generation(self):
        app = self.app
        app.generate()
        self.assertEqual(len(app.fields['password'].get()), 24)
        app.copy_password()
        self.assertEqual(app.clipboard_get(), app.fields['password'].get())
        app.clear_clipboard()
        self.assertIsNone(app.copied)
        app.copy_password()
        app.clipboard_clear()
        app.clipboard_append('unrelated text')
        app.clear_clipboard()
        self.assertEqual(app.clipboard_get(), 'unrelated text')
        app.clipboard_clear()


if __name__ == '__main__':
    unittest.main()

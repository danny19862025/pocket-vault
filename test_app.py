"""GUI regression test; run with a graphical display available."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from app import App


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires a graphical display')
class AppTests(unittest.TestCase):
    def test_create_save_lock_and_unlock(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CONFIG_HOME=directory):
            app = App()
            self.addCleanup(app.destroy)
            app.withdraw()
            with patch('app.messagebox.showerror') as error:
                app.update()
                self.assertIsNone(app.master)
                app.path.set(str(Path(directory) / 'passwords.vault'))
                app.choose(True)
                dialog = next(child for child in app.winfo_children() if child.winfo_class() == 'Toplevel')

                def button(root, text):
                    for child in root.winfo_children():
                        if child.winfo_class() == 'TButton' and child.cget('text') == text:
                            return child
                        found = button(child, text)
                        if found:
                            return found
                    return None

                with patch('app.simpledialog.askstring', return_value='My Vault'):
                    button(dialog, 'Create new folder…').invoke()
                button(dialog, 'Use this location').invoke()
                self.assertEqual(app.path.get(), str(Path(directory) / 'My Vault' / 'passwords.vault'))
                self.assertTrue((Path(directory) / 'My Vault').is_dir())
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

    def test_last_vault_survives_restart_and_picker_uses_its_folder(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CONFIG_HOME=directory):
            path = Path(directory) / 'my vaults' / 'personal.vault'
            app = App()
            app.withdraw()
            app.path.set(str(path))
            app.master_password.set('temporary master password')
            app.confirm.set('temporary master password')
            app.unlock(True)
            app.destroy()
            reopened = App()
            self.addCleanup(reopened.destroy)
            reopened.withdraw()
            self.assertEqual(reopened.path.get(), str(path))
            with patch('app.filedialog.askopenfilename', return_value='') as picker:
                reopened.choose(False)
            self.assertEqual(picker.call_args.kwargs['initialdir'], str(path.parent))
            self.assertEqual(picker.call_args.kwargs['initialfile'], path.name)
            self.assertEqual(reopened.path.get(), str(path))
            reopened.path.set(str(Path(directory) / 'wrong.vault'))
            with patch('app.messagebox.showerror'):
                reopened.unlock(False)
            reopened.login()
            self.assertEqual(reopened.path.get(), str(path))
            reopened.master_password.set('temporary master password')
            reopened.unlock(False)
            self.assertIsNotNone(reopened.vault)

@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires a graphical display')
class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        environment = patch.dict(os.environ, XDG_CONFIG_HOME=self.directory.name)
        environment.start()
        self.addCleanup(environment.stop)
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

    def import_dialog(self, text):
        path = Path(self.directory.name) / 'export.csv'
        path.write_text(text)
        with patch('app.filedialog.askopenfilename', return_value=str(path)):
            self.app.import_passwords()
        return next(child for child in self.app.winfo_children() if child.winfo_class() == 'Toplevel')

    def widgets(self, root):
        for child in root.winfo_children():
            yield child
            yield from self.widgets(child)

    def import_button(self, window):
        return next(widget for widget in self.widgets(window) if widget.winfo_class() == 'TButton' and widget.cget('text') == 'Import into vault')

    def test_import_preview_encrypts_on_confirmation_and_preserves_edits(self):
        app = self.app
        app.fields['name'].set('Unsaved edit')
        original = app.vault.path.read_bytes()
        dialog = self.import_dialog('name,username,password,url\nImported,alice,dummy imported secret,https://example.com\n')
        app.deiconify()
        app.update()
        self.assertLessEqual(dialog.winfo_reqheight(), dialog.winfo_height())
        self.assertEqual(app.vault.path.read_bytes(), original)
        tree = next(widget for widget in self.widgets(dialog) if widget.winfo_class() == 'Treeview')
        self.assertNotIn('dummy imported secret', str([tree.item(i) for i in tree.get_children()]))
        self.import_button(dialog).invoke()
        self.assertEqual(app.vault.entries[0]['password'], 'dummy imported secret')
        self.assertNotIn(b'dummy imported secret', app.vault.path.read_bytes())
        self.assertEqual(app.fields['name'].get(), 'Unsaved edit')
        # Reimporting exact matches does not create another entry.
        dialog = self.import_dialog('name,username,password,url\nImported,alice,dummy imported secret,https://example.com\n')
        self.assertTrue(self.import_button(dialog).instate(['disabled']))
        app.login()
        self.assertFalse(dialog.winfo_exists())
        app.master_password.set('temporary master password')
        app.unlock(False)
        self.assertEqual(app.vault.entries[0]['password'], 'dummy imported secret')

    def test_import_manual_column_mapping(self):
        dialog = self.import_dialog('Label,User ID,Credential,Address\nExample,alice,secret,https://example.com\n')
        self.assertTrue(self.import_button(dialog).instate(['disabled']))
        boxes = [widget for widget in self.widgets(dialog) if widget.winfo_class() == 'TCombobox']
        for widget, column in zip(boxes, ['Label', 'User ID', 'Credential', 'Address']):
            widget.set(column)
        self.assertFalse(self.import_button(dialog).instate(['disabled']))
        self.import_button(dialog).invoke()
        self.assertEqual(self.app.vault.entries[0]['name'], 'Example')
        self.assertEqual(self.app.vault.entries[0]['password'], 'secret')

    def test_import_cancel_and_failed_save_leave_vault_unchanged(self):
        app = self.app
        original = app.vault.path.read_bytes()
        dialog = self.import_dialog('name,password\nImported,secret\n')
        dialog.destroy()
        self.assertEqual(app.vault.path.read_bytes(), original)
        dialog = self.import_dialog('name,password\nImported,secret\n')
        with patch.object(app.vault, 'save', side_effect=OSError('disk full')), patch('app.messagebox.showerror') as error:
            self.import_button(dialog).invoke()
            error.assert_called_once()
        self.assertEqual(app.vault.entries, [])
        self.assertEqual(app.vault.path.read_bytes(), original)
        self.assertTrue(dialog.winfo_exists())

    def test_clipboard_and_generation(self):
        app = self.app
        app.deiconify()
        app.geometry('1000x720')
        app.update()
        editor = app.password_strength.master
        self.assertLessEqual(editor.winfo_reqheight(), editor.winfo_height())
        app.generate()
        original = app.fields['password'].get()
        self.assertEqual(app.password_widget.cget('show'), '•')
        app.password_field.button.invoke()
        self.assertEqual(app.password_widget.cget('show'), '')
        self.assertEqual(app.password_field.button.cget('text'), 'Hide')
        self.assertEqual(app.fields['password'].get(), original)
        app.password_field.button.invoke()
        self.assertEqual(app.password_widget.cget('show'), '•')
        self.assertEqual(app.password_field.button.cget('text'), 'Show')
        self.assertEqual(len(app.fields['password'].get()), 24)
        self.assertEqual(app.password_strength.score, 4)
        app.fields['password'].set('Password123!')
        self.assertEqual(app.password_strength.score, 1)
        self.assertIn('Very weak', app.password_strength.text.get())
        app.fields['password'].set('')
        self.assertEqual(app.password_strength.score, 0)
        app.generate()
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
        app.password_field.button.invoke()
        app.new(force=True)
        self.assertFalse(app.password_field.visible.get())
        self.assertEqual(app.password_widget.cget('show'), '•')
        self.assertEqual(app.password_field.button.cget('text'), 'Show')
        app.login()
        self.assertEqual(app.master_field.entry.cget('show'), '•')
        app.master_field.button.invoke()
        self.assertEqual(app.master_field.entry.cget('show'), '')
        app.confirm_field.button.invoke()
        self.assertEqual(app.confirm_field.entry.cget('show'), '')
        app.login()
        self.assertEqual(app.master_field.entry.cget('show'), '•')
        self.assertEqual(app.confirm_field.entry.cget('show'), '•')


if __name__ == '__main__':
    unittest.main()

@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires a graphical display')
class CloudInteractionTests(unittest.TestCase):
    def test_dialog_background_backup_and_offline_save(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CONFIG_HOME=directory):
            app = App()
            self.addCleanup(app.destroy)
            app.withdraw()
            app.path.set(str(Path(directory) / 'test.vault'))
            app.master_password.set('temporary master password')
            app.confirm.set('temporary master password')
            app.unlock(True)
            app.cloud.configure('drive:', 'Pocket Vault', app.vault.path, True)
            captured = []

            def upload(raw, remote, folder):
                captured.append(raw)
                return 'backup.vault'

            def settle():
                deadline = time.monotonic() + 3
                while app.cloud_busy and time.monotonic() < deadline:
                    app.update()
                    time.sleep(0.01)
                self.assertFalse(app.cloud_busy)

            with patch.object(app.cloud, 'remotes', return_value=['drive:']):
                app.deiconify()
                app.cloud_dialog()
                settle()
                app.update()
                self.assertLessEqual(app.cloud_window.winfo_reqheight(), app.cloud_window.winfo_height())
                with patch.object(app.cloud, 'connect_dropbox', return_value='pocket-vault-dropbox-test:') as connect:
                    frame = app.cloud_window.winfo_children()[0]
                    button = next(widget for row in frame.winfo_children() for widget in row.winfo_children()
                                  if widget.winfo_class() == 'TButton' and widget.cget('text') == 'Connect Dropbox…')
                    button.invoke()
                    settle()
                    connect.assert_called_once()
                    self.assertIn('Dropbox connected', app.cloud_notice.get())
                    accounts = next(widget for widget in frame.winfo_children() if widget.winfo_class() == 'TCombobox')
                    self.assertEqual(accounts.get(), 'pocket-vault-dropbox-test:')
                    self.assertIn('drive:', accounts.cget('values'))
                app.cloud_window.destroy()
            with patch.object(app.cloud, 'backup', side_effect=upload):
                app.fields['name'].set('Cloud test')
                app.fields['password'].set('dummy secret')
                app.save()
                settle()
            self.assertEqual(captured, [app.vault.original])
            self.assertNotIn(b'dummy secret', captured[0])
            self.assertIn('Encrypted backup saved', app.cloud_notice.get())
            with patch.object(app.cloud, 'backup', side_effect=ValueError('offline')), patch('app.messagebox.showerror') as error:
                app.fields['name'].set('Saved offline')
                app.save()
                settle()
                self.assertEqual(app.vault.entries[0]['name'], 'Saved offline')
                self.assertIn('local vault is safe', app.cloud_notice.get())
                error.assert_called_once()

    def test_queued_latest_save_survives_lock(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CONFIG_HOME=directory):
            app = App()
            self.addCleanup(app.destroy)
            app.withdraw()
            app.path.set(str(Path(directory) / 'test.vault'))
            app.master_password.set('temporary master password')
            app.confirm.set('temporary master password')
            app.unlock(True)
            app.cloud.configure('drive:', 'Pocket Vault', app.vault.path, True)
            app.cloud_busy = True
            app.fields['name'].set('Queued')
            app.fields['password'].set('dummy secret')
            app.save()
            raw = app.vault.original
            app.login()
            app.cloud_jobs.put(([], None, lambda value: None))
            with patch.object(app.cloud, 'backup', return_value='backup.vault') as upload:
                app.poll_cloud()
                deadline = time.monotonic() + 3
                while app.cloud_busy and time.monotonic() < deadline:
                    app.update()
                    time.sleep(0.01)
                upload.assert_called_once_with(raw, 'drive:', 'Pocket Vault')
                self.assertIsNone(app.vault)

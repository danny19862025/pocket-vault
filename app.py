"""Run with: python3 app.py"""
import os
from pathlib import Path
import secrets
import string
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import uuid

from vault import Vault


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Pocket Vault • Password Manager')
        self.geometry('1120x760')
        self.minsize(1000, 720)
        style = ttk.Style(self)
        style.theme_use('clam')
        self.configure(background='#f3f5fa')
        style.configure('.', font=('DejaVu Sans', 10), background='#f3f5fa', foreground='#18243b')
        style.configure('TFrame', background='#f3f5fa')
        style.configure('Card.TFrame', background='#ffffff')
        style.configure('TLabel', background='#f3f5fa')
        style.configure('Card.TLabel', background='#ffffff')
        style.configure('Muted.TLabel', foreground='#64748b')
        style.configure('Title.TLabel', font=('DejaVu Sans', 25, 'bold'))
        style.configure('Section.TLabel', font=('DejaVu Sans', 15, 'bold'), background='#ffffff')
        style.configure('TButton', padding=(14, 10), background='#e6eaf2', borderwidth=0)
        style.map('TButton', background=[('active', '#d9dfeb')])
        style.configure('Accent.TButton', background='#4359d4', foreground='white')
        style.map('Accent.TButton', background=[('active', '#3448b4')])
        style.configure('Danger.TButton', foreground='#b42338', background='#fff0f1')
        style.configure('TEntry', padding=8, fieldbackground='#ffffff', bordercolor='#dce2ec', lightcolor='#dce2ec', darkcolor='#dce2ec')
        style.configure('TCheckbutton', background='#ffffff', padding=4)
        style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', rowheight=46, borderwidth=0)
        style.configure('Treeview.Heading', background='#eaf0f7', foreground='#53627a', padding=12, relief='flat')
        style.map('Treeview', background=[('selected', '#e5eaff')], foreground=[('selected', '#273b9b')])
        self.vault = None
        self.copied = None
        self.last_active = time.monotonic()
        self.bind_all('<KeyPress>', self.activity)
        self.bind_all('<ButtonPress>', self.activity)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.idle_timer = self.after(1000, self.check_idle)
        self.login()
        self.bind('<Control-s>', lambda event: self.save() if self.vault else None)
        self.bind('<Control-n>', lambda event: self.new() if self.vault else None)

    def activity(self, event=None):
        self.last_active = time.monotonic()

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def login(self):
        self.clear_clipboard()
        self.vault = None
        if hasattr(self, 'fields'):
            for value in self.fields.values():
                value.set('')
        self.clear()
        frame = ttk.Frame(self, padding=(100, 32))
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Pocket Vault', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='A private home for your passwords. Encrypted on your device.', style='Muted.TLabel').pack(anchor='w', pady=(8, 30))
        default = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'pocket-vault/passwords.vault'
        self.path = tk.StringVar(value=getattr(self, 'last_path', str(default)))
        ttk.Label(frame, text='Encrypted vault file').pack(anchor='w')
        ttk.Entry(frame, textvariable=self.path).pack(fill='x', pady=8)
        row = ttk.Frame(frame)
        row.pack(fill='x')
        ttk.Button(row, text='Open existing file…', command=lambda: self.choose(False)).pack(side='left')
        ttk.Button(row, text='Choose new location…', command=lambda: self.choose(True)).pack(side='left', padx=8)
        ttk.Label(frame, text='For cloud sync, choose a folder managed by your cloud sync client.').pack(anchor='w', pady=15)
        ttk.Label(frame, text='Master password').pack(anchor='w')
        self.master_password = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.master_password, show='•')
        entry.pack(fill='x', pady=8)
        entry.bind('<Return>', lambda event: self.unlock(False))
        ttk.Label(frame, text='Confirm master password (new vault only)').pack(anchor='w')
        self.confirm = tk.StringVar()
        ttk.Entry(frame, textvariable=self.confirm, show='•').pack(fill='x', pady=8)
        row = ttk.Frame(frame)
        row.pack(anchor='w', pady=16)
        ttk.Button(row, text='Unlock vault', style='Accent.TButton', command=lambda: self.unlock(False)).pack(side='left')
        ttk.Button(row, text='Create new vault', command=lambda: self.unlock(True)).pack(side='left', padx=8)
        ttk.Label(frame, text='Keep your master password safe. It cannot be recovered.').pack(anchor='w')

    def choose(self, new):
        picker = filedialog.asksaveasfilename if new else filedialog.askopenfilename
        result = picker(defaultextension='.vault', filetypes=[('Encrypted vault', '*.vault'), ('All files', '*')])
        if result:
            self.path.set(result)

    def unlock(self, create):
        try:
            if not self.path.get().strip():
                raise ValueError('Choose a vault file.')
            if create and self.master_password.get() != self.confirm.get():
                raise ValueError('The master passwords do not match.')
            self.vault = Vault(self.path.get(), self.master_password.get(), create=create)
        except (OSError, ValueError) as error:
            messagebox.showerror('Cannot open vault', str(error))
            return
        self.last_path = self.path.get()
        self.master_password.set('')
        self.confirm.set('')
        self.activity()
        self.dashboard()

    def dashboard(self):
        self.clear()
        frame = ttk.Frame(self, padding=28)
        frame.pack(fill='both', expand=True)
        header = ttk.Frame(frame)
        header.pack(fill='x')
        ttk.Label(header, text='Pocket Vault', style='Title.TLabel').pack(side='left')
        ttk.Button(header, text='Lock vault', command=self.lock).pack(side='right')
        ttk.Label(frame, text='YOUR PASSWORDS  /  Encrypted locally • Auto-lock after 5 minutes', style='Muted.TLabel').pack(anchor='w', pady=(8, 24))
        content = ttk.Frame(frame)
        content.pack(fill='both', expand=True)
        content.columnconfigure(0, weight=1, uniform='panels')
        content.columnconfigure(1, weight=1, uniform='panels')
        content.rowconfigure(0, weight=1)
        library = ttk.Frame(content, style='Card.TFrame', padding=20)
        library.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
        top = ttk.Frame(library, style='Card.TFrame')
        top.pack(fill='x', pady=(0, 16))
        self.count = tk.StringVar(value='All passwords')
        ttk.Label(top, textvariable=self.count, style='Section.TLabel').pack(side='left')
        ttk.Button(top, text='+ New', command=self.new).pack(side='right')
        ttk.Label(library, text='Search service or username', style='Card.TLabel').pack(anchor='w', pady=(0, 6))
        self.search = tk.StringVar()
        ttk.Entry(library, textvariable=self.search).pack(fill='x', pady=(0, 16))
        self.search.trace_add('write', lambda *args: self.refresh())
        listing = ttk.Frame(library, style='Card.TFrame')
        listing.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(listing, columns=('username',), selectmode='browse')
        self.tree.heading('#0', text='Service')
        self.tree.heading('username', text='Username')
        self.tree.column('#0', width=140, minwidth=100)
        self.tree.column('username', width=160, minwidth=100)
        scroll = ttk.Scrollbar(listing, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(side='left', fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        self.empty = tk.StringVar()
        ttk.Label(library, textvariable=self.empty, style='Card.TLabel', wraplength=350).pack(anchor='w', pady=(12, 0))
        editor = ttk.Frame(content, padding=24, style='Card.TFrame')
        editor.grid(row=0, column=1, sticky='nsew')
        self.editor_title = tk.StringVar(value='New password')
        ttk.Label(editor, textvariable=self.editor_title, style='Section.TLabel').pack(anchor='w', pady=(0, 12))
        self.fields = {}
        for key, label in [('name', 'Service / title'), ('username', 'Username / email'), ('password', 'Password'), ('url', 'Website')]:
            ttk.Label(editor, text=label, style='Card.TLabel').pack(anchor='w', pady=(8, 4))
            self.fields[key] = tk.StringVar()
            widget = ttk.Entry(editor, textvariable=self.fields[key], show='•' if key == 'password' else '')
            widget.pack(fill='x')
            if key == 'name':
                self.name_widget = widget
            if key == 'password':
                self.password_widget = widget
        self.show_password = tk.BooleanVar(value=False)
        ttk.Checkbutton(editor, text='Show password', variable=self.show_password,
                        command=lambda: self.password_widget.configure(show='' if self.show_password.get() else '•')).pack(anchor='w', pady=8)
        row = ttk.Frame(editor, style='Card.TFrame')
        row.pack(fill='x')
        ttk.Button(row, text='Generate', command=self.generate).pack(side='left')
        ttk.Button(row, text='Copy password', command=self.copy_password).pack(side='left', padx=8)
        row = ttk.Frame(editor, style='Card.TFrame')
        row.pack(fill='x', pady=(16, 0))
        ttk.Button(row, text='Save password', command=self.save, style='Accent.TButton').pack(side='left')
        ttk.Button(row, text='Delete', command=self.delete, style='Danger.TButton').pack(side='right')
        self.status = tk.StringVar(value='Ready. Select a password or create your first entry.')
        ttk.Label(frame, textvariable=self.status, style='Muted.TLabel', wraplength=1000).pack(side='bottom', anchor='w', pady=(12, 0), before=content)
        self.selected = None
        self.baseline = self.values()
        for value in self.fields.values():
            value.trace_add('write', self.edited)
        self.refresh()

    def values(self):
        return {key: value.get() for key, value in self.fields.items()}

    def edited(self, *args):
        if self.values() != self.baseline:
            self.status.set('Unsaved changes • Save password to keep your edits.')

    def discard(self):
        return self.values() == self.baseline or messagebox.askyesno(
            'Discard unsaved changes?', 'Your edits have not been saved. Discard them?', parent=self)

    def lock(self):
        if self.discard():
            self.login()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        query = self.search.get().casefold()
        for entry in sorted(self.vault.entries, key=lambda e: e['name'].casefold()):
            if query in (entry['name'] + ' ' + entry['username']).casefold():
                self.tree.insert('', 'end', iid=entry['id'], text=entry['name'], values=(entry['username'],))

        visible = self.tree.get_children()
        self.count.set(f'Passwords · {len(self.vault.entries)}')
        self.empty.set('' if visible else ('No matching passwords.' if query else 'Your vault is ready. Click + New to add a password.'))
        if self.selected in visible:
            self.tree.selection_set(self.selected)

    def select(self, event=None):
        selected = self.tree.selection()
        if selected and selected[0] != self.selected:
            if not self.discard():
                self.tree.selection_remove(*selected)
                if self.selected and self.tree.exists(self.selected):
                    self.tree.selection_set(self.selected)
                return
            self.selected = selected[0]
            entry = next(e for e in self.vault.entries if e['id'] == self.selected)
            for key, value in self.fields.items():
                value.set(entry[key])
            self.baseline = self.values()
            self.editor_title.set('Password details')
            self.status.set('Ready to edit • Changes are saved when you click Save password.')
            self.show_password.set(False)
            self.password_widget.configure(show='•')

    def new(self, force=False):
        if not force and not self.discard():
            return
        self.selected = None
        self.tree.selection_remove(*self.tree.selection())
        for value in self.fields.values():
            value.set('')
        self.show_password.set(False)
        self.password_widget.configure(show='•')
        self.baseline = self.values()
        self.editor_title.set('New password')
        self.name_widget.focus_set()
        self.status.set('Enter a new password entry, then Save password.')

    def generate(self):
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*()-_+'
        self.fields['password'].set(''.join(secrets.choice(alphabet) for _ in range(24)))

    def save(self):
        entry = {key: value.get() for key, value in self.fields.items()}
        if not entry['name'].strip() or not entry['password']:
            messagebox.showerror('Missing details', 'Enter a service name and password.')
            return
        entry['id'] = self.selected or str(uuid.uuid4())
        entries = [e for e in self.vault.entries if e['id'] != entry['id']] + [entry]
        if self.persist(entries):
            self.selected = entry['id']
            self.baseline = self.values()
            self.editor_title.set('Password details')
            self.refresh()
            self.status.set('Saved encrypted vault.')

    def persist(self, entries):
        try:
            self.vault.save(entries)
            return True
        except (OSError, ValueError) as error:
            messagebox.showerror('Could not save', str(error))
            return False

    def delete(self):
        if self.selected and messagebox.askyesno('Delete entry?', 'Permanently delete the selected password entry?'):
            if self.persist([e for e in self.vault.entries if e['id'] != self.selected]):
                self.new(force=True)
                self.refresh()
                self.status.set('Entry deleted.')

    def copy_password(self):
        value = self.fields['password'].get()
        if value:
            self.clipboard_clear()
            self.clipboard_append(value)
            self.copied = value
            if hasattr(self, 'clipboard_timer'):
                self.after_cancel(self.clipboard_timer)
            self.clipboard_timer = self.after(20000, self.clear_clipboard)
            self.status.set('Copied. Clipboard clears in 20 seconds; clipboard history may retain it.')

    def clear_clipboard(self):
        if self.copied is not None:
            try:
                if self.clipboard_get() == self.copied:
                    self.clipboard_clear()
            except tk.TclError:
                pass
            self.copied = None

    def check_idle(self):
        self.after_cancel(self.idle_timer)
        if self.vault and time.monotonic() - self.last_active >= 300:
            self.login()
        self.idle_timer = self.after(1000, self.check_idle)

    def destroy(self):
        for timer in self.tk.splitlist(self.tk.call('after', 'info')):
            self.after_cancel(timer)
        super().destroy()

    def close(self):
        if self.vault and not self.discard():
            return
        self.clear_clipboard()
        self.destroy()


if __name__ == '__main__':
    App().mainloop()

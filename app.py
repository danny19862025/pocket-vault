"""Run with: python3 app.py"""
import os
import queue
import threading
from pathlib import Path
import secrets
import string
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import uuid

from version import VERSION
from theme import apply_theme
from vault import Vault
from cloud import Cloud
from preferences import last_vault, remember_vault
from password_field import PasswordField
from strength import StrengthMeter
from importing import load_export, prepare_entries, FIELDS


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Pocket Vault {VERSION} • Password Manager')
        self.geometry('1120x760')
        self.minsize(1000, 720)
        apply_theme(self)
        self.vault = None
        self.cloud = Cloud()
        self.cloud_jobs = queue.Queue()
        self.cloud_busy = False
        self.cloud_pending = None
        self.cloud_notice = tk.StringVar(value="Cloud backups are optional.")
        self.after(100, self.poll_cloud)
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
        shell = ttk.Frame(self, padding=28)
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, minsize=270)
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(0, weight=1)
        hero = ttk.Frame(shell, style='Hero.TFrame', padding=24)
        hero.grid(row=0, column=0, sticky='nsew', padx=(0, 24))
        ttk.Label(hero, text='Pocket', style='HeroTitle.TLabel').pack(anchor='w', pady=(14, 0))
        ttk.Label(hero, text='Vault', style='HeroAccent.TLabel').pack(anchor='w')
        emblem = tk.Canvas(hero, width=220, height=160, background='#102f3a', highlightthickness=0)
        emblem.pack(pady=(30, 22))
        emblem.create_oval(45, 10, 177, 142, fill='#164654', outline='')
        emblem.create_arc(79, 31, 143, 101, start=0, extent=180, style='arc', width=9, outline='#67d7e9')
        emblem.create_rectangle(75, 71, 147, 121, fill='#ff8a3d', outline='')
        emblem.create_oval(105, 85, 117, 97, fill='#102f3a', outline='')
        emblem.create_line(111, 93, 111, 107, fill='#102f3a', width=5, capstyle='round')
        ttk.Label(hero, text='Your passwords.\nYour space.', style='Hero.TLabel', wraplength=230).pack(anchor='w')
        ttk.Label(hero, text='Encrypted storage.\nOptional cloud backups.', style='Hero.TLabel', wraplength=230).pack(side='bottom', anchor='w', pady=(20, 12))
        frame = ttk.Frame(shell, style='Card.TFrame', padding=24)
        frame.grid(row=0, column=1, sticky='nsew')
        ttk.Label(frame, text='Unlock your vault', style='Section.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Choose your vault and enter your master password.', style='Card.TLabel').pack(anchor='w', pady=(6, 22))
        default = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'pocket-vault/passwords.vault'
        self.path = tk.StringVar(value=getattr(self, 'last_path', None) or last_vault() or str(default))
        ttk.Label(frame, style='Card.TLabel', text='Encrypted vault file').pack(anchor='w')
        ttk.Entry(frame, textvariable=self.path).pack(fill='x', pady=8)
        row = ttk.Frame(frame, style='Card.TFrame')
        row.pack(fill='x')
        ttk.Button(row, text='Open existing file…', command=lambda: self.choose(False)).pack(side='left')
        ttk.Button(row, text='Choose new location…', command=lambda: self.choose(True)).pack(side='left', padx=8)
        ttk.Button(row, text='Create folder…', command=self.create_folder).pack(side='left')
        ttk.Button(frame, text='Cloud storage • Google Drive & Dropbox…', command=self.cloud_dialog).pack(anchor='w', pady=15)
        ttk.Label(frame, style='Card.TLabel', text='Master password').pack(anchor='w')
        self.master_password = tk.StringVar()
        self.master_field = PasswordField(frame, self.master_password, card=True)
        self.master_field.pack(fill='x', pady=8)
        entry = self.master_field.entry
        entry.bind('<Return>', lambda event: self.unlock(False))
        self.master_strength = StrengthMeter(frame, self.master_password, card=True)
        self.master_strength.pack(fill='x', pady=(0, 8))
        confirmation_label = ttk.Frame(frame, style='Card.TFrame')
        confirmation_label.pack(anchor='w')
        ttk.Label(confirmation_label, text='Confirm master password', style='Card.TLabel').pack(side='left')
        ttk.Label(confirmation_label, text='(new vault only)', style='NewVault.TLabel').pack(side='left', padx=(8, 0))
        self.confirm = tk.StringVar()
        self.confirm_field = PasswordField(frame, self.confirm, card=True)
        self.confirm_field.pack(fill='x', pady=8)
        row = ttk.Frame(frame, style='Card.TFrame')
        row.pack(anchor='w', pady=16)
        ttk.Button(row, text='Unlock vault', style='Accent.TButton', command=lambda: self.unlock(False)).pack(side='left')
        ttk.Button(row, text='Create new vault', command=lambda: self.unlock(True)).pack(side='left', padx=8)
        ttk.Label(frame, style='Card.TLabel', text='Keep your master password safe. It cannot be recovered.').pack(anchor='w')

    def choose(self, new):
        if new:
            self.choose_new_location()
            return
        current = Path(self.path.get()).expanduser()
        folder = current.parent if current.parent.is_dir() else Path.home()
        result = filedialog.askopenfilename(parent=self, initialdir=str(folder), initialfile=current.name,
                                            defaultextension='.vault',
                                            filetypes=[('Encrypted vault', '*.vault'), ('All files', '*')])
        if result:
            self.path.set(result)

    def choose_new_location(self):
        window = tk.Toplevel(self)
        window.title('Choose new vault location')
        window.transient(self)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill='both', expand=True)
        current = Path(self.path.get()).expanduser()
        directory = tk.StringVar(value=str(current.parent if current.parent.is_dir() else Path.home()))
        filename = tk.StringVar(value=current.name or 'passwords.vault')
        ttk.Label(frame, text='Choose new location', style='Section.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Choose a folder or create a new one for your encrypted vault.').pack(anchor='w', pady=(8, 16))
        ttk.Label(frame, text='Folder').pack(anchor='w')
        ttk.Entry(frame, textvariable=directory, width=65).pack(fill='x', pady=8)

        def browse():
            result = filedialog.askdirectory(parent=window, title='Choose vault folder',
                                             initialdir=directory.get(), mustexist=True)
            if result:
                directory.set(result)

        def create():
            result = self.make_folder(directory.get(), window)
            if result:
                directory.set(str(result))

        row = ttk.Frame(frame)
        row.pack(anchor='w', pady=(0, 16))
        ttk.Button(row, text='Browse folders…', command=browse).pack(side='left')
        ttk.Button(row, text='Create new folder…', command=create).pack(side='left', padx=8)
        ttk.Label(frame, text='Vault filename').pack(anchor='w')
        entry = ttk.Entry(frame, textvariable=filename)
        entry.pack(fill='x', pady=8)

        def use_location():
            try:
                folder = Path(directory.get()).expanduser()
                name = filename.get().strip()
                if not folder.is_dir():
                    raise ValueError('Choose an existing folder or click Create new folder.')
                if not name or name in ('.', '..') or '/' in name or '\\' in name or '\x00' in name:
                    raise ValueError('Enter a filename without slashes, such as passwords.vault.')
                if not name.endswith('.vault'):
                    name += '.vault'
                target = folder / name
                if target.exists():
                    raise ValueError('A file already exists at that location. Choose a new filename, or use Open existing file.')
                self.path.set(str(target))
            except (OSError, ValueError) as error:
                messagebox.showerror('Cannot choose location', str(error), parent=window)
                return
            window.destroy()

        row = ttk.Frame(frame)
        row.pack(anchor='e', pady=(12, 0))
        ttk.Button(row, text='Cancel', command=window.destroy).pack(side='left')
        ttk.Button(row, text='Use this location', style='Accent.TButton', command=use_location).pack(side='left', padx=(8, 0))
        entry.bind('<Return>', lambda event: use_location())
        window.bind('<Escape>', lambda event: window.destroy())
        window.grab_set()
        entry.focus_set()

    def make_folder(self, parent, window):
        name = simpledialog.askstring('Create vault folder', 'New folder name:', parent=window)
        if name is None:
            return None
        name = name.strip()
        try:
            if not name or name in ('.', '..') or '/' in name or '\\' in name or '\x00' in name:
                raise ValueError('Enter a folder name without slashes, such as My Vault.')
            folder = Path(parent).expanduser() / name
            folder.mkdir(mode=0o700)
            return folder
        except FileExistsError:
            messagebox.showerror('Cannot create folder', 'A folder or file with that name already exists. Choose another name.', parent=window)
        except (OSError, ValueError) as error:
            messagebox.showerror('Cannot create folder', str(error), parent=window)
        return None

    def create_folder(self):
        current = Path(self.path.get()).expanduser().parent
        parent = filedialog.askdirectory(parent=self, title='Choose where to create your vault folder',
                                         initialdir=str(current if current.is_dir() else Path.home()),
                                         mustexist=True)
        if not parent:
            return
        folder = self.make_folder(parent, self)
        if folder:
            self.path.set(str(folder / 'passwords.vault'))
            messagebox.showinfo('Folder created', 'Vault location selected. Enter and confirm your master password, then click Create new vault.', parent=self)

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
        self.last_path = str(self.vault.path.absolute())
        self.master_password.set('')
        self.confirm.set('')
        self.activity()
        self.dashboard()
        try:
            remember_vault(self.last_path)
        except OSError:
            messagebox.showwarning('Vault location not remembered',
                                   'Your vault is open, but its location could not be saved for next time.', parent=self)

    def dashboard(self):
        self.clear()
        frame = ttk.Frame(self, padding=28)
        frame.pack(fill='both', expand=True)
        header = ttk.Frame(frame)
        header.pack(fill='x')
        ttk.Label(header, text='Pocket Vault', style='Title.TLabel').pack(side='left')
        ttk.Button(header, text='Lock vault', command=self.lock).pack(side='right')
        ttk.Button(header, text='Cloud storage…', command=self.cloud_dialog).pack(side='right', padx=8)
        ttk.Button(header, text='Import passwords…', command=self.import_passwords).pack(side='right')
        ttk.Label(frame, text='YOUR PASSWORDS  /  Encrypted locally • Auto-lock after 5 minutes', style='Eyebrow.TLabel').pack(anchor='w', pady=(8, 12))
        ttk.Separator(frame, style='Brand.TSeparator').pack(fill='x', pady=(0, 12))
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
        editor = ttk.Frame(content, padding=(24, 12), style='Card.TFrame')
        editor.grid(row=0, column=1, sticky='nsew')
        self.editor_title = tk.StringVar(value='New password')
        ttk.Label(editor, textvariable=self.editor_title, style='Section.TLabel').pack(anchor='w', pady=(0, 12))
        self.fields = {}
        for key, label in [('name', 'Service / title'), ('username', 'Username / email'), ('password', 'Password'), ('url', 'Website')]:
            ttk.Label(editor, text=label, style='Card.TLabel').pack(anchor='w', pady=(8, 4))
            self.fields[key] = tk.StringVar()
            if key == 'password':
                self.password_field = PasswordField(editor, self.fields[key], card=True)
                self.password_field.pack(fill='x')
                self.password_widget = self.password_field.entry
                self.show_password = self.password_field.visible
                self.password_strength = StrengthMeter(editor, self.fields[key], card=True)
                self.password_strength.pack(fill='x', pady=(6, 8))
            else:
                widget = ttk.Entry(editor, textvariable=self.fields[key])
                widget.pack(fill='x')
                if key == 'name':
                    self.name_widget = widget
        row = ttk.Frame(editor, style='Card.TFrame')
        row.pack(fill='x')
        ttk.Button(row, text='Generate', command=self.generate).pack(side='left')
        ttk.Button(row, text='Copy password', command=self.copy_password).pack(side='left', padx=8)
        row = ttk.Frame(editor, style='Card.TFrame')
        row.pack(fill='x', pady=(12, 0))
        ttk.Button(row, text='Save password', command=self.save, style='Accent.TButton').pack(side='left')
        ttk.Button(row, text='Delete', command=self.delete, style='Danger.TButton').pack(side='right')
        self.status = tk.StringVar(value='Ready. Select a password or create your first entry.')
        ttk.Label(frame, textvariable=self.status, style='Muted.TLabel', wraplength=1000).pack(side='bottom', anchor='w', pady=(12, 0), before=content)
        ttk.Label(frame, textvariable=self.cloud_notice, style='Muted.TLabel', wraplength=1000).pack(side='bottom', anchor='w', before=content)
        self.selected = None
        self.baseline = self.values()
        for value in self.fields.values():
            value.trace_add('write', self.edited)
        self.refresh()

    def import_passwords(self):
        if not self.vault:
            return
        source_vault = self.vault
        downloads = Path.home() / 'Downloads'
        path = filedialog.askopenfilename(parent=self, title='Import an export from another password manager',
                                         initialdir=str(downloads if downloads.is_dir() else Path.home()),
                                         initialfile='',
                                         filetypes=[('Password exports', '*.csv *.tsv *.json *.txt'),
                                                    ('CSV files', '*.csv'), ('JSON files', '*.json'), ('All files', '*')])
        if not path or self.vault is not source_vault:
            return
        try:
            data = load_export(path)
        except (OSError, ValueError) as error:
            messagebox.showerror('Cannot import passwords', str(error), parent=self)
            return
        window = tk.Toplevel(self)
        window.title('Pocket Vault • Import passwords')
        window.geometry('840x650')
        window.minsize(760, 620)
        window.transient(self)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Import passwords', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Match the export columns below, then review the logins before importing.', wraplength=780).pack(anchor='w', pady=(8, 12))
        grid = ttk.Frame(frame)
        grid.pack(fill='x')
        mapping = {}
        for index, (field, label) in enumerate(zip(FIELDS, ('Service / title', 'Username / email', 'Password (required)', 'Website'))):
            cell = ttk.Frame(grid, padding=(0, 0, 12, 8))
            cell.grid(row=index // 2, column=index % 2, sticky='ew')
            grid.columnconfigure(index % 2, weight=1)
            ttk.Label(cell, text=label).pack(anchor='w')
            mapping[field] = tk.StringVar(value=data.mapping()[field])
            ttk.Combobox(cell, textvariable=mapping[field], values=['', *data.columns], state='readonly').pack(fill='x', pady=4)
        summary = tk.StringVar()
        ttk.Label(frame, textvariable=summary, wraplength=780).pack(anchor='w', pady=(4, 8))
        listing = ttk.Frame(frame)
        listing.pack(fill='both', expand=True)
        tree = ttk.Treeview(listing, columns=('name', 'username', 'url'), show='headings', height=3)
        for field, label in [('name', 'Service'), ('username', 'Username'), ('url', 'Website')]:
            tree.heading(field, text=label)
            tree.column(field, width=230, minwidth=90)
        scroll = ttk.Scrollbar(listing, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(fill='both', expand=True)
        ttk.Label(frame, text='Passwords stay hidden in this preview. Exact duplicates are skipped.\nExisting entries are kept. Only service, username, password, and website are imported;\nnotes, TOTP, attachments, and passkeys are not imported.', wraplength=780, style='Muted.TLabel').pack(anchor='w', pady=10)
        ttk.Label(frame, text='Your export file may contain readable passwords. Remove it after verifying the import.', wraplength=780).pack(anchor='w', pady=(0, 8))
        actions = ttk.Frame(frame)
        actions.pack(fill='x')
        ttk.Button(actions, text='Cancel', command=window.destroy).pack(side='right')
        candidates = []

        def preview(*args):
            nonlocal candidates
            candidates = []
            tree.delete(*tree.get_children())
            if self.vault is not source_vault:
                window.destroy()
                return
            try:
                candidates, skipped, duplicates = prepare_entries(data, {field: value.get() for field, value in mapping.items()}, source_vault.entries)
            except ValueError as error:
                summary.set(str(error))
                confirm.state(['disabled'])
                return
            summary.set(f'{len(candidates)} logins to import • {duplicates} exact duplicates • {skipped} incomplete or non-login items skipped. Showing up to 100 logins.')
            confirm.state(['!disabled'] if candidates else ['disabled'])
            for entry in candidates[:100]:
                tree.insert('', 'end', values=(entry['name'], entry['username'], entry['url']))

        def commit():
            if self.vault is not source_vault:
                window.destroy()
                return
            preview()
            if candidates and self.persist(source_vault.entries + candidates):
                count = len(candidates)
                self.refresh()
                notice = f'Imported {count} passwords into your encrypted vault.'
                if self.values() != self.baseline:
                    notice += ' Your editor still has unsaved changes.'
                self.status.set(notice)
                window.destroy()

        confirm = ttk.Button(actions, text='Import into vault', style='Accent.TButton', command=commit)
        confirm.pack(side='right', padx=8)
        traces = [(variable, variable.trace_add('write', preview)) for variable in mapping.values()]

        def release(event):
            if event.widget is window:
                data.rows.clear()
                candidates.clear()
                for variable, trace in traces:
                    variable.trace_remove('write', trace)

        window.bind('<Destroy>', release)
        preview()
        window.bind('<Escape>', lambda event: window.destroy())
        window.grab_set()

    def cloud_task(self, operation, complete):
        if self.cloud_busy:
            messagebox.showinfo('Cloud storage', 'A cloud operation is already running.', parent=self)
            return False
        self.cloud_busy = True
        self.cloud_notice.set('Working… You can keep using your vault.')

        def worker():
            try:
                result = operation()
            except Exception as error:
                self.cloud_jobs.put((None, str(error), complete))
            else:
                self.cloud_jobs.put((result, None, complete))

        threading.Thread(target=worker, daemon=True).start()
        return True

    def poll_cloud(self):
        try:
            result, error, complete = self.cloud_jobs.get_nowait()
        except queue.Empty:
            pass
        else:
            self.cloud_busy = False
            if error:
                self.cloud_notice.set('Cloud failed • ' + error + ' Your local vault is safe.')
                messagebox.showerror('Cloud storage', self.cloud_notice.get(), parent=self)
            else:
                complete(result)
            if self.cloud_pending is not None:
                raw, remote, folder = self.cloud_pending
                self.cloud_pending = None
                self.start_backup(raw, remote, folder)
        self.after(100, self.poll_cloud)

    def start_backup(self, raw, remote, folder):
        return self.cloud_task(lambda: self.cloud.backup(raw, remote, folder),
                               lambda name: self.cloud_notice.set('Encrypted backup saved to ' + remote + folder + '.'))

    def auto_backup(self):
        if self.cloud.automatic(self.vault.path):
            settings = self.cloud.settings
            job = (self.vault.original, settings.get('remote', ''), settings.get('folder', 'Pocket Vault'))
            if self.cloud_busy:
                self.cloud_pending = job
                self.cloud_notice.set('Latest local save is queued for cloud backup.')
            else:
                self.start_backup(*job)

    def cloud_dialog(self):
        if hasattr(self, 'cloud_window') and self.cloud_window.winfo_exists():
            self.cloud_window.lift()
            return
        window = self.cloud_window = tk.Toplevel(self)
        window.title('Pocket Vault • Cloud storage')
        window.geometry('720x700')
        window.minsize(680, 690)
        window.transient(self)
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Cloud storage', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Back up your encrypted vault to Google Drive, Dropbox, or another connected cloud.\nYour master password stays on this device.', wraplength=620).pack(anchor='w', pady=(8, 16))
        remote = tk.StringVar(value=self.cloud.settings.get('remote', ''))
        folder = tk.StringVar(value=self.cloud.settings.get('folder', 'Pocket Vault'))
        automatic = tk.BooleanVar(value=bool(self.vault and self.cloud.automatic(self.vault.path)))
        ttk.Label(frame, text='Connected cloud account').pack(anchor='w')
        accounts = ttk.Combobox(frame, textvariable=remote, state='readonly')
        accounts.pack(fill='x', pady=8)

        def loaded(names):
            if window.winfo_exists():
                accounts.configure(values=names)
                if not remote.get() and names:
                    remote.set(names[0])
            self.cloud_notice.set('Choose an account, or connect Google Drive or Dropbox.')

        def refresh_accounts():
            self.cloud_task(self.cloud.remotes, loaded)

        def connected(name, provider):
            if window.winfo_exists():
                names = list(accounts.cget('values'))
                if name not in names:
                    names.append(name)
                accounts.configure(values=names)
                remote.set(name)
            self.cloud_notice.set(provider + ' connected. Save these options to use it.')

        row = ttk.Frame(frame)
        row.pack(anchor='w')
        ttk.Button(row, text='Connect Google Drive…', command=lambda: self.cloud_task(self.cloud.connect_drive, lambda name: connected(name, 'Google Drive'))).pack(side='left')
        ttk.Button(row, text='Connect Dropbox…', command=lambda: self.cloud_task(self.cloud.connect_dropbox, lambda name: connected(name, 'Dropbox'))).pack(side='left', padx=8)
        ttk.Button(row, text='Refresh accounts', command=refresh_accounts).pack(side='left')
        ttk.Label(frame, text='Connect opens the provider’s sign-in page in your browser. Existing rclone\naccounts (including OneDrive) appear after Refresh accounts.', wraplength=620, style='Muted.TLabel').pack(anchor='w', pady=10)
        ttk.Label(frame, text='Folder in your cloud account').pack(anchor='w')
        ttk.Entry(frame, textvariable=folder).pack(fill='x', pady=8)
        check = ttk.Checkbutton(frame, text='Back up this vault after every saved change', variable=automatic)
        check.pack(anchor='w')
        if not self.vault:
            check.state(['disabled'])

        def configure():
            try:
                self.cloud.configure(remote.get(), folder.get(), self.vault.path if self.vault else None, automatic.get())
                if not automatic.get():
                    self.cloud_pending = None
            except (OSError, ValueError) as error:
                messagebox.showerror('Cloud storage', str(error), parent=window)
                return False
            self.cloud_notice.set('Cloud options saved.')
            return True

        def backup_now():
            if not self.vault:
                messagebox.showinfo('Unlock your vault', 'Unlock a vault first to back it up.', parent=window)
                return
            if configure():
                self.start_backup(self.vault.original, remote.get(), folder.get())

        row = ttk.Frame(frame)
        row.pack(anchor='w', pady=12)
        ttk.Button(row, text='Save options', command=configure).pack(side='left')
        ttk.Button(row, text='Back up now', command=backup_now, style='Accent.TButton').pack(side='left', padx=8)
        ttk.Label(frame, text='Restore an encrypted backup (lock your vault first)').pack(anchor='w', pady=(6, 0))
        backup_name = tk.StringVar()
        backups = ttk.Combobox(frame, textvariable=backup_name, state='readonly')
        backups.pack(fill='x', pady=8)

        def show_backups(names):
            if window.winfo_exists():
                backups.configure(values=names)
                backup_name.set(names[0] if names else '')
            self.cloud_notice.set('Newest backups appear first.' if names else 'No backups found in this folder.')

        def list_backups():
            account, directory = remote.get(), folder.get()
            self.cloud_task(lambda: self.cloud.backups(account, directory), show_backups)

        def restored(path):
            if not self.vault:
                self.path.set(path)
            self.cloud_notice.set('Backup restored. Open the restored file with its master password.')

        def restore():
            if self.vault:
                messagebox.showinfo('Lock your vault first', 'Lock the current vault before restoring a backup.', parent=window)
                return
            if not backup_name.get():
                messagebox.showinfo('Select a backup', 'Click List backups and choose a backup.', parent=window)
                return
            target = filedialog.asksaveasfilename(parent=window, title='Restore to a NEW local vault file',
                                                  initialfile='restored.vault', defaultextension='.vault',
                                                  filetypes=[('Encrypted vault', '*.vault')])
            if target:
                account, directory, name = remote.get(), folder.get(), backup_name.get()
                self.cloud_task(lambda: self.cloud.restore(account, directory, name, target), restored)

        row = ttk.Frame(frame)
        row.pack(anchor='w')
        ttk.Button(row, text='List backups', command=list_backups).pack(side='left')
        ttk.Button(row, text='Restore to new file…', command=restore).pack(side='left', padx=8)
        ttk.Label(frame, textvariable=self.cloud_notice, wraplength=620, style='Muted.TLabel').pack(anchor='w', pady=12)
        ttk.Label(frame, text='Each backup is a separate version. Unsaved edits are not included.\nThis is backup and restore; edit on one device at a time.', wraplength=620).pack(anchor='w')
        refresh_accounts()

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
            self.password_field.set_visible(False)

    def new(self, force=False):
        if not force and not self.discard():
            return
        self.selected = None
        self.tree.selection_remove(*self.tree.selection())
        for value in self.fields.values():
            value.set('')
        self.password_field.set_visible(False)
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
            self.auto_backup()
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
        if self.cloud_busy or self.cloud_pending is not None:
            messagebox.showinfo('Cloud operation running', 'Wait for the cloud operation to finish before closing Pocket Vault.', parent=self)
            return
        if self.vault and not self.discard():
            return
        self.clear_clipboard()
        self.destroy()


if __name__ == '__main__':
    App().mainloop()

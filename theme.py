"""ArchEasy-inspired appearance, rounded controls and saved per-app preferences."""
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

FIELDS = ('Background', 'Surfaces', 'Text', 'Secondary text', 'Accent', 'Borders')
DARK = ('#101722', '#1b2738', '#e7eef8', '#aebdd0', '#55cbb6', '#537586')
LIGHT = ('#f6f8fb', '#ffffff', '#202b3b', '#596b80', '#1793d1', '#cdd7e3')


def blend(a, b, fraction):
    return '#' + ''.join(f'{round(int(a[i:i+2], 16) * (1-fraction) + int(b[i:i+2], 16) * fraction):02x}' for i in (1, 3, 5))


def valid_palette(value):
    return isinstance(value, (list, tuple)) and len(value) == 6 and all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in value)


def desktop_setting(schema, key):
    try:
        return subprocess.run(['gsettings', 'get', schema, key], capture_output=True, text=True, timeout=0.5, check=False).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ''


class Appearance:
    def __init__(self, root):
        self.root = root
        self.path = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'pocket-vault/appearance.json'
        try:
            settings = json.loads(self.path.read_text())
            if not isinstance(settings, dict):
                settings = {}
        except (OSError, ValueError):
            settings = {}
        self.custom = settings.get('custom', list(DARK))
        custom_valid = valid_palette(self.custom)
        if not custom_valid:
            self.custom = list(DARK)
        mode = settings.get('theme', 'System')
        self.mode = tk.StringVar(root, value=mode if mode in ('System', 'Light', 'Dark', 'Custom') and (mode != 'Custom' or custom_valid) else 'System')
        self.system_dark = 'dark' in desktop_setting('org.gnome.desktop.interface', 'color-scheme').lower()
        if not self.system_dark:
            self.system_dark = 'dark' in desktop_setting('org.gnome.desktop.interface', 'gtk-theme').lower()
        motion = desktop_setting('org.gnome.desktop.interface', 'enable-animations') != 'false'
        self.motion = tk.BooleanVar(root, value=settings.get('animations', True) is not False and motion)
        self.style = ttk.Style(root)
        self.style.theme_use('clam')
        self.images = []
        self.hover_images = {}
        self.apply()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.appearance-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(dict(theme=self.mode.get(), custom=self.custom, animations=self.motion.get()), stream)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def changed(self, *args):
        try:
            self.save()
        except OSError:
            messagebox.showerror('Appearance', 'Could not save appearance preferences.', parent=self.root)
        self.apply()
        if not self.motion.get() and hasattr(self.root, 'intro'):
            self.root.intro.finish()

    def controls(self, parent):
        bar = ttk.Frame(parent, padding=(28, 8))
        bar.pack(fill='x')
        ttk.Label(bar, text='KeyKite', style='Eyebrow.TLabel').pack(side='left')
        ttk.Checkbutton(bar, text='Animations', variable=self.motion, command=self.changed).pack(side='right', padx=(14, 0))
        Button(bar, text='Colours…', command=self.edit).pack(side='right', padx=8)
        picker = ttk.Combobox(bar, values=('System', 'Light', 'Dark', 'Custom'), textvariable=self.mode, state='readonly', width=9)
        picker.pack(side='right')
        picker.bind('<<ComboboxSelected>>', self.changed)
        ttk.Label(bar, text='Theme').pack(side='right', padx=8)

    def apply(self):
        mode = self.mode.get()
        self.palette = tuple(self.custom) if mode == 'Custom' else DARK if mode == 'Dark' or (mode == 'System' and self.system_dark) else LIGHT
        bg, surface, text, muted, accent, border = self.palette
        s = self.style
        self.root.configure(background=bg)
        s.configure('.', font=('DejaVu Sans', 10), background=bg, foreground=text)
        for name in ('TFrame', 'TLabel'):
            s.configure(name, background=bg, foreground=text)
        for name in ('Card.TFrame', 'Card.TLabel', 'Section.TLabel', 'TCheckbutton'):
            s.configure(name, background=surface, foreground=text)
        s.map('TCheckbutton', background=[('active', surface)])
        s.configure('Section.TLabel', font=('DejaVu Sans', 14, 'bold'))
        s.configure('Title.TLabel', font=('DejaVu Sans', 25, 'bold'), foreground=text)
        s.configure('Muted.TLabel', foreground=muted)
        s.configure('Eyebrow.TLabel', foreground=accent, font=('DejaVu Sans', 9, 'bold'))
        for name in ('Hero.TFrame', 'Hero.TLabel', 'HeroTitle.TLabel', 'HeroAccent.TLabel'):
            s.configure(name, background=surface, foreground=muted)
        s.configure('HeroTitle.TLabel', foreground=text, font=('DejaVu Sans', 28, 'bold'))
        s.configure('HeroAccent.TLabel', foreground=accent, font=('DejaVu Sans', 28, 'bold'))
        s.configure('Hero.TLabel', font=('DejaVu Sans', 11))
        s.configure('NewVault.TLabel', background=blend(surface, accent, .15), foreground=text, font=('DejaVu Sans', 9, 'bold'), padding=(6, 2))
        s.configure('TEntry', padding=8, fieldbackground=surface, foreground=text, insertcolor=text, bordercolor=border, lightcolor=border, darkcolor=border)
        s.map('TEntry', bordercolor=[('focus', accent)], lightcolor=[('focus', accent)], darkcolor=[('focus', accent)])
        s.configure('TCombobox', padding=7, fieldbackground=surface, background=surface, foreground=text, arrowcolor=accent, bordercolor=border)
        s.map('TCombobox', fieldbackground=[('readonly', surface)], foreground=[('readonly', text)], selectbackground=[('readonly', surface)], selectforeground=[('readonly', text)])
        popup_colors = {
            'background': surface, 'foreground': text,
            'selectBackground': blend(surface, accent, .28),
            'selectForeground': text,
        }
        for option, color in popup_colors.items():
            self.root.option_add(f'*TCombobox*Listbox.{option}', color)
        s.configure('Treeview', background=surface, fieldbackground=surface, foreground=text, rowheight=46, borderwidth=0)
        s.configure('Treeview.Heading', background=blend(surface, accent, .1), foreground=text, font=('DejaVu Sans', 9, 'bold'), padding=12, relief='flat')
        s.map('Treeview', background=[('selected', blend(surface, accent, .28))], foreground=[('selected', text)])
        s.map('Treeview.Heading', background=[('active', blend(surface, accent, .2))])
        s.configure('Vertical.TScrollbar', background=border, troughcolor=bg, borderwidth=0, arrowsize=12)
        s.configure('Brand.TSeparator', background=accent)
        self.buttons()
        def notify(widget):
            if isinstance(widget, ttk.Combobox):
                # Tk caches the dropdown after its first opening. Option database
                # changes only affect new listboxes, so recolour existing ones too.
                listbox = f'{widget}.popdown.f.l'
                if self.root.tk.call('winfo', 'exists', listbox):
                    options = [item for option, color in popup_colors.items()
                               for item in (f'-{option.lower()}', color)]
                    self.root.tk.call(listbox, 'configure', *options)
            widget.event_generate('<<AppearanceChanged>>')
            for child in widget.winfo_children():
                notify(child)
        notify(self.root)

    def buttons(self):
        bg, surface, text, muted, accent, border = self.palette
        for name, fill, ink in [('TButton', surface, text), ('Accent.TButton', accent, '#08151e' if sum(int(accent[i:i+2],16) for i in (1,3,5)) > 380 else '#ffffff'), ('Danger.TButton', blend(surface, '#e05264', .12), '#e05264'), ('Eye.TButton', surface, text)]:
            self.style.configure(name, padding=(14, 9), foreground=ink, background=bg, font=('DejaVu Sans', 10, 'bold'), anchor='center')
            self.style.map(name, foreground=[('disabled', muted)])
            frames = [self.rounded(fill, border, 0), self.rounded(blend(fill, accent, .18), accent, .5), self.rounded(blend(fill, '#000000', .15), accent, .8), self.rounded(fill, accent, .8), self.rounded(blend(fill, bg, .65), blend(border, bg, .6), 0)]
            element = 'KeyKite.' + name
            if element not in self.style.element_names():
                self.style.element_create(element, 'image', frames[0], ('disabled', frames[4]), ('pressed', frames[2]), ('active', frames[1]), ('focus', frames[3]), border=14, padding=0, sticky='nsew')
                self.style.layout(name, [(element, {'sticky': 'nsew', 'children': [('Button.padding', {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})]})])
                self.images.extend(frames)
            else:
                # Elements retain their image names: update pixels rather than recreating elements.
                offset = ('TButton', 'Accent.TButton', 'Danger.TButton', 'Eye.TButton').index(name) * 5
                for old, new in zip(self.images[offset:offset+5], frames):
                    self.root.tk.call(str(old), 'copy', str(new))

            for step in range(1, 7):
                variant = f'Hover{step}.{name}'
                image = self.rounded(blend(fill, accent, .18*step/6), blend(border, accent, step/6), .5*step/6)
                if variant in self.hover_images:
                    self.root.tk.call(str(self.hover_images[variant]), 'copy', str(image))
                else:
                    self.hover_images[variant] = image
                    hover_element = 'KeyKite.' + variant
                    self.style.element_create(hover_element, 'image', image, ('disabled', frames[4]), ('pressed', frames[2]), ('focus', frames[3]), border=14, padding=0, sticky='nsew')
                    self.style.layout(variant, [(hover_element, {'sticky': 'nsew', 'children': [('Button.padding', {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})]})])

    def rounded(self, fill, edge, glow):
        image = tk.PhotoImage(master=self.root, width=32, height=32)
        bg = self.palette[0]
        for y in range(32):
            row = []
            for x in range(32):
                dx, dy = max(11-x, 0, x-20), max(11-y, 0, y-20)
                distance = math.hypot(dx, dy)
                if distance > 11:
                    color = blend(bg, edge, max(0, (14-distance)/14) * glow)
                elif distance > 9.5:
                    color = edge
                else:
                    color = blend(fill, '#ffffff', max(0, (14-y)/14) * .035)
                row.append(color)
            image.put('{' + ' '.join(row) + '}', to=(0, y))
        return image

    def edit(self):
        window = tk.Toplevel(self.root)
        window.title('Customize KeyKite theme')
        window.configure(background=self.palette[0])
        window.transient(self.root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Customize your colours', style='Title.TLabel').grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 12))
        values = [tk.StringVar(window, value=c) for c in self.custom]
        def pick(index):
            color = colorchooser.askcolor(values[index].get() if re.fullmatch(r'#[0-9a-fA-F]{6}', values[index].get()) else DARK[index], parent=window)[1]
            if color:
                values[index].set(color)
        for i, (label, value) in enumerate(zip(FIELDS, values)):
            ttk.Label(frame, text=label).grid(row=i+1, column=0, sticky='w', padx=(0, 24), pady=6)
            ttk.Entry(frame, textvariable=value, width=12).grid(row=i+1, column=1, padx=8)
            Button(frame, text='Choose…', command=lambda i=i: pick(i)).grid(row=i+1, column=2)
        def apply():
            colors = [v.get() for v in values]
            if not valid_palette(colors):
                messagebox.showerror('Invalid colour', 'Enter each colour as #RRGGBB.', parent=window)
                return
            self.custom = colors
            self.mode.set('Custom')
            self.changed()
            window.destroy()
        actions = ttk.Frame(frame)
        actions.grid(row=8, column=0, columnspan=3, pady=(20, 0))
        Button(actions, text='Reset colours', command=lambda: [v.set(c) for v, c in zip(values, DARK)]).pack(side='left')
        Button(actions, text='Cancel', command=window.destroy).pack(side='left', padx=10)
        Button(actions, text='Apply theme', command=apply, style='Accent.TButton').pack(side='left')


def apply_theme(root):
    root.appearance = Appearance(root)
    return root.appearance.style


class OpeningAnimation:
    """1.8-second scale, blue rings and wordmark reveal, skippable like ArchEasy."""
    def __init__(self, root):
        self.root = root
        self.timer = None
        self.canvas = tk.Canvas(root, background='#090e17', highlightthickness=0, takefocus=True)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.bind('<Button-1>', self.finish)
        self.canvas.bind('<Escape>', self.finish)
        self.canvas.focus_set()
        self.start = time.monotonic()
        self.tick()

    def finish(self, event=None):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.canvas.winfo_exists():
            self.canvas.destroy()
            self.root.focus_set()
        return 'break'

    def tick(self):
        if not self.canvas.winfo_exists():
            return
        t = time.monotonic() - self.start
        if t >= 1.8:
            self.finish()
            return
        c = self.canvas
        c.delete('all')
        width, height = c.winfo_width(), c.winfo_height()
        x, y = width/2, height/2-55
        ease = 1 - (1-min(1, t/.8))**3
        fade = max(0, min(1, (1.8-t)/.45))
        bg = blend(self.root.appearance.palette[0], '#090e17', fade)
        c.configure(background=bg)
        def color(value, alpha=1):
            return blend(bg, value, alpha * fade)
        for radius in range(290, 5, -10):
            c.create_oval(x-radius, y-radius, x+radius, y+radius, fill=color('#1793d1', .22*ease*(1-radius/300)**2), outline='')
        for offset in (0, .32):
            pulse = max(0, min(1, (t-offset)/1.5))
            r = 105 + pulse*145
            c.create_oval(x-r, y-r, x+r, y+r, outline=color('#55b9ed', ease*(1-pulse)*.55), width=2)
        size = 100*(.72+.28*ease)
        y += (1-ease)*22
        c.create_polygon(x, y-size, x+size*.75, y, x, y+size, x-size*.75, y, fill=color('#1793d1', ease), outline=color('#72d5ed', ease), width=2)
        c.create_line(x-size*.75, y, x+size*.75, y, fill=color('#a2e4f2', ease), width=2)
        c.create_line(x, y-size, x, y+size, fill=color('#a2e4f2', ease), width=2)
        c.create_line(x, y+size, x+18, y+size+24, x-4, y+size+42, fill=color('#55cbb6', ease), smooth=True, width=3)
        reveal = min(1, max(0, (t-.25)/.5))
        c.create_text(x, height/2+122, text='KeyKite', font=('DejaVu Sans', 34, 'bold'), fill=color('#e7eef8', reveal))
        c.create_text(x, height/2+166, text='Your passwords. Your space.', font=('DejaVu Sans', 12), fill=color('#aebdd0', reveal))
        c.create_text(x, height-34, text='Click or press Esc to skip', font=('DejaVu Sans', 9), fill=color('#aebdd0', reveal*.7))
        self.timer = self.root.after(16, self.tick)


class Button(ttk.Button):
    """Native keyboard/command behavior with a shared 180ms hover transition."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.base_style = kwargs.get('style', 'TButton')
        self.hover_step = 0
        self.hover_timer = None
        self.bind('<Enter>', lambda event: self.animate(6), add='+')
        self.bind('<Leave>', lambda event: self.animate(0), add='+')
        self.bind('<Destroy>', self.cancel_animation, add='+')

    def cancel_animation(self, event=None):
        if self.hover_timer:
            self.after_cancel(self.hover_timer)
            self.hover_timer = None

    def animate(self, target):
        self.cancel_animation()
        appearance = getattr(self._root(), 'appearance', None)
        if appearance is None or not appearance.motion.get() or self.instate(['disabled']):
            self.configure(style=self.base_style)
            return
        self.hover_step += 1 if target > self.hover_step else -1 if target < self.hover_step else 0
        self.configure(style=f'Hover{self.hover_step}.{self.base_style}' if self.hover_step else self.base_style)
        if self.hover_step != target:
            self.hover_timer = self.after(30, lambda: self.animate(target))

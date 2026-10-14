"""Orange and cyan styling shared by every KeyKite screen."""
from tkinter import ttk

BACKGROUND = '#edf7f9'
TEXT = '#173544'
MUTED = '#57737d'
CYAN = '#0e7490'
ORANGE = '#ff8a3d'


def apply_theme(root):
    root.configure(background=BACKGROUND)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=('DejaVu Sans', 10), background=BACKGROUND, foreground=TEXT)
    style.configure('TFrame', background=BACKGROUND)
    style.configure('Card.TFrame', background='#ffffff')
    style.configure('Hero.TFrame', background='#102f3a')
    style.configure('TLabel', background=BACKGROUND)
    style.configure('Card.TLabel', background='#ffffff')
    style.configure('NewVault.TLabel', background='#fff1a8', foreground='#654e00',
                    font=('DejaVu Sans', 9, 'bold'), padding=(6, 2))
    style.configure('Muted.TLabel', foreground=MUTED)
    style.configure('Title.TLabel', font=('DejaVu Sans', 25, 'bold'), foreground=TEXT)
    style.configure('Section.TLabel', font=('DejaVu Sans', 14, 'bold'), background='#ffffff')
    style.configure('Eyebrow.TLabel', foreground=CYAN, font=('DejaVu Sans', 9, 'bold'))
    style.configure('HeroTitle.TLabel', background='#102f3a', foreground='#ffffff', font=('DejaVu Sans', 28, 'bold'))
    style.configure('HeroAccent.TLabel', background='#102f3a', foreground=ORANGE, font=('DejaVu Sans', 28, 'bold'))
    style.configure('Hero.TLabel', background='#102f3a', foreground='#b9e7ee', font=('DejaVu Sans', 11))
    style.configure('TButton', padding=(12, 9), background='#d9f0f4', foreground='#15576a',
                    borderwidth=0, relief='flat', font=('DejaVu Sans', 10))
    style.map('TButton', background=[('disabled', '#edf2f3'), ('pressed', '#a8dde6'), ('active', '#c1e9ef')],
              foreground=[('disabled', '#8ba0a7')])
    style.configure('Accent.TButton', background=ORANGE, foreground='#3d2109', font=('DejaVu Sans', 10, 'bold'))
    style.map('Accent.TButton', background=[('disabled', '#f5e2d6'), ('pressed', '#f47724'), ('active', '#ff9e5e')],
              foreground=[('disabled', '#96765f')])
    style.configure('Eye.TButton', padding=(8, 6))
    style.configure('Danger.TButton', foreground='#b42338', background='#fff0f1')
    style.map('Danger.TButton', background=[('active', '#ffe0e4'), ('pressed', '#ffd1d8')])
    style.configure('TEntry', padding=8, fieldbackground='#ffffff', bordercolor='#c4dce2',
                    lightcolor='#c4dce2', darkcolor='#c4dce2', insertcolor=TEXT)
    style.map('TEntry', bordercolor=[('focus', CYAN)], lightcolor=[('focus', CYAN)], darkcolor=[('focus', CYAN)])
    style.configure('TCombobox', padding=7, fieldbackground='#ffffff', background='#d9f0f4',
                    bordercolor='#c4dce2', arrowcolor=CYAN)
    style.map('TCombobox', fieldbackground=[('readonly', '#ffffff')], selectbackground=[('readonly', '#d9f0f4')],
              selectforeground=[('readonly', TEXT)])
    style.configure('TCheckbutton', background='#ffffff', padding=4)
    style.configure('Treeview', background='#ffffff', fieldbackground='#ffffff', foreground=TEXT,
                    rowheight=46, borderwidth=0)
    style.configure('Treeview.Heading', background='#e1f4f7', foreground='#236778',
                    font=('DejaVu Sans', 9, 'bold'), padding=12, relief='flat')
    style.map('Treeview', background=[('selected', '#c9f0f5')], foreground=[('selected', '#114b5b')])
    style.map('Treeview.Heading', background=[('active', '#c9edf2')])
    style.configure('Vertical.TScrollbar', background='#c2e1e7', troughcolor='#f0f8fa',
                    borderwidth=0, arrowsize=12)
    style.configure('Brand.TSeparator', background=ORANGE)
    return style

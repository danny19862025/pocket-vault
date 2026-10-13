"""A small, offline password-strength estimate; no passwords leave the app."""
import re
import tkinter as tk
from tkinter import ttk


COMMON = {'password', 'passwords', 'passw0rd', 'qwerty', 'letmein', 'welcome',
          'admin', 'administrator', 'iloveyou', 'monkey', 'dragon', 'football',
          'abc', 'abcd', 'abcdef', 'test', 'secret', 'login', 'changeme'}
SEQUENCES = ('abcdefghijklmnopqrstuvwxyz', '01234567890', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm')


def estimate(password):
    """Return 0 (empty) through 4 (strong estimated), with conservative pattern caps."""
    if not password:
        return 0
    base = re.sub(r'[\d\W_]+$', '', password.casefold())
    normalized = base.translate(str.maketrans({'@': 'a', '$': 's', '0': 'o', '1': 'i',
                                               '3': 'e', '4': 'a', '5': 's', '7': 't', '!': 'i'}))
    letters = re.sub(r'[^a-z]', '', normalized)
    plain = password.casefold().strip()
    if len(set(plain)) <= 3 or letters in COMMON:
        return 1
    if any(plain in sequence or plain in sequence[::-1] for sequence in SEQUENCES):
        return 1
    # Detect repeated chunks, including long strings like abcdabcdabcdabcd.
    for size in range(1, min(16, len(plain) // 2) + 1):
        if len(plain) % size == 0 and plain == plain[:size] * (len(plain) // size):
            return 1
    length = len(password)
    score = 1 if length < 8 else 2 if length < 12 else 3 if length < 16 else 4
    if len(set(plain)) < 6:
        score = min(score, 2)
    return score


class StrengthMeter(ttk.Frame):
    LABELS = ('Enter a password', 'Very weak', 'Weak', 'Fair', 'Strong')
    COLORS = ('#94a3b8', '#b42338', '#e16b21', '#b58a00', '#23834b')

    def __init__(self, parent, variable, card=False):
        super().__init__(parent, style='Card.TFrame' if card else 'TFrame')
        self.variable = variable
        self.text = tk.StringVar()
        self.bar = tk.Canvas(self, height=6, highlightthickness=0, background='#e0eef1')
        self.bar.pack(fill='x')
        self.label = ttk.Label(self, textvariable=self.text, style='Card.TLabel' if card else 'TLabel',
                               font=('DejaVu Sans', 9))
        self.label.pack(anchor='w', pady=(3, 0))
        self.bar.bind('<Configure>', self.update_meter)
        self.trace = variable.trace_add('write', self.update_meter)
        self.update_meter()

    def update_meter(self, *args):
        self.score = estimate(self.variable.get())
        self.text.set('Estimated strength · ' + self.LABELS[self.score])
        color = self.COLORS[self.score]
        self.label.configure(foreground=color)
        self.bar.delete('all')
        if self.score:
            self.bar.create_rectangle(0, 0, self.bar.winfo_width() * self.score / 4, 6, fill=color, outline='')

    def destroy(self):
        self.variable.trace_remove('write', self.trace)
        super().destroy()

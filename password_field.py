"""Password entry with a keyboard-accessible eye button."""
import tkinter as tk
from tkinter import ttk


class PasswordField(ttk.Frame):
    def __init__(self, parent, variable, card=False):
        super().__init__(parent, style='Card.TFrame' if card else 'TFrame')
        self.visible = tk.BooleanVar(value=False)
        self.entry = ttk.Entry(self, textvariable=variable, show='•')
        self.entry.pack(side='left', fill='x', expand=True)
        self.eye = self.eye_icon(False)
        self.crossed_eye = self.eye_icon(True)
        self.button = ttk.Button(self, text='Show', image=self.eye, compound='left',
                                 style='Eye.TButton', command=self.toggle)
        self.button.pack(side='right', padx=(6, 0))

    def eye_icon(self, crossed):
        icon = tk.PhotoImage(master=self, width=24, height=18)
        color = '#0e7490'
        for x in range(2, 22):
            radius = 5 * (1 - ((x - 11.5) / 9.5) ** 2)
            for y in (round(8.5 - radius), round(8.5 + radius)):
                icon.put(color, (x, y))
        for x in range(9, 15):
            for y in range(6, 12):
                if (x - 11.5) ** 2 + (y - 8.5) ** 2 < 8:
                    icon.put(color, (x, y))
        if crossed:
            for x in range(2, 22):
                y = round(2 + (x - 2) * 13 / 19)
                icon.put(color, (x, y))
                icon.put(color, (x, min(y + 1, 17)))
        return icon

    def set_visible(self, visible):
        self.visible.set(visible)
        self.entry.configure(show='' if visible else '•')
        self.button.configure(text='Hide' if visible else 'Show',
                              image=self.crossed_eye if visible else self.eye)

    def toggle(self):
        self.set_visible(not self.visible.get())

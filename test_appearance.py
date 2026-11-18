"""Appearance integration checks; uses disposable settings and no personal vaults."""
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk

from app import App
from theme import DARK, LIGHT, Button, OpeningAnimation, blend


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires a graphical display')
class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env = patch.dict(os.environ, XDG_CONFIG_HOME=self.directory.name)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.desktop = patch('theme.desktop_setting', return_value='')
        self.desktop.start()
        self.addCleanup(self.desktop.stop)
        self.app = App()
        self.addCleanup(self.app.destroy)
        self.app.update()

    def test_live_theme_preserves_edits_and_updates_canvas(self):
        self.app.intro.finish()
        self.app.master_password.set('unsaved master password')
        self.app.appearance.mode.set('Dark')
        self.app.appearance.changed()
        self.app.update()
        self.assertEqual(self.app.master_password.get(), 'unsaved master password')
        self.assertEqual(self.app.cget('background'), DARK[0])
        self.assertEqual(ttk.Style(self.app).lookup('Card.TFrame', 'background'), DARK[1])
        self.assertEqual(self.app.master_strength.bar.cget('background'), blend(DARK[1], DARK[5], .25))
        self.app.appearance.mode.set('Light')
        self.app.appearance.changed()
        self.app.update()
        self.assertEqual(self.app.cget('background'), LIGHT[0])

    def test_opened_theme_dropdown_tracks_palette_changes(self):
        self.app.intro.finish()
        appearance = self.app.appearance
        bar = next(w for w in self.app.winfo_children()
                   if any(isinstance(c, ttk.Combobox) for c in w.winfo_children()))
        picker = next(w for w in bar.winfo_children() if isinstance(w, ttk.Combobox))
        appearance.mode.set('Dark')
        appearance.changed()
        popup = self.app.tk.call('ttk::combobox::PopdownWindow', str(picker))
        listbox = f'{popup}.f.l'
        if not self.app.tk.call('winfo', 'exists', listbox):
            self.skipTest('Platform uses a native dropdown instead of a Tk listbox')
        for mode, palette in (('Light', LIGHT), ('Dark', DARK), ('Light', LIGHT)):
            appearance.mode.set(mode)
            appearance.changed()
            self.app.update()
            for option, expected in (
                ('background', palette[1]), ('foreground', palette[2]),
                ('selectbackground', blend(palette[1], palette[4], .28)),
                ('selectforeground', palette[2]),
            ):
                self.assertEqual(self.app.tk.call(listbox, 'cget', f'-{option}'), expected)

    def test_custom_palette_persists_and_corrupt_file_falls_back(self):
        custom = list(DARK)
        custom[4] = '#a855f7'
        self.app.appearance.custom = custom
        self.app.appearance.mode.set('Custom')
        self.app.appearance.changed()
        path = self.app.appearance.path
        self.assertEqual(json.loads(path.read_text())['custom'], custom)
        from theme import Appearance
        for corrupt in (False, True):
            if corrupt:
                path.write_text('{broken')
            root = tk.Tk()
            try:
                controller = Appearance(root)
                self.assertEqual(controller.mode.get(), 'System' if corrupt else 'Custom')
                if not corrupt:
                    self.assertEqual(controller.palette[4], '#a855f7')
            finally:
                root.destroy()

    def test_colour_editor_apply_and_cancel(self):
        self.app.intro.finish()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        self.app.appearance.edit()
        window = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        entries = [w for w in descendants(window) if isinstance(w, ttk.Entry)]
        entries[4].delete(0, 'end')
        entries[4].insert(0, ' #A5F ')
        next(w for w in descendants(window) if isinstance(w, Button) and w.cget('text') == 'Apply theme').invoke()
        self.app.update()
        self.assertEqual(self.app.appearance.palette[4], '#aa55ff')
        self.assertEqual(self.app.appearance.mode.get(), 'Custom')
        self.app.appearance.edit()
        window = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        next(w for w in descendants(window) if isinstance(w, Button) and w.cget('text') == 'Reset colours').invoke()
        next(w for w in descendants(window) if isinstance(w, Button) and w.cget('text') == 'Cancel').invoke()
        self.assertEqual(self.app.appearance.palette[4], '#aa55ff')

    def test_hover_and_intro_stop_cleanly(self):
        intro = self.app.intro
        intro.start -= 2
        intro.tick()
        self.assertFalse(intro.canvas.winfo_exists())
        self.assertIsNone(intro.timer)
        button = Button(self.app, text='Preview')
        button.pack()
        button.animate(6)
        deadline = time.monotonic() + .3
        while time.monotonic() < deadline:
            self.app.update()
            time.sleep(.01)
        self.assertEqual(button.hover_step, 6)
        button.animate(0)
        button.destroy()
        self.assertIsNone(button.hover_timer)
        self.app.intro = OpeningAnimation(self.app)
        self.app.appearance.motion.set(False)
        self.app.appearance.changed()
        self.assertFalse(self.app.intro.canvas.winfo_exists())
        self.assertFalse(json.loads(self.app.appearance.path.read_text())['animations'])

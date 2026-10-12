# Pocket Vault

An open-source Python/Tkinter password manager, tested on Arch Linux. Create an encrypted vault,
add/edit/delete credentials, search services and usernames, generate passwords,
and copy a password with a 20-second clipboard timeout. Locks after five minutes
without keyboard or mouse-button activity; unsaved edits are discarded on lock.

## License and availability

Pocket Vault is released under the [MIT License](LICENSE). Anyone who obtains a
copy may use, modify, and redistribute it under those terms. This repository contains only Pocket Vault.

## Requirements and installation

Tested with Python 3.14, Tkinter, and cryptography 50.0.2 on Arch Linux.
Other desktop platforms have not been tested. A graphical desktop is required.
There is no standalone installer; run the Python source.

Clone the repository:

```bash
git clone https://github.com/danny19862025/pocket-vault.git
cd pocket-vault
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Tkinter must be installed through your operating system; it is not included in
`requirements.txt`. The Arch Linux instructions below install all dependencies
without a virtual environment.

## Run on Arch Linux

Run these commands from the repository root:

```bash
sudo pacman -Syu --needed python tk python-cryptography
/usr/bin/python3 app.py
```

Use the system Python above so it can access the packages installed by pacman.
Choose a new vault location, enter and confirm a master password (12+ characters),
then click **Create new vault**. Later, select the same file and click **Unlock vault**.
Click **+ New**, fill in the details, then **Save**. Select an existing entry to edit it.
The default vault is in `~/.local/share/pocket-vault/`, outside this repository.

## Cloud storage

Use **Choose new location** to put the encrypted `.vault` file inside a folder
already synchronized by your cloud client. On another computer, open the synced
file using the same master password. This app does not include provider login or
its own cloud client. Sync must be configured separately.

Edit on only one computer at a time; lock the app and let sync finish before opening
it elsewhere. The app detects changes present before saving, but cannot merge
simultaneous edits or guarantee protection against sync races. Keep encrypted backups.

## Storage details

Uses authenticated Fernet encryption with a key derived using scrypt (N=131072,
r=8, p=1) and a random 16-byte salt. Passwords, usernames, service names, and URLs
are encrypted together. Writes use a private temporary file and atomic replacement.
The master password is never saved. It cannot be reset to recover an existing vault.
Clipboard managers may keep copied passwords after the app clears its clipboard.
Python cannot guarantee that secrets are erased from process memory.
This is a learning project, not an independently audited password manager.

References: [cryptography documentation](https://cryptography.io/en/stable/fernet/),
[Arch Tk package](https://archlinux.org/packages/extra/x86_64/tk/),
[Arch cryptography package](https://archlinux.org/packages/extra/x86_64/python-cryptography/).

## Verify storage

From the repository root:

```bash
/usr/bin/python3 -m unittest discover -v
```

## Interface

The two-panel layout includes a searchable, alphabetically sorted password list,
a scroll bar, and an entry editor. Save with **Save password** or **Ctrl+S**;
create an entry with **+ New** or **Ctrl+N**. Unsaved edits prompt before switching
entries, creating another entry, manually locking, or closing. Automatic locking
still discards unsaved edits after five minutes to protect an unattended vault.

## Contributing

Bug reports and pull requests are welcome. Include your operating system, Python
version, and steps to reproduce the issue. Use a temporary vault with dummy data;
never attach a real vault, master password, or personal credentials. Run the test
suite before submitting changes. GUI tests require a display and are skipped when
`DISPLAY` is unset. Passing tests are not a security audit.

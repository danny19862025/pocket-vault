# KeyKite 1.1.0

See [release changes](CHANGELOG.md).

An open-source Python/Tkinter password manager, tested on Arch Linux. Create an encrypted vault,
add/edit/delete credentials, search services and usernames, generate passwords,
and copy a password with a 20-second clipboard timeout. A live strength bar below
the master password and entry password fields shows an offline estimate from very
weak to strong. It accounts for length and some common or repeated patterns; it
does not check breach databases or guarantee that a password is safe. Locks after five minutes
without keyboard or mouse-button activity; unsaved edits are discarded on lock.

## License and availability

KeyKite is released under the [MIT License](LICENSE). Anyone who obtains a
copy may use, modify, and redistribute it under those terms. This repository contains only KeyKite.

## Requirements and installation

Tested with Python 3.14, Tkinter, and cryptography 50.0.2 on Arch Linux.
A graphical desktop is required. Linux is tested locally; Windows and macOS
packages are built by GitHub Actions. Interactive use on those platforms still
needs verification. The packages are portable apps, without an installer.

### Linux distributions

See the [Linux installation guide](INSTALL.md) for dependency commands and setup:

- [Debian, Ubuntu, Linux Mint, Pop!_OS, and related distributions](INSTALL.md#debian-ubuntu-linux-mint-and-related-distributions)
- [Fedora](INSTALL.md#fedora) and [Fedora Atomic desktops](INSTALL.md#fedora-atomic-desktops)
- [Arch Linux, EndeavourOS, and Manjaro](INSTALL.md#arch-linux-endeavouros-and-manjaro)
- [Gentoo](INSTALL.md#gentoo)
- [openSUSE Tumbleweed and Leap](INSTALL.md#opensuse-tumbleweed-and-leap)
- [Alpine Linux](INSTALL.md#alpine-linux)
- [Void Linux](INSTALL.md#void-linux)
- [NixOS and Nix](INSTALL.md#nixos-and-nix)
- [Other Linux distributions](INSTALL.md#other-linux-distributions)

The guide includes launching, updating, optional cloud backup, and troubleshooting.
Only Arch Linux has been tested locally; the other instructions are installation
guidance, not a claim that each distribution has been tested.

## Windows and macOS apps

Open [desktop builds](https://github.com/danny19862025/pocket-vault/actions/workflows/desktop-builds.yml),
select a successful run, and download its artifact (GitHub sign-in required):

- **KeyKite-Windows-x64**: extract the archive and open `KeyKite.exe`.
- **KeyKite-macOS-arm64** (Apple Silicon): extract the artifact, then the enclosed
  ZIP, and move `KeyKite.app` into Applications.

Both apps display **KeyKite**. Existing vault paths and preferences retain the
`pocket-vault` directory name so the rename does not move stored data.
Python and the encryption library are bundled. Cloud backup still requires
[rclone](https://rclone.org/install/) installed separately and available on PATH.
These builds have no Windows publisher certificate or Apple Developer ID
signature/notarization; the operating system may require approval before opening.

To build locally, use Python 3.13 with Tkinter on the target operating system:

```text
python -m pip install -r requirements.txt "pyinstaller>=6.16,<7" "pillow>=11,<13"
```

On Windows:

```text
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon keykite.png --name KeyKite app.py
```

On macOS:

```text
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon keykite.png --name KeyKite --osx-bundle-identifier io.github.danny19862025.keykite app.py
```

The output is in `dist/`. Build each package on its target OS; PyInstaller does
not cross-compile. See [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html).

## Run from Python source

On Linux, first install the dependencies for your distribution in the
[installation guide](INSTALL.md). Then clone the repository:

```bash
git clone https://github.com/danny19862025/pocket-vault.git
cd pocket-vault
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Tkinter must be installed through your operating system; it is not included in
`requirements.txt`. openSUSE and Void have alternative environment-creation
commands in the guide. The Arch Linux instructions below install all dependencies
without a virtual environment.

## Run on Arch Linux

Run these commands from the repository root:

```bash
sudo pacman -Syu --needed python tk python-cryptography
/usr/bin/python3 app.py
```

Use the system Python above so it can access the packages installed by pacman.
Click **Choose new location…**, browse to a parent folder, then use **Create new
folder…** inside that dialog if needed. Enter a vault filename and click **Use this
location**. You can also use **Create folder…** directly on the unlock screen. Then enter and confirm a master password (12+ characters),
then click **Create new vault**. Later, select the same file and click **Unlock vault**.
Click **+ New**, fill in the details, then **Save**. Select an existing entry to edit it.
The default vault is in `~/.local/share/pocket-vault/`, outside this repository.
After successfully opening or creating a vault, KeyKite remembers its path
for the next launch. **Open existing file…** starts in the selected vault’s folder
with its filename prefilled. Only the location is saved, never the master password.

## Import from another password manager

Unlock your vault, click **Import passwords…**, and select a CSV, TSV, or unencrypted
JSON export from your other manager. Common column names are matched automatically;
use the dropdowns to correct the mapping. Review the logins and click **Import into
vault**. Nothing is saved until you click that button. The import is encrypted and
saved in one operation, with the usual cloud backup if enabled.

Supported layouts include browser CSV (`name,url,username,password`), Firefox-style
CSV without a name (the website becomes the title), Bitwarden CSV and unencrypted
JSON, KeePass CSV (`Account,Login Name,Password,Web Site`), and generic delimited
exports such as LastPass or 1Password CSV with manual column mapping. Other JSON
files can use a list of login objects, or `{ "entries": [...] }`, with the same fields.
CSV must have a header row; UTF-8 (with or without BOM) and UTF-16 are supported.

The preview reports skipped duplicates and incomplete/non-login items. Exact
matches across all four login fields are skipped, including duplicates within the
export. Existing entries are never replaced; changed credentials are imported as
separate entries. Passwords are preserved exactly, including spaces and newlines.
Only service/title, username, password, and website are imported. Notes, custom
fields, TOTP, attachments, cards, identities, and passkeys are not imported.
Native encrypted formats such as KDBX, 1PUX, and encrypted Bitwarden JSON are not
supported; export CSV or unencrypted JSON in the original manager first.

Export files contain readable credentials and are left unchanged by KeyKite.
After verifying the imported entries, remove the export from your device. The
importer never uploads the plaintext export or writes plaintext temporary files.
Files are limited to 20 MB and 50,000 items per import.

Format references: [Bitwarden exports](https://bitwarden.com/help/condition-bitwarden-import/),
[KeePass CSV](https://keepass.info/help/base/importexport.html).

## Cloud storage

Open **Cloud storage…** from the vault dashboard or **Cloud storage • Google Drive & Dropbox…**
from the unlock screen. Install [rclone](https://rclone.org/install/) first
(on Arch: `sudo pacman -S rclone`). It is already installed on the development desktop.

1. Click **Connect Google Drive…** or **Connect Dropbox…**, and finish signing in
   with the chosen provider in your browser. KeyKite uses rclone’s OAuth flow;
   account tokens are managed by rclone, separately from the master password.
   Google Drive uses `drive.file` scope, limiting access to files created through
   this app’s rclone connection. Dropbox uses rclone’s standard connection
   ([Dropbox setup](https://rclone.org/dropbox/)).
2. Select the account and cloud folder, then click **Save options**.
3. Unlock your vault and click **Back up now**, or enable **Back up this vault after
   every saved change**. Saving or deleting an entry then queues an encrypted backup.
   Local saves still succeed offline; failures appear in the cloud panel. Retry with
   **Back up now** when connected. Keep the app open until the upload finishes.
4. To restore, lock the vault, open the cloud panel, click **List backups**, select a
   version, and **Restore to new file…**. Choose a new local filename; existing vaults
   are never overwritten. Unlock the restored file with its original master password.

Backups upload only the encrypted vault bytes, never the master password or unsaved
edits. Each upload creates a separate timestamped version, avoiding replacement of
another device's backup. Backups accumulate; remove unwanted versions in your cloud
account. The local vault remains available offline. This is backup and restore,
not automatic two-way synchronization or merging; edit on one device at a time.

Google Drive and Dropbox both support manual backup, automatic backup after saved
changes, and restore to a new file. Select the account you want to back up to;
automatic backups use the selected destination. Existing rclone accounts for other providers also appear under **Refresh accounts**.
You can still use **Choose new location** to store the encrypted file in a folder
managed by a separate cloud sync client. Sync races cannot be merged by the app.
On a new device, reconnect your existing rclone configuration to access files created
with the restricted Google Drive scope (see [rclone Drive documentation](https://rclone.org/drive/)).

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

The orange-and-cyan interface has a split unlock screen, white cards, orange
primary actions, and cyan highlights. The two-panel vault layout includes a searchable, alphabetically sorted password list,
a scroll bar, and an entry editor. Save with **Save password** or **Ctrl+S**;
create an entry with **+ New** or **Ctrl+N**. Click the eye-shaped **Show/Hide**
button beside a password to reveal or mask it. Eye buttons also appear beside the
master and confirmation passwords. New entries, switching entries, and locking
reset password visibility. Unsaved edits prompt before switching
entries, creating another entry, manually locking, or closing. Automatic locking
still discards unsaved edits after five minutes to protect an unattended vault.

## Contributing

Bug reports and pull requests are welcome. Include your operating system, Python
version, and steps to reproduce the issue. Use a temporary vault with dummy data;
never attach a real vault, master password, or personal credentials. Run the test
suite before submitting changes. GUI tests require a display and are skipped when
`DISPLAY` is unset. Passing tests are not a security audit.

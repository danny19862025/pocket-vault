# Install KeyKite on Linux

KeyKite runs from Python source on a graphical Linux desktop. The project is
tested locally on Arch Linux with Python 3.14 and cryptography 50.0.2. Instructions
for other distributions are based on their package names and Python setup;
they have not all been tested on those systems.

Use a maintained distribution with Python 3.9 or newer, Tkinter, and access to
PyPI to install the version of cryptography specified in [requirements.txt](requirements.txt).
Python 3.13 or 3.14 is recommended to match the project's build/test environments.
There is currently no project-provided Linux `.deb`, `.rpm`, AppImage, or Flatpak.

1. Install the prerequisites for your distribution below.
2. Follow [Download, install, and launch](#download-install-and-launch).
3. Optionally install [cloud backup support](#optional-cloud-backup).

Run package-manager commands with `sudo`, or as root if your distribution does
not use sudo. Run KeyKite and the Python installation commands as your normal user.
NixOS has a separate workflow below.

## Debian, Ubuntu, Linux Mint, and related distributions

Also applies to Pop!_OS, Zorin OS, and other Debian/Ubuntu derivatives using apt.

```bash
sudo apt update
sudo apt install git python3 python3-tk python3-venv python3-pip
```

Continue with [Download, install, and launch](#download-install-and-launch).
Installing `python3-venv` is necessary on Debian/Ubuntu to create an environment
with pip. See the Debian package pages for [Tkinter](https://packages.debian.org/trixie/python3-tk)
and [venv](https://packages.debian.org/trixie/python3-venv).

## Fedora

For the standard Fedora Workstation, KDE, and other mutable Fedora editions:

```bash
sudo dnf install git python3 python3-tkinter python3-pip
```

Continue with [Download, install, and launch](#download-install-and-launch).
Fedora calls the GUI package [python3-tkinter](https://packages.fedoraproject.org/pkgs/python3.14/python3-tkinter/).

## Fedora Atomic desktops

On Silverblue, Kinoite, and similar rpm-ostree desktops, layer the prerequisites:

```bash
sudo rpm-ostree install git python3-tkinter python3-pip
```

If a package is already provided by the base image, omit it from the command.
Reboot into the new deployment, then follow
[Download, install, and launch](#download-install-and-launch) from a normal desktop
terminal. See [Fedora's package-layering guide](https://docs.fedoraproject.org/en-US/fedora-silverblue/getting-started/#package-layering).

## Arch Linux, EndeavourOS, and Manjaro

```bash
sudo pacman -Syu --needed git python tk python-pip
```

Continue with [Download, install, and launch](#download-install-and-launch).
Use a full system update with `-Syu` to avoid partial upgrades.

For the existing, locally tested system-package approach instead, install
`python-cryptography` and run `/usr/bin/python3 app.py` from the cloned repository,
as described in the [README](README.md#run-on-arch-linux). That alternative uses
Arch's encryption-library version rather than the virtual environment's pinned range.

## Gentoo

Enable `tk` and `ensurepip` for Python in your Portage package USE configuration.
For example, add this line to a file under `/etc/portage/package.use/` if it is a
directory, or to `/etc/portage/package.use` if it is a file:

```text
dev-lang/python tk ensurepip
```

Then install or rebuild Python with those flags:

```bash
sudo emerge --ask --changed-use dev-lang/python dev-vcs/git
python3 -c 'import tkinter, ensurepip; print("Python prerequisites are ready")'
```

Ensure the Python selected by `python3` is a supported Python 3 interpreter built
with those flags. Continue with
[Download, install, and launch](#download-install-and-launch).
The [Gentoo Python package](https://packages.gentoo.org/packages/dev-lang/python)
documents both USE flags; installing Tk alone does not enable Python's Tkinter module.

## openSUSE Tumbleweed and Leap

On current Tumbleweed and Leap 16, use matching Python 3.13 packages:

```bash
sudo zypper refresh
sudo zypper install git python313 python313-tk python313-pip python313-virtualenv
```

Follow [Download, install, and launch](#download-install-and-launch), but replace
its environment-creation command with:

```bash
python3.13 -m virtualenv .venv
```

On a release offering a different supported Python version, use that version's
matching interpreter, Tk, pip, and virtualenv packages (for example, `python311`,
`python311-tk`, `python311-pip`, and `python311-virtualenv`, with `python3.11`).
Do not mix Tk packages from one Python version with an interpreter from another.
See [openSUSE's Python package naming](https://github.com/openSUSE/python-rpm-macros#terminology).

## Alpine Linux

On an Alpine desktop:

```bash
sudo apk add git python3 python3-tkinter py3-pip
```

Some releases place [python3-tkinter](https://pkgs.alpinelinux.org/packages?name=python3-tkinter)
in `community`; enable the community repository for your installed Alpine release
if needed. Do not mix stable and edge repositories.
Continue with [Download, install, and launch](#download-install-and-launch).
Alpine's musl-based environment may need compilation dependencies on architectures
without a compatible cryptography wheel; see [troubleshooting](#troubleshooting).

## Void Linux

```bash
sudo xbps-install -S git python3 python3-tkinter python3-pip python3-virtualenv
```

Follow [Download, install, and launch](#download-install-and-launch), but replace
its environment-creation command with:

```bash
python3 -m virtualenv .venv
```

Void builds Python without ensurepip, so virtualenv supplies pip for this setup.
See the [Python package definition](https://github.com/void-linux/void-packages/blob/master/srcpkgs/python3/template)
and [virtualenv package](https://github.com/void-linux/void-packages/blob/master/srcpkgs/python3-virtualenv/template).
Void musl users may also need compilation dependencies; see
[cryptography's installation documentation](https://cryptography.io/en/stable/installation/).

## NixOS and Nix

Use a Nix-provided Python environment, rather than installing binary PyPI wheels
into a regular venv. With a configured `nixpkgs` channel:

```bash
nix-shell -p git 'python3.withPackages (ps: [ ps.tkinter ps.cryptography ps.packaging ])'
git clone https://github.com/danny19862025/pocket-vault.git
cd pocket-vault
python3 -c 'from pathlib import Path; import cryptography; from packaging.requirements import Requirement; requirement = Requirement(Path("requirements.txt").read_text().strip()); assert requirement.specifier.contains(cryptography.__version__), "Update nixpkgs: cryptography does not match requirements.txt"; print("Dependency version is compatible")'
python3 app.py
```

Check that the dependency check succeeds before launching. The cryptography
version depends on your nixpkgs revision; older revisions may not yet provide
the required range. Use a nixpkgs revision that supplies it, or override the
package using Nix packaging tools. This route does not run pip or create `.venv`.
See the [NixOS Python guide](https://wiki.nixos.org/wiki/Python).

On later launches, enter the same `nix-shell`, change to the repository directory,
and run `python3 app.py` again. Include `rclone` in the `nix-shell -p` package list
if you want cloud backup.

## Other Linux distributions

Install Git, a supported Python 3 interpreter, its matching Tkinter/Tk support,
and either venv with pip/ensurepip or virtualenv through your distribution's
package manager. Then follow the common steps below. If venv has no ensurepip,
use `python3 -m virtualenv .venv` instead, after installing virtualenv.

Package names vary between distributions and releases. KeyKite needs a graphical
desktop; a minimal server or container alone cannot display its window.

## Download, install, and launch

After installing your distribution's prerequisites, run:

```bash
git clone https://github.com/danny19862025/pocket-vault.git
cd pocket-vault
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'import tkinter, cryptography; print("Dependencies ready; cryptography", cryptography.__version__)'
.venv/bin/python app.py
```

Use the alternate environment-creation command above on openSUSE or Void.
The repository is still named `pocket-vault` on GitHub; the app is named KeyKite.
Tkinter comes from your operating system, while pip installs the required
encryption-library version inside `.venv`. Do not use `sudo pip` or
`--break-system-packages`; the virtual environment keeps these dependencies separate.

For later launches, open a terminal in your `pocket-vault` directory and run:

```bash
.venv/bin/python app.py
```

There is no need to activate the environment when using its Python path directly.
Follow the [README's first-vault steps](README.md#run-on-arch-linux) to create or
open a vault. Vault files are stored outside the repository by default.

## Optional cloud backup

Local vault use does not need rclone. For Google Drive or Dropbox backup, install
it through your distribution's package manager:

| Distribution | Command |
| --- | --- |
| Debian / Ubuntu and derivatives | `sudo apt install rclone` |
| Fedora | `sudo dnf install rclone` |
| Fedora Atomic | `sudo rpm-ostree install rclone` (then reboot) |
| Arch and derivatives | `sudo pacman -Syu --needed rclone` |
| Gentoo | `sudo emerge --ask net-misc/rclone` |
| openSUSE | `sudo zypper install rclone` |
| Alpine | `sudo apk add rclone` |
| Void | `sudo xbps-install -S rclone` |
| NixOS / Nix | Add `rclone` to the `nix-shell -p` command above |

If your release does not provide rclone, see its
[official installation instructions](https://rclone.org/install/).
Verify `rclone version` works in the terminal you use to start KeyKite, then
follow the [cloud-storage setup](README.md#cloud-storage).

## Update KeyKite

Close KeyKite and back up your encrypted vault file first. From the repository:

```bash
git pull --ff-only
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

If you use the Arch system-package route, update with pacman and launch with
`/usr/bin/python3 app.py`. For Nix, update the source with `git pull --ff-only`,
enter your Nix environment, repeat the dependency check, and run `python3 app.py`.
If a distribution upgrade changes Python's major/minor version, recreate the
virtual environment with the new matching interpreter and reinstall requirements.

## Troubleshooting

- **`No module named tkinter` or `_tkinter`:** install your distribution's Tkinter
  package for the interpreter used to create `.venv`. On Gentoo, rebuild that
  Python with `tk`. Tkinter cannot be installed with pip.
- **`No module named cryptography`:** run the requirements installation using
  `.venv/bin/python`, then launch with that same interpreter.
- **`ensurepip is not available` when creating `.venv`:** install `python3-venv`
  on Debian/Ubuntu. On Void or openSUSE, use the virtualenv instructions above.
- **`externally-managed-environment`:** use `.venv/bin/python -m pip`, not the
  system pip. See [Void's explanation](https://voidlinux.org/news/2023/10/python3-external.html).
- **No display / `$DISPLAY` error:** launch from a logged-in graphical desktop.
  Tkinter uses X11; a Wayland desktop needs working XWayland support.
- **pip tries to compile cryptography and fails:** first upgrade pip in `.venv`
  so it can detect current Linux wheels. If no wheel exists for your architecture,
  follow [cryptography's source-build prerequisites](https://cryptography.io/en/stable/installation/)
  for a C compiler, sufficiently recent Rust, Python headers, OpenSSL, and libffi.
  On Alpine, the build packages include `gcc musl-dev python3-dev libffi-dev
  openssl-dev cargo pkgconfig`; the Rust version must meet cryptography's requirement.
- **Nix dependency-version check fails:** your nixpkgs cryptography package falls
  outside the range in `requirements.txt`; select or package a compatible version.

When reporting an installation problem, include the distribution/release,
`python3 --version`, the command you ran, and its error message. Never include
vault files, master passwords, or personal credentials.

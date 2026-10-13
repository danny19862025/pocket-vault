# Changelog

## 1.1.0 — 2026-10-13

- Add Google Drive and Dropbox sign-in, encrypted versioned backups, optional
  backup after saved changes, and restore to a new local vault file.
- Add CSV/TSV and unencrypted JSON imports from other password managers, with
  column matching, a password-hidden preview, and exact duplicate skipping.
- Add live offline password-strength estimates and eye buttons for revealing
  or hiding passwords.
- Remember the last successfully opened vault across restarts and open the file
  picker in its folder. Start password imports in Downloads.
- Add folder creation inside the new-vault location dialog.
- Refresh the interface with orange actions, cyan accents, a split unlock screen,
  white cards, and a matching vault icon. Highlight the new-vault confirmation hint.

### Validation

28 automated tests cover vault encryption and conflict detection, GUI actions,
imports, strength estimates, preferences, cloud command routing, backup/restore,
and a real rclone round trip using a temporary local backend. Live Google Drive
and Dropbox authentication and uploads require the user's provider sign-in and
were not exercised against a real account during development.

### Scope

Cloud storage is versioned backup and restore, not two-way synchronization.
Imports include service, username, password, and website fields; notes, TOTP,
attachments, and passkeys are not imported. The master password is never saved.

## Initial release — 2026-10-12

Encrypted local vault, password generation and search, clipboard timeout,
auto-lock, conflict checks, and an MIT license.

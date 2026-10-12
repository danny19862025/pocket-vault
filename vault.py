"""Encrypted local vault; only encrypted bytes are written to disk."""
import base64
import json
import os
from pathlib import Path
import tempfile

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


class Vault:
    def __init__(self, path, password, create=False):
        self.path = Path(path).expanduser()
        self.original = None if create else self.path.read_bytes()
        if create:
            if self.path.exists():
                raise ValueError("A vault already exists at this location.")
            if len(password) < 12:
                raise ValueError("Use a master password with at least 12 characters.")
            self.salt = os.urandom(16)
        else:
            try:
                envelope = json.loads(self.original)
                if envelope['version'] != 1:
                    raise ValueError()
                self.salt = base64.b64decode(envelope['salt'], validate=True)
                if len(self.salt) != 16:
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise ValueError("This file is not a supported vault.") from None
        key = Scrypt(salt=self.salt, length=32, n=2**17, r=8, p=1).derive(password.encode())
        self.cipher = Fernet(base64.urlsafe_b64encode(key))
        if create:
            self.entries = []
            self.save([])
        else:
            try:
                self.entries = json.loads(self.cipher.decrypt(envelope['data'].encode()))
                self.validate(self.entries)
            except (InvalidToken, ValueError, KeyError, AttributeError, TypeError):
                raise ValueError("Incorrect master password or damaged vault.") from None

    @staticmethod
    def validate(entries):
        if not isinstance(entries, list) or any(
            not isinstance(e, dict) or any(not isinstance(e.get(k), str)
            for k in ('id', 'name', 'username', 'password', 'url'))
            for e in entries
        ):
            raise ValueError('Invalid password entries.')
        ids = [e['id'] for e in entries]
        if any(not value for value in ids) or len(set(ids)) != len(ids):
            raise ValueError('Password entry IDs must be unique and nonempty.')

    def save(self, entries):
        self.validate(entries)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = self.path.read_bytes() if self.path.exists() else None
        if current != self.original:
            raise ValueError("The vault changed elsewhere. Lock and reopen it before editing.")
        raw = json.dumps({'version': 1, 'salt': base64.b64encode(self.salt).decode(),
                          'data': self.cipher.encrypt(json.dumps(entries).encode()).decode()}).encode()
        fd, temporary = tempfile.mkstemp(prefix='.vault-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if self.original is None:
                os.link(temporary, self.path)  # Never overwrite a file during creation.
                os.unlink(temporary)
            else:
                os.replace(temporary, self.path)
            self.original = raw
            self.entries = entries
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

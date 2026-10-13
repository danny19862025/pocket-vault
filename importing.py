"""Read password-manager exports in memory; only Vault writes imported credentials."""
import csv
from dataclasses import dataclass
import io
import json
from pathlib import Path
import re
import uuid

FIELDS = ('name', 'username', 'password', 'url')
ALIASES = {
    'name': ('name', 'title', 'account', 'servicetitle', 'service', 'sitename'),
    'username': ('username', 'loginusername', 'loginname', 'login', 'email', 'user'),
    'password': ('password', 'loginpassword', 'passwd', 'pass'),
    'url': ('url', 'loginuri', 'website', 'webaddress', 'uri', 'loginurl'),
}


def normalized(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


@dataclass
class ImportData:
    columns: list
    rows: list
    skipped: int = 0

    def mapping(self):
        headers = {normalized(column): column for column in self.columns}
        return {field: next((headers[alias] for alias in ALIASES[field] if alias in headers), '')
                for field in FIELDS}


def load_export(path):
    path = Path(path)
    with path.open('rb') as stream:
        raw = stream.read(20 * 1024 * 1024 + 1)
    if len(raw) > 20 * 1024 * 1024:
        raise ValueError('Export is too large. Import files up to 20 MB.')
    try:
        text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:
        raise ValueError('Export must use UTF-8 or UTF-16 text encoding.') from None
    if path.suffix.lower() == '.json':
        try:
            data = json.loads(text)
        except (ValueError, RecursionError):
            raise ValueError('Cannot read this JSON export. Export a fresh unencrypted JSON or CSV file.') from None
        skipped = 0
        if isinstance(data, dict) and data.get('encrypted'):
            raise ValueError('Encrypted exports from other managers are not supported. Export CSV or unencrypted JSON from that manager.')
        if isinstance(data, dict) and 'items' in data:
            if not isinstance(data['items'], list):
                raise ValueError('This JSON export has no supported login list.')
            if len(data['items']) > 50000:
                raise ValueError('Import up to 50,000 entries at a time.')
            rows = []
            for item in data['items']:
                if not isinstance(item, dict):
                    raise ValueError('This JSON export contains an invalid item.')
                login = item.get('login')
                if item.get('type') != 1 or not isinstance(login, dict):
                    skipped += 1
                    continue
                uris = login.get('uris') or []
                uri = next((u.get('uri') for u in uris if isinstance(u, dict) and isinstance(u.get('uri'), str)), '') if isinstance(uris, list) else ''
                rows.append(dict(name=item.get('name'), username=login.get('username'),
                                 password=login.get('password'), url=uri))
            return ImportData(list(FIELDS), rows, skipped)
        rows = data.get('entries') if isinstance(data, dict) else data
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('Use a Bitwarden unencrypted JSON export or a JSON list of login objects.')
        if len(rows) > 50000:
            raise ValueError('Import up to 50,000 entries at a time.')
        columns = list(dict.fromkeys(key for row in rows for key in row))
        return ImportData(columns, rows)
    if path.suffix.lower() not in ('.csv', '.tsv', '.txt'):
        raise ValueError('Choose a CSV, TSV, or unencrypted JSON export. For KDBX or 1PUX files, export CSV from the original manager first.')
    try:
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel_tab if path.suffix.lower() == '.tsv' else csv.excel
        reader = csv.reader(io.StringIO(text, newline=''), dialect=dialect, strict=True)
        columns = [column.strip() for column in next(reader, [])]
        if not columns or any(not column for column in columns) or len(set(columns)) != len(columns):
            raise ValueError('CSV needs a header row with unique, nonempty column names.')
        rows = []
        skipped = 0
        bitwarden = 'loginpassword' in {normalized(c) for c in columns}
        for values in reader:
            if not values or not any(values):
                continue
            if len(values) != len(columns):
                raise ValueError('CSV rows do not match the header. Export a fresh CSV file from the original manager.')
            row = dict(zip(columns, values))
            if bitwarden:
                entry_type = next((v for k, v in row.items() if normalized(k) == 'type'), 'login')
                if entry_type not in ('login', '1', ''):
                    skipped += 1
                    continue
            rows.append(row)
            if len(rows) > 50000:
                raise ValueError('Import up to 50,000 entries at a time.')
    except csv.Error:
        raise ValueError('Cannot read this CSV export. Check its format or export it again.') from None
    return ImportData(columns, rows, skipped)


def prepare_entries(data, mapping, existing):
    if not mapping.get('password') or mapping['password'] not in data.columns:
        raise ValueError('Select the Password column to preview your import.')
    selected = [mapping.get(field) for field in FIELDS if mapping.get(field)]
    if len(set(selected)) != len(selected):
        raise ValueError('Choose a different column for each field.')
    seen = {tuple(entry[field] for field in FIELDS) for entry in existing}
    entries = []
    skipped, duplicates = data.skipped, 0
    for row in data.rows:
        entry = {field: row.get(mapping.get(field), '') for field in FIELDS}
        entry = {field: '' if value is None else value for field, value in entry.items()}
        if any(not isinstance(value, str) for value in entry.values()) or not entry['password']:
            skipped += 1
            continue
        entry['name'] = entry['name'].strip() or entry['url'].strip() or 'Imported login'
        signature = tuple(entry[field] for field in FIELDS)
        if signature in seen:
            duplicates += 1
            continue
        seen.add(signature)
        entries.append(dict(entry, id=str(uuid.uuid4())))
    return entries, skipped, duplicates

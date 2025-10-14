import gzip
import os
import re
from pathlib import Path

from .diagnostics import decode_counters


def _maybe_gzip_open(path):
    with open(path, 'rb') as handle:
        if handle.read(2) == b'\x1f\x8b':
            return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, 'rt', encoding='utf-8', errors='replace')


def parse_bcert(path):
    text = _maybe_gzip_open(path).read()
    out = {'_source': os.path.basename(path)}

    def g(tag):
        match = re.search(rf'<{tag}>(.*?)</{tag}>', text, re.I | re.S)
        return match.group(1).strip() if match else None

    out['ProductName'] = g('ProductName')
    out['SerialNumber'] = g('SerialNumber')
    out['ROMVersion'] = g('ROMVersion')
    out['ILO'] = g('ILOVersion')
    return out


def parse_filepkg_txt(path):
    files = []
    with open(path, 'rt', encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.strip()
            if line:
                files.append(line)
    return {'_source': os.path.basename(path), 'files': files}


def parse_counters_pkg(path):
    """Decode counters.pkg into a structured diagnostic payload."""

    buffer = Path(path).read_bytes()
    counters, unknown, trailing = decode_counters(buffer)
    out = {
        '_source': os.path.basename(path),
        'counters': counters,
        'bytes': len(buffer),
    }
    if unknown:
        out['unknown_offsets'] = unknown
    if trailing:
        out['trailing_bytes'] = trailing
    return out


def parse_cust_info(path):
    out = {'_source': os.path.basename(path), 'fields': {}}
    try:
        with open(path, 'rt', encoding='utf-8') as handle:
            for line in handle:
                if '=' in line:
                    key, value = line.split('=', 1)
                    out['fields'][key.strip()] = value.strip()
    except UnicodeDecodeError:
        out['fields']['_size_bytes'] = os.path.getsize(path)
    return out

import gzip
import io
import os
import re
import zipfile


_SEVERITY_KEYWORDS = (
    (('critical', 'fatal', 'panic', 'unrecoverable', 'catastrophic', 'failed', 'failure', 'asr'), 'ERROR'),
    (('warn', 'caution', 'degraded', 'attention'), 'WARN'),
    (('info', 'informational', 'notice', 'ok', 'started'), 'INFO'),
)

_TIMESTAMP_PATTERNS = (
    re.compile(r'(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})'),
    re.compile(r'(?P<ts>\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})'),
    re.compile(r'(?P<ts>\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})'),
)


def _decode_text(data):
    for enc in ('utf-8', 'utf-16le', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


def _looks_binary(data):
    if not data:
        return False
    sample = data[: min(len(data), 1024)]
    control = sum(1 for b in sample if b < 9 or 13 < b < 32)
    return control / max(len(sample), 1) > 0.2


def _iter_text_chunks(path):
    with open(path, 'rb') as fh:
        blob = fh.read()
    if blob.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                data = zf.read(info.filename)
                if _looks_binary(data):
                    continue
                yield info.filename, _decode_text(data)
        return
    if blob.startswith(b'\x1f\x8b'):
        text = _decode_text(gzip.decompress(blob))
        yield os.path.basename(path), text
        return
    if _looks_binary(blob):
        return
    yield os.path.basename(path), _decode_text(blob)


def _classify_severity(line):
    lower = line.lower()
    for keywords, level in _SEVERITY_KEYWORDS:
        if any(word in lower for word in keywords):
            return level
    if 'err' in lower:
        return 'ERROR'
    return 'INFO'


def _extract_timestamp(line):
    for pattern in _TIMESTAMP_PATTERNS:
        match = pattern.search(line)
        if match:
            return match.group('ts')
    return None


def parse_bb_files(paths):
    records = []
    sources = []
    for path in paths:
        base = os.path.basename(path)
        sources.append(base)
        for inner, text in _iter_text_chunks(path):
            source = base if inner == base else f'{base}:{inner}'
            for idx, raw_line in enumerate(text.splitlines(), start=1):
                line = raw_line.strip()
                if not line:
                    continue
                rec = {
                    'source': source,
                    'line': idx,
                    'message': line,
                    'severity': _classify_severity(line),
                }
                ts = _extract_timestamp(line)
                if ts:
                    rec['timestamp'] = ts
                records.append(rec)
    return {'records': records, 'sources': sources}

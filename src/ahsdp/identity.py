from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, Optional


def _maybe_open(path: Path):
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return path.open('rt', encoding='utf-8', errors='replace')


def _parse_bcert(path: Path) -> Dict[str, Optional[str]]:
    details: Dict[str, Optional[str]] = {
        'model': None,
        'serial_number': None,
        'uuid': None,
        'firmware_system_rom': None,
        'firmware_ilo': None,
    }

    try:
        with _maybe_open(path) as handle:
            text = handle.read()
    except OSError:
        return details

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return details

    def _get(tag: str) -> Optional[str]:
        elem = root.find(f'.//{tag}')
        if elem is not None and elem.text:
            value = elem.text.strip()
            return value or None
        return None

    details['model'] = _get('ProductName')
    details['serial_number'] = _get('SerialNumber')
    details['uuid'] = _get('UUID') or _get('UID')
    details['firmware_system_rom'] = _get('ROMVersion')
    details['firmware_ilo'] = _get('ILOVersion')
    return details


def _parse_filepkg(path: Path) -> Dict[str, object]:
    captures = []
    capture_ids = []
    capture_dates = []

    try:
        with path.open('rt', encoding='utf-8', errors='replace') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if line.startswith('\ufeff'):
                    line = line.lstrip('\ufeff')
                if not line:
                    continue
                lower = line.lower()
                if lower.endswith(('.bb', '.bb.gz', '.bb.zip')):
                    captures.append(line)
                    id_match = re.match(r'(\d+)-', line)
                    if id_match:
                        capture_ids.append(id_match.group(1))
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    if date_match:
                        capture_dates.append(date_match.group(1))
    except OSError:
        pass

    def _unique(sequence: Iterable[str]) -> Iterable[str]:
        seen = set()
        for item in sequence:
            if item not in seen:
                seen.add(item)
                yield item

    capture: Dict[str, object] = {}
    if captures:
        capture['artifacts'] = list(_unique(captures))
        capture['artifact_count'] = len(capture['artifacts'])
    unique_dates = list(_unique(capture_dates))
    if unique_dates:
        capture['dates'] = sorted(unique_dates)
    unique_ids = list(_unique(capture_ids))
    if unique_ids:
        capture['ids'] = sorted(unique_ids)

    return {'capture': capture} if capture else {}


def _hint_from_filename(ahs_source: Optional[Path]) -> Dict[str, object]:
    if ahs_source is None:
        return {}

    name = ahs_source.name
    if not name:
        return {}

    capture: Dict[str, object] = {'source': name}
    id_match = re.search(r'(\d{5,})', name)
    if id_match:
        capture['bundle_ids'] = [id_match.group(1)]

    return {'capture': capture}


def _find_case_insensitive(root: Path, target: str) -> Optional[Path]:
    lowered = target.lower()
    for candidate in root.rglob('*'):
        if candidate.name.lower() == lowered:
            return candidate
    return None


def _merge_capture(dest: Dict[str, object], src: Dict[str, object]) -> None:
    for key, value in src.items():
        if value in (None, ''):
            continue
        if key in {'artifacts', 'dates', 'ids', 'bundle_ids'}:
            items = list(value) if isinstance(value, (list, tuple)) else [value]
            existing = dest.setdefault(key, [])
            for item in items:
                if item not in existing:
                    existing.append(item)
        elif key == 'artifact_count':
            existing_count = dest.get('artifact_count', 0)
            if isinstance(value, int) and value > existing_count:
                dest['artifact_count'] = value
        else:
            dest[key] = value

    if 'artifacts' in dest:
        dest['artifact_count'] = len(dest['artifacts'])
    for ordered in ('dates', 'ids', 'bundle_ids'):
        if ordered in dest:
            dest[ordered] = sorted(dict.fromkeys(dest[ordered]))


def extract_identity(extract_dir: Path, ahs_source: Optional[Path]) -> Dict[str, object]:
    identity: Dict[str, object] = {}

    bcert = _find_case_insensitive(extract_dir, 'bcert.pkg.xml')
    if bcert is not None:
        bcert_data = _parse_bcert(bcert)
        if bcert_data.get('model'):
            identity['model'] = bcert_data['model']
        if bcert_data.get('serial_number'):
            identity['serial_number'] = bcert_data['serial_number']
        if bcert_data.get('uuid'):
            identity['uuid'] = bcert_data['uuid']

        firmware = {}
        if bcert_data.get('firmware_system_rom'):
            firmware['system_rom'] = bcert_data['firmware_system_rom']
        if bcert_data.get('firmware_ilo'):
            firmware['ilo'] = bcert_data['firmware_ilo']
        if firmware:
            identity.setdefault('firmware', {}).update(firmware)

    filepkg = _find_case_insensitive(extract_dir, 'file.pkg.txt')
    if filepkg is not None:
        pkg_data = _parse_filepkg(filepkg)
        capture = pkg_data.get('capture')
        if isinstance(capture, dict) and capture:
            dest = identity.setdefault('capture', {})
            _merge_capture(dest, capture)

    hint_capture = _hint_from_filename(ahs_source).get('capture', {})
    if hint_capture:
        dest = identity.setdefault('capture', {})
        _merge_capture(dest, hint_capture)

    return identity


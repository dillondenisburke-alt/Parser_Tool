import datetime
import json
import os
from collections import Counter

from .redact import mask


def _redact(value, redactions):
    return mask(value, redactions) if isinstance(value, str) else value


def _exec_summary(events, findings, inventory, metadata):
    severity_counts = Counter((evt.get('severity') or 'INFO').upper() for evt in events)
    errors = severity_counts.get('ERROR', 0) + severity_counts.get('CRITICAL', 0)
    warns = severity_counts.get('WARN', 0)

    def has_level(level):
        return any((f.get('severity') or '').upper() == level for f in findings)

    if has_level('ERROR'):
        status = '🔴 Issues detected'
    elif has_level('WARN'):
        status = '🟠 Warnings detected'
    elif errors:
        status = '🟠 Elevated events detected'
    elif warns:
        status = '🟡 Warnings observed'
    else:
        status = '🟢 No issues detected'

    inventory_note = 'inventory detected' if inventory else 'inventory missing'
    if metadata.get('bb_parsed'):
        bb_note = '`.bb` parsed'
    elif metadata.get('bb_enabled'):
        bb_note = '`.bb` artifacts not found'
    else:
        bb_note = '`.bb` parsing disabled'

    return (
        f'**Executive Summary:** {status} — {errors} ERROR, {warns} WARN; '
        f'{inventory_note}; {bb_note}.'
    )


def _system_summary(identity, inventory, redactions):
    identity = identity or {}
    inventory = inventory or {}

    lines = ['## System Summary']

    model = identity.get('model') or inventory.get('ProductName')
    serial = identity.get('serial_number') or inventory.get('SerialNumber')
    uuid = identity.get('uuid') or inventory.get('UUID')

    firmware = identity.get('firmware') or {}
    rom = firmware.get('system_rom') or inventory.get('ROMVersion')
    ilo = firmware.get('ilo') or inventory.get('ILO')

    capture = identity.get('capture') or {}

    has_identity = any([model, serial, uuid, rom, ilo, capture])

    if not has_identity:
        lines.append('- _No identity information available._')
        return lines

    if model:
        lines.append(f'- **Model:** {_redact(model, redactions)}')
    if serial:
        lines.append(f'- **Serial Number:** {_redact(serial, redactions)}')
    if uuid:
        lines.append(f'- **UUID:** {_redact(uuid, redactions)}')

    firmware_bits = []
    if rom:
        firmware_bits.append(f'System ROM {_redact(rom, redactions)}')
    if ilo:
        firmware_bits.append(f'iLO {_redact(ilo, redactions)}')
    if firmware_bits:
        lines.append(f"- **Firmware:** {'; '.join(firmware_bits)}")

    if capture:
        capture_parts = []
        count = capture.get('artifact_count')
        artifacts = capture.get('artifacts') or []
        if count is None and artifacts:
            count = len(artifacts)
        if count:
            capture_parts.append(f'{count} capture file(s)')
        dates = capture.get('dates') or []
        if dates:
            capture_parts.append('dates ' + ', '.join(dates[:3]) + (' …' if len(dates) > 3 else ''))
        ids = capture.get('ids') or capture.get('bundle_ids') or []
        if ids:
            capture_parts.append('IDs ' + ', '.join(ids[:3]) + (' …' if len(ids) > 3 else ''))
        source = capture.get('source')
        if source:
            capture_parts.append(f"source {_redact(source, redactions)}")
        if artifacts and not count:
            sample = ', '.join(_redact(a, redactions) for a in artifacts[:2])
            capture_parts.append(f'sample {sample}')
        elif artifacts and count and len(artifacts) < count:
            sample = ', '.join(_redact(a, redactions) for a in artifacts[:2])
            capture_parts.append(f'sample {sample}')
        elif artifacts and len(artifacts) <= 2:
            sample = ', '.join(_redact(a, redactions) for a in artifacts)
            capture_parts.append(f'files {sample}')

        if capture_parts:
            lines.append(f"- **Capture:** {', '.join(capture_parts)}")

    return lines


def write_markdown(
    summary,
    inventory,
    events,
    diagnostics,
    out_path,
    redactions,
    *,
    findings=None,
    metadata=None,
    identity=None,
):
    findings = findings or []
    metadata = metadata or {}
    events = events or []

    timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    lines = ['# AHS Diagnostic Parser Report', f'_Generated: {timestamp}_', '']
    lines.extend(_system_summary(identity, inventory, redactions))
    lines.append('')
    lines.append(
        _exec_summary(events=events, findings=findings, inventory=inventory, metadata=metadata)
    )
    lines.append('')

    lines.extend(['| Finding | Severity | Confidence |', '|---|---|---|'])
    if findings:
        for entry in findings:
            title = entry.get('finding', 'Finding')
            if entry.get('timestamp'):
                title = f"{title} ({entry['timestamp']})"
            lines.append(
                f"| {_redact(title, redactions)} | "
                f"{entry.get('severity', 'INFO')} | {entry.get('confidence', 'Medium')} |"
            )
    else:
        default_row = (
            'ℹ️ Inventory detected' if inventory else 'ℹ️ No actionable faults detected'
        )
        lines.append(f'| {default_row} | INFO | High |')

    if findings:
        lines.extend(['', '### Finding Details'])
        for entry in findings:
            detail = _redact(entry.get('details', ''), redactions)
            source = entry.get('source')
            timestamp_detail = entry.get('timestamp')
            suffix_bits = []
            if source:
                suffix_bits.append(f'source: {_redact(source, redactions)}')
            if timestamp_detail:
                suffix_bits.append(f'timestamp: {timestamp_detail}')
            suffix = f" ({'; '.join(suffix_bits)})" if suffix_bits else ''
            lines.append(
                f"- **{entry.get('severity', 'INFO')}** {_redact(entry.get('finding', ''), redactions)}: "
                f"{detail}{suffix}"
            )

    lines.extend(['', '## System Inventory'])
    for key in ('ProductName', 'SerialNumber', 'ROMVersion', 'ILO'):
        value = _redact(inventory.get(key), redactions)
        if value:
            lines.append(f'- **{key}:** {value}')
    if not inventory:
        lines.append('- _Inventory details unavailable from provided artifacts._')

    lines.extend(['', '## Discovered Files'])
    for item in summary.get('files', []):
        lines.append(f'- {_redact(item, redactions)}')
    if not summary.get('files'):
        lines.append('- _No file inventory available._')

    lines.extend(['', '## Diagnostics'])
    counters = (diagnostics.get('counters') or {}) if diagnostics else {}
    if counters:
        for key, value in counters.items():
            lines.append(f'- {key}: {value}')
    else:
        lines.append('- _No diagnostic counters available._')

    if metadata.get('bb_enabled'):
        lines.extend(['', '## BB Scan Summary'])
        if metadata.get('bb_parsed'):
            high_priority = [
                evt
                for evt in events
                if (evt.get('severity') or 'INFO').upper() in {'ERROR', 'WARN'}
            ]
            sample = high_priority[:10] or events[:5]
            if sample:
                for evt in sample:
                    message = _redact(evt.get('message', ''), redactions)
                    prefix = (evt.get('severity') or 'INFO').upper()
                    source = evt.get('source')
                    ts = evt.get('timestamp')
                    suffix_parts = []
                    if source:
                        suffix_parts.append(f'source: {_redact(source, redactions)}')
                    if ts:
                        suffix_parts.append(f'timestamp: {ts}')
                    suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ''
                    lines.append(f'- [{prefix}] {message}{suffix}')
            else:
                lines.append('- BB artifacts parsed but contained no readable events.')
        else:
            if metadata.get('artifact_count', 0) == 0:
                lines.append('- No `.bb` artifacts were discovered in the bundle.')
            else:
                lines.append('- `.bb` parsing was disabled for this run.')

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'wt', encoding='utf-8') as handle:
        handle.write('\n'.join(lines))


def dump_json(obj, path):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'wt', encoding='utf-8') as handle:
        handle.write(json.dumps(obj, indent=2, ensure_ascii=False))

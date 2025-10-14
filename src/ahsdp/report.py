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
):
    findings = findings or []
    metadata = metadata or {}
    events = events or []

    timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    lines = ['# AHS Diagnostic Parser Report', f'_Generated: {timestamp}_', '']
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
        for component in sorted(counters):
            value = counters[component]
            if isinstance(value, dict):
                lines.append(f"- **{component.replace('_', ' ').title()}**")
                for metric in sorted(value):
                    metric_value = value[metric]
                    label = metric.replace('_', ' ')
                    lines.append(f"  - {label}: {metric_value}")
            else:
                lines.append(f'- {component}: {value}')
        unknown = diagnostics.get('unknown_offsets') if diagnostics else None
        if unknown:
            lines.append('- _Unmapped Offsets:_')
            for offset, value in sorted(unknown.items()):
                lines.append(f'  - {offset}: {value}')
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

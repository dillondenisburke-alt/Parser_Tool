import datetime
import json
import os
from collections import Counter


DEFAULT_COMPONENTS = (
    'System Board',
    'Power Supply',
    'Cooling',
    'Storage',
    'Networking',
)

SEVERITY_DISPLAY_ORDER = ('CRITICAL', 'ERROR', 'WARN', 'INFO')


def _normalise_severity(value):
    if not value:
        return 'INFO'
    upper = str(value).upper()
    if upper == 'CRIT':
        return 'CRITICAL'
    return upper


def _component_has_base_telemetry(component, metadata, events):
    if component == 'System Board':
        return (
            metadata.get('faults_enabled', False)
            and metadata.get('bb_enabled', False)
            and metadata.get('bb_parsed', False)
            and bool(events)
        )
    return False


def build_component_matrix(findings, metadata, events):
    findings = findings or []
    metadata = metadata or {}
    events = events or []

    component_map = {}
    for entry in findings:
        component = entry.get('component') or 'General'
        component_map.setdefault(component, []).append(entry)

    components = list(DEFAULT_COMPONENTS)
    for component in component_map:
        if component not in components:
            components.append(component)

    matrix = {}
    for component in components:
        component_entries = component_map.get(component, [])
        counts = Counter()
        for entry in component_entries:
            counts[_normalise_severity(entry.get('severity', 'INFO'))] += 1

        telemetry_present = bool(component_entries) or _component_has_base_telemetry(
            component, metadata, events
        )

        if counts.get('ERROR') or counts.get('CRITICAL'):
            status = 'error'
        elif counts.get('WARN'):
            status = 'warn'
        elif component_entries:
            status = 'ok'
        else:
            status = 'ok' if telemetry_present else 'missing'

        entry = {'status': status}
        if counts:
            entry['counts'] = dict(counts)
            entry['total_findings'] = sum(counts.values())
        if not telemetry_present:
            entry['telemetry'] = 'missing'
        matrix[component] = entry

    return matrix


def _format_component_summary(component, entry):
    status = entry.get('status', 'missing')
    total = entry.get('total_findings', 0)
    counts = entry.get('counts', {})

    severity_bits = []
    for level in SEVERITY_DISPLAY_ORDER:
        if counts.get(level):
            severity_bits.append(f"{level}×{counts[level]}")

    if total:
        finding_label = 'finding' if total == 1 else 'findings'
        detail = f"{total} {finding_label}"
        if severity_bits:
            detail = f"{detail} ({', '.join(severity_bits)})"
    else:
        detail = 'No issues detected'

    if status == 'missing':
        detail = f'{detail} / data missing'

    prefix = {'error': '🔴', 'warn': '🟠', 'ok': '🟢', 'missing': '⚪'}.get(status, '⚪')
    return f"- {prefix} **{component}:** {detail}"

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

    component_matrix = metadata.get('component_matrix') or build_component_matrix(
        findings, metadata, events
    )
    lines.append('## Hardware Fault Summary')
    if component_matrix:
        for component, entry in component_matrix.items():
            lines.append(_format_component_summary(component, entry))
    else:
        lines.append('- _No component telemetry available._')
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

"""Utilities for decoding and evaluating non-BB diagnostic counters."""
from __future__ import annotations

import struct
from typing import Dict, Iterable, List, Tuple

# Description of known diagnostic counter offsets. Each entry describes the
# component the value belongs to, the metric name we expose in the public schema,
# and optional evaluation metadata so anomalies can be surfaced as findings.
COUNTER_LAYOUT: List[Dict[str, object]] = [
    {
        'offset': 0x00,
        'component': 'storage',
        'metric': 'write_errors',
        'description': 'Storage write error events',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'High',
    },
    {
        'offset': 0x04,
        'component': 'storage',
        'metric': 'read_errors',
        'description': 'Storage read error events',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'High',
    },
    {
        'offset': 0x08,
        'component': 'storage',
        'metric': 'uncorrectable_errors',
        'description': 'Uncorrectable media errors',
        'type': 'counter',
        'threshold': 0,
        'severity': 'ERROR',
        'confidence': 'High',
    },
    {
        'offset': 0x0C,
        'component': 'storage',
        'metric': 'dropped_io',
        'description': 'Dropped I/O operations',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x10,
        'component': 'fan',
        'metric': 'tach_faults',
        'description': 'Fan tachometer faults',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x14,
        'component': 'fan',
        'metric': 'stall_events',
        'description': 'Fan stall events',
        'type': 'counter',
        'threshold': 0,
        'severity': 'ERROR',
        'confidence': 'High',
    },
    {
        'offset': 0x18,
        'component': 'power',
        'metric': 'psu_failures',
        'description': 'Power supply failures',
        'type': 'counter',
        'threshold': 0,
        'severity': 'ERROR',
        'confidence': 'High',
    },
    {
        'offset': 0x1C,
        'component': 'power',
        'metric': 'voltage_low_events',
        'description': 'Low input voltage events',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x20,
        'component': 'thermal',
        'metric': 'ambient_celsius',
        'description': 'Ambient temperature (°C)',
        'type': 'telemetry',
        'range': (10, 45),
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x24,
        'component': 'thermal',
        'metric': 'cpu_celsius',
        'description': 'CPU temperature (°C)',
        'type': 'telemetry',
        'range': (10, 85),
        'severity': 'ERROR',
        'confidence': 'Medium',
    },
    {
        'offset': 0x28,
        'component': 'thermal',
        'metric': 'inlet_celsius',
        'description': 'Inlet temperature (°C)',
        'type': 'telemetry',
        'range': (5, 45),
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x2C,
        'component': 'network',
        'metric': 'link_down_events',
        'description': 'Network link down events',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x30,
        'component': 'network',
        'metric': 'packet_errors',
        'description': 'Packet error count',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'offset': 0x34,
        'component': 'firmware',
        'metric': 'update_failures',
        'description': 'Firmware update failures',
        'type': 'counter',
        'threshold': 0,
        'severity': 'ERROR',
        'confidence': 'High',
    },
    {
        'offset': 0x38,
        'component': 'firmware',
        'metric': 'rollback_events',
        'description': 'Firmware rollback events',
        'type': 'counter',
        'threshold': 0,
        'severity': 'WARN',
        'confidence': 'Medium',
    },
]


def _known_offsets() -> Iterable[int]:
    for entry in COUNTER_LAYOUT:
        yield int(entry['offset'])


def decode_counters(buffer: bytes) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int], int]:
    """Decode counters.pkg content into a normalised schema.

    Returns a tuple of:
        - nested counters grouped by component
        - a mapping of unknown offsets (hex) to values for observability
        - the count of trailing bytes that could not be parsed as 32-bit values
    """

    counters: Dict[str, Dict[str, int]] = {}
    unknown: Dict[str, int] = {}

    known_offsets = set(_known_offsets())
    length = len(buffer)
    for entry in COUNTER_LAYOUT:
        offset = int(entry['offset'])
        if offset + 4 > length:
            continue
        value = struct.unpack_from('<I', buffer, offset)[0]
        component = str(entry['component'])
        metric = str(entry['metric'])
        counters.setdefault(component, {})[metric] = value

    max_aligned = length - (length % 4)
    for offset in range(0, max_aligned, 4):
        if offset in known_offsets:
            continue
        value = struct.unpack_from('<I', buffer, offset)[0]
        if value:
            unknown[f'0x{offset:04x}'] = value

    trailing = length % 4
    return counters, unknown, trailing


def evaluate_diagnostic_findings(diagnostics: Dict[str, object] | None) -> List[Dict[str, object]]:
    """Generate findings from decoded diagnostic counters."""

    if not diagnostics:
        return []

    counters = diagnostics.get('counters') if isinstance(diagnostics, dict) else None
    if not counters or not isinstance(counters, dict):
        return []

    findings: List[Dict[str, object]] = []
    for entry in COUNTER_LAYOUT:
        component = str(entry['component'])
        metric = str(entry['metric'])
        component_counters = counters.get(component)
        if not isinstance(component_counters, dict):
            continue
        if metric not in component_counters:
            continue
        value = component_counters[metric]
        metric_type = entry.get('type', 'counter')
        description = str(entry.get('description') or metric.replace('_', ' '))
        severity = str(entry.get('severity', 'WARN'))
        confidence = str(entry.get('confidence', 'Medium'))
        finding_base = {
            'component': component,
            'severity': severity,
            'confidence': confidence,
            'source': 'diagnostics:counters.pkg',
        }

        if metric_type == 'telemetry':
            range_tuple = entry.get('range')
            if not isinstance(range_tuple, tuple) or len(range_tuple) != 2:
                continue
            lower, upper = range_tuple
            if lower is None or upper is None:
                continue
            if value < lower or value > upper:
                direction = 'below' if value < lower else 'above'
                finding = {
                    **finding_base,
                    'finding': f'{description} telemetry out of range',
                    'details': (
                        f'{description} reading {value} is {direction} the expected '
                        f'range {lower}-{upper}. '
                        'Check thermal conditions and sensor health.'
                    ),
                }
                findings.append(finding)
        else:
            threshold = int(entry.get('threshold', 0))
            if value > threshold:
                finding = {
                    **finding_base,
                    'finding': f'{description} counter exceeded threshold',
                    'details': (
                        f'{description} reported {value} which exceeds '
                        f'allowed threshold {threshold}. '
                        'Investigate the component for faults.'
                    ),
                }
                findings.append(finding)

    return findings

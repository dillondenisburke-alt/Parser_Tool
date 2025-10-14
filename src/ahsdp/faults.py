import re
from typing import Dict, Iterable, List, Optional

BOARD_PATTERNS = [
    r"\bSystem Board\b",
    r"\bSYSBOARD\b",
    r"\bBoard Failure\b",
    r"\bFRU\b.*Board",
    r"\bPOST Error\b.*(system|board)",
    r"\bUnrecoverable\b.*(system|board)",
    r"\bPCH\b",
    r"\bPCIe Bus Fatal\b",
    r"\biLO Health Subsystem\b",
    r"\bKBBX BOOT\b",
]

_ERROR_HINTS = re.compile(r"\b(CRIT|CRITICAL|FATAL|UNREC|ERROR|FAIL|PANIC)\b", re.I)

_SEVERITY_ORDER = {"INFO": 0, "WARN": 1, "ERROR": 2, "CRITICAL": 3}

_HARDWARE_PATTERNS = [
    {
        'pattern': r"\b(Power\s+Supply|PSU)\b.*(fail|fault|error|removed)",
        'finding': 'Power supply failure detected',
        'component': 'Power Supply',
        'severity': 'ERROR',
        'confidence': 'High',
    },
    {
        'pattern': r"\bFan\b.*(degrad|fault|fail|error)",
        'finding': 'Cooling fan issue detected',
        'component': 'Cooling',
        'severity': 'WARN',
        'confidence': 'Medium',
    },
    {
        'pattern': r"\bDIMM\b.*(uncorrectable|fatal|error|fail)",
        'finding': 'Memory DIMM error recorded',
        'component': 'Memory',
        'severity': 'ERROR',
        'confidence': 'High',
    },
    {
        'pattern': r"\bDisk\b.*(write fault|write error|predictive failure|media error)",
        'finding': 'Disk write fault reported',
        'component': 'Storage',
        'severity': 'ERROR',
        'confidence': 'Medium',
    },
]


def _snippet(message: str) -> str:
    return message if len(message) <= 300 else message[:297] + '...'


def _coalesce_severity(record_level: Optional[str], default: str) -> str:
    record = (record_level or '').upper()
    default = default.upper()
    if record not in _SEVERITY_ORDER:
        return default
    if _SEVERITY_ORDER[record] >= _SEVERITY_ORDER.get(default, 0):
        return record
    return default


def _base_finding(
    record: dict,
    message: str,
    *,
    finding: str,
    severity: str,
    confidence: str,
    component: Optional[str] = None,
) -> dict:
    entry = {
        'finding': finding,
        'details': _snippet(message),
        'severity': _coalesce_severity(record.get('severity'), severity),
        'confidence': confidence,
        'source': record.get('source'),
    }
    if record.get('timestamp'):
        entry['timestamp'] = record['timestamp']
    if component:
        entry['component'] = component
    return entry


def detect_board_faults(records: Iterable[dict]) -> List[dict]:
    findings: List[dict] = []
    for rec in records:
        message = rec.get('message', '')
        if not message:
            continue
        if not any(re.search(pattern, message, re.I) for pattern in BOARD_PATTERNS):
            continue
        sev = (rec.get('severity') or 'INFO').upper()
        level = 'ERROR' if sev in ('ERROR', 'CRITICAL') or _ERROR_HINTS.search(message) else 'WARN'
        findings.append(
            _base_finding(
                rec,
                message,
                finding='System board anomaly detected',
                severity=level,
                confidence='High',
                component='System Board',
            )
        )
    return findings


def _detect_from_records(records: Iterable[dict]) -> List[dict]:
    findings: List[dict] = []
    for rec in records:
        message = rec.get('message', '')
        if not message:
            continue
        for rule in _HARDWARE_PATTERNS:
            if re.search(rule['pattern'], message, re.I):
                findings.append(
                    _base_finding(
                        rec,
                        message,
                        finding=rule['finding'],
                        severity=rule['severity'],
                        confidence=rule['confidence'],
                        component=rule.get('component'),
                    )
                )
                break
    return findings


def _detect_from_diagnostics(diagnostics: Optional[Dict]) -> List[dict]:
    if not diagnostics:
        return []
    counters = diagnostics.get('counters', {}) if isinstance(diagnostics, dict) else {}
    findings: List[dict] = []
    if isinstance(counters, dict):
        write_errors = counters.get('write_errors')
        if isinstance(write_errors, int) and write_errors > 0:
            severity = 'WARN' if write_errors < 10 else 'ERROR'
            finding = {
                'finding': 'Disk write error counter incremented',
                'details': f"Controller reported {write_errors} write error(s)",
                'severity': severity,
                'confidence': 'Medium',
                'component': 'Storage',
            }
            source = diagnostics.get('_source') if isinstance(diagnostics, dict) else None
            if source:
                finding['source'] = source
            findings.append(finding)
    return findings


def detect_hardware_faults(records: Iterable[dict], diagnostics: Optional[Dict] = None) -> List[dict]:
    """Analyse records and diagnostics for notable hardware faults."""

    findings: List[dict] = []
    findings.extend(_detect_from_records(records))
    findings.extend(_detect_from_diagnostics(diagnostics))
    # Ensure legacy board detection is retained for callers that rely on it.
    findings.extend(detect_board_faults(records))
    return findings

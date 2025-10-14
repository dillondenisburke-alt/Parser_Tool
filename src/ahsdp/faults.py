import re

BOARD_PATTERNS = [
    r'\bSystem Board\b',
    r'\bSYSBOARD\b',
    r'\bBoard Failure\b',
    r'\bFRU\b.*Board',
    r'\bPOST Error\b.*(system|board)',
    r'\bUnrecoverable\b.*(system|board)',
    r'\bPCH\b',
    r'\bPCIe Bus Fatal\b',
    r'\biLO Health Subsystem\b',
    r'\bKBBX BOOT\b',
]

_ERROR_HINTS = re.compile(r'\b(CRIT|CRITICAL|FATAL|UNREC|ERROR|FAIL|PANIC)\b', re.I)


def detect_board_faults(records):
    findings = []
    for rec in records:
        message = rec.get('message', '')
        if not message:
            continue
        if not any(re.search(pattern, message, re.I) for pattern in BOARD_PATTERNS):
            continue
        sev = (rec.get('severity') or 'INFO').upper()
        level = 'ERROR' if sev in ('ERROR', 'CRITICAL') or _ERROR_HINTS.search(message) else 'WARN'
        snippet = message if len(message) <= 300 else message[:297] + '...'
        finding = {
            'finding': 'System board anomaly detected',
            'details': snippet,
            'severity': level,
            'confidence': 'High',
            'source': rec.get('source'),
            'component': 'System Board',
        }
        if rec.get('timestamp'):
            finding['timestamp'] = rec['timestamp']
        findings.append(finding)
    return findings

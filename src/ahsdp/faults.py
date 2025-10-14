import re
from typing import Dict, List


_ERROR_HINTS = re.compile(r'\b(CRIT|CRITICAL|FATAL|UNREC|ERROR|FAIL|PANIC)\b', re.I)

_SEVERITY_ORDER = ['INFO', 'WARN', 'ERROR', 'CRITICAL']


def _normalise_sources(raw_source):
    if not raw_source:
        return []
    if isinstance(raw_source, (list, tuple, set)):
        return [str(item) for item in raw_source if item]
    return [str(raw_source)]


def _coerce_severity(*levels: str) -> str:
    ranking = {level: index for index, level in enumerate(_SEVERITY_ORDER)}
    winner = 'INFO'
    for level in levels:
        if not level:
            continue
        normalised = str(level).upper()
        if normalised not in ranking:
            continue
        if ranking[normalised] > ranking[winner]:
            winner = normalised
    return winner


HARDWARE_RULES: Dict[str, Dict] = {
    'system_board': {
        'component': 'System Board',
        'patterns': [
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
        ],
        'finding': '{component} anomaly detected',
        'default_severity': 'WARN',
        'confidence': 'High',
    },
    'cpu': {
        'component': 'CPU',
        'patterns': [
            r'\bCPU\b',
            r'\bProcessor\b',
            r'\bAPIC\b',
            r'\bCore(?:\s+\d+)?\b',
        ],
        'finding': '{component} anomaly detected',
        'default_severity': 'WARN',
        'confidence': 'Medium',
    },
    'memory': {
        'component': 'Memory',
        'patterns': [
            r'\bDIMM\b',
            r'\bMemory\b',
            r'\bECC\b',
            r'\bUncorrectable Memory\b',
        ],
        'finding': '{component} fault detected',
        'default_severity': 'WARN',
        'confidence': 'Medium',
    },
    'power_supply': {
        'component': 'Power Supply',
        'patterns': [
            r'\bPower Supply\b',
            r'\bPSU\b',
            r'\bPower Unit\b',
            r'\bPower Failure\b',
        ],
        'finding': '{component} issue detected',
        'default_severity': 'ERROR',
        'confidence': 'Medium',
    },
}


def _matches_rule(message: str, rule: Dict) -> bool:
    return any(re.search(pattern, message, re.I) for pattern in rule.get('patterns', []))


def detect_hardware_faults(records: List[dict]):
    findings: List[dict] = []
    for rec in records:
        message = rec.get('message') or ''
        if not message:
            continue

        sev = (rec.get('severity') or 'INFO').upper()
        has_error_hint = bool(_ERROR_HINTS.search(message))
        escalation = 'CRITICAL' if sev == 'CRITICAL' else 'ERROR' if sev == 'ERROR' or has_error_hint else 'WARN'

        snippet = message if len(message) <= 300 else message[:297] + '...'

        for rule_key, rule in HARDWARE_RULES.items():
            if not _matches_rule(message, rule):
                continue

            base_severity = (rule.get('default_severity') or 'WARN').upper()
            final_severity = _coerce_severity('INFO', base_severity, escalation)
            confidence = rule.get('confidence', 'Medium')
            finding_text = rule.get('finding', '{component} anomaly detected').format(
                component=rule.get('component', rule_key.replace('_', ' ').title())
            )

            finding = {
                'finding': finding_text,
                'details': snippet,
                'severity': final_severity,
                'confidence': confidence,
                'component': rule.get('component', rule_key.replace('_', ' ').title()),
                'source': rec.get('source'),
                'sources': _normalise_sources(rec.get('source')),
            }
            if rec.get('timestamp'):
                finding['timestamp'] = rec['timestamp']
            findings.append(finding)
    return findings

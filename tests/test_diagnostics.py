import json
import struct

import pytest

from src.ahsdp.core import run_parser
from src.ahsdp.diagnostics import COUNTER_LAYOUT, evaluate_diagnostic_findings
from src.ahsdp.parse_nonbb import parse_counters_pkg


@pytest.fixture()
def sample_counter_bytes():
    size = max(int(entry['offset']) for entry in COUNTER_LAYOUT) + 4
    buffer = bytearray(size)
    overrides = {
        ('storage', 'write_errors'): 3,
        ('fan', 'tach_faults'): 2,
        ('thermal', 'ambient_celsius'): 55,  # out of range
        ('thermal', 'cpu_celsius'): 95,  # out of range
        ('power', 'psu_failures'): 1,
    }
    for entry in COUNTER_LAYOUT:
        offset = int(entry['offset'])
        value = overrides.get((entry['component'], entry['metric']), 0)
        struct.pack_into('<I', buffer, offset, value)
    return bytes(buffer)


@pytest.fixture()
def diagnostics_payload(tmp_path, sample_counter_bytes):
    path = tmp_path / 'counters.pkg'
    path.write_bytes(sample_counter_bytes)
    return parse_counters_pkg(path)


def test_parse_counters_pkg_decodes_known_offsets(diagnostics_payload, sample_counter_bytes):
    counters = diagnostics_payload['counters']

    assert counters['storage']['write_errors'] == 3
    assert counters['fan']['tach_faults'] == 2
    assert counters['thermal']['ambient_celsius'] == 55
    assert diagnostics_payload['bytes'] == len(sample_counter_bytes)


def test_evaluate_diagnostic_findings_flags_anomalies(diagnostics_payload):
    findings = evaluate_diagnostic_findings(diagnostics_payload)

    components = {entry['component'] for entry in findings}
    assert 'storage' in components
    assert 'thermal' in components
    assert any('write error' in entry['finding'].lower() for entry in findings)
    assert any(entry['severity'] == 'ERROR' for entry in findings)


def test_run_parser_exports_diagnostic_findings(tmp_path, sample_counter_bytes):
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    (bundle / 'counters.pkg').write_bytes(sample_counter_bytes)

    export_dir = tmp_path / 'export'
    report_dir = tmp_path / 'report_dir'

    result = run_parser(str(bundle), str(report_dir), export_dir=str(export_dir))

    assert result['findings'], 'expected diagnostic findings to be emitted'
    assert any(entry['component'] == 'thermal' for entry in result['findings'])

    findings_path = export_dir / 'findings.json'
    diagnostics_path = export_dir / 'diagnostics.json'

    exported_findings = json.loads(findings_path.read_text())
    assert exported_findings == result['findings']

    exported_diagnostics = json.loads(diagnostics_path.read_text())
    assert exported_diagnostics['counters']['storage']['write_errors'] == 3

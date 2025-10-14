from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ahsdp.faults import detect_hardware_faults
from ahsdp.parse_bb import parse_bb_files


FIXTURES = Path(__file__).parent / 'fixtures' / 'demo_data'


def test_parse_bb_extracts_records():
    bb_path = FIXTURES / 'sample.bb'
    result = parse_bb_files([bb_path])
    assert result['records'], 'expected records to be extracted'
    first = result['records'][0]
    assert first['severity'] == 'ERROR'
    assert 'System Board' in first['message']


def test_detect_hardware_faults_flags_board_issue():
    bb_path = FIXTURES / 'sample.bb'
    records = parse_bb_files([bb_path])['records']
    findings = detect_hardware_faults(records)
    assert findings, 'expected hardware fault detection'
    assert findings[0]['severity'] == 'ERROR'
    assert findings[0]['component'] == 'System Board'


def test_detect_hardware_faults_multi_component():
    records = [
        {'message': 'Power Supply Failure detected in PSU bay 1', 'severity': 'WARN', 'source': 'log'},
        {'message': 'Corrected ECC error on DIMM B1', 'severity': 'INFO', 'source': 'log'},
    ]
    findings = detect_hardware_faults(records)
    components = {finding['component'] for finding in findings}
    assert 'Power Supply' in components
    assert 'Memory' in components

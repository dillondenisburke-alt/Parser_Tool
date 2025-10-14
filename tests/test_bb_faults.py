from pathlib import Path

from src.ahsdp.faults import detect_board_faults
from src.ahsdp.parse_bb import parse_bb_files


FIXTURES = Path(__file__).parent / 'fixtures' / 'demo_data'


def test_parse_bb_extracts_records():
    bb_path = FIXTURES / 'sample.bb'
    result = parse_bb_files([bb_path])
    assert result['records'], 'expected records to be extracted'
    first = result['records'][0]
    assert first['severity'] == 'ERROR'
    assert 'System Board' in first['message']


def test_detect_board_faults_flags_board_issue():
    bb_path = FIXTURES / 'sample.bb'
    records = parse_bb_files([bb_path])['records']
    findings = detect_board_faults(records)
    assert findings, 'expected board fault detection'
    assert findings[0]['severity'] == 'ERROR'
    assert 'System board anomaly' in findings[0]['finding']

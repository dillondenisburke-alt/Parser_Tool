from src.ahsdp.report import write_markdown


def test_report_includes_system_summary(tmp_path):
    out_path = tmp_path / 'report.md'
    identity = {
        'model': 'Widget 2000',
        'serial_number': 'SN123',
        'uuid': 'uuid-1234',
        'firmware': {'system_rom': 'ROM 1.0', 'ilo': 'iLO 2.0'},
        'capture': {
            'artifact_count': 1,
            'artifacts': ['0001-2024-02-01.bb'],
            'dates': ['2024-02-01'],
            'source': 'Case_AHS.zip',
        },
    }

    write_markdown(
        summary={'files': []},
        inventory={},
        events=[],
        diagnostics={},
        out_path=out_path,
        redactions=[],
        findings=[],
        metadata={},
        identity=identity,
    )

    text = out_path.read_text(encoding='utf-8')
    assert '## System Summary' in text
    assert '**Model:** Widget 2000' in text
    assert '**Serial Number:** SN123' in text
    assert '**UUID:** uuid-1234' in text
    assert '**Firmware:** System ROM ROM 1.0; iLO iLO 2.0' in text
    assert '**Capture:** 1 capture file(s), dates 2024-02-01' in text
    assert 'source Case_AHS.zip' in text

    system_idx = text.index('## System Summary')
    exec_idx = text.index('**Executive Summary:**')
    assert system_idx < exec_idx


def test_report_system_summary_uses_inventory_fallback(tmp_path):
    out_path = tmp_path / 'report.md'

    write_markdown(
        summary={'files': []},
        inventory={'ProductName': 'Fallback Model', 'SerialNumber': 'SN999'},
        events=[],
        diagnostics={},
        out_path=out_path,
        redactions=[],
        findings=[],
        metadata={},
        identity={},
    )

    text = out_path.read_text(encoding='utf-8')
    assert '**Model:** Fallback Model' in text
    assert '**Serial Number:** SN999' in text

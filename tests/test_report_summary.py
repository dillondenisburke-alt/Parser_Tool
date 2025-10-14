from src.ahsdp.report import build_component_matrix, write_markdown


def test_component_matrix_marks_error_and_missing():
    metadata = {'bb_enabled': True, 'bb_parsed': True, 'faults_enabled': True}
    events = [{'message': 'System Board failure', 'severity': 'ERROR'}]
    findings = [
        {
            'finding': 'System board anomaly detected',
            'severity': 'ERROR',
            'confidence': 'High',
            'component': 'System Board',
        }
    ]

    matrix = build_component_matrix(findings, metadata, events)

    assert matrix['System Board']['status'] == 'error'
    assert matrix['System Board']['counts']['ERROR'] == 1
    assert matrix['Power Supply']['status'] == 'missing'


def test_write_markdown_includes_hardware_summary(tmp_path):
    report_path = tmp_path / 'report.md'
    findings = [
        {
            'finding': 'Board warning',
            'severity': 'WARN',
            'confidence': 'Medium',
            'component': 'System Board',
        }
    ]
    metadata = {'bb_enabled': True, 'bb_parsed': True, 'faults_enabled': True}

    write_markdown(
        summary={'files': []},
        inventory={},
        events=[{'message': 'System Board caution', 'severity': 'WARN'}],
        diagnostics={},
        out_path=str(report_path),
        redactions=[],
        findings=findings,
        metadata=metadata,
    )

    contents = report_path.read_text(encoding='utf-8')
    assert '## Hardware Fault Summary' in contents
    assert 'System Board' in contents
    assert 'Power Supply' in contents
    assert 'data missing' in contents

from pathlib import Path

from src.ahsdp.identity import extract_identity


def test_extract_identity_combines_sources():
    fixture_dir = Path('tests/fixtures/demo_data')

    identity = extract_identity(fixture_dir, Path('CASE123456_AHS.zip'))

    assert identity['model'] == 'ProLiant DL380 Gen10'
    assert identity['serial_number'] == 'ABC1234DEF'
    assert identity['firmware']['system_rom'] == 'U32 v2.72'
    assert identity['firmware']['ilo'] == 'iLO 5 v2.77'

    capture = identity['capture']
    assert capture['artifact_count'] == 2
    assert capture['artifacts'] == [
        '0002382-2019-09-02.bb',
        '0002383-2019-09-03.bb',
    ]
    assert capture['dates'] == ['2019-09-02', '2019-09-03']
    assert capture['source'] == 'CASE123456_AHS.zip'
    assert capture['bundle_ids'] == ['123456']


def test_extract_identity_handles_missing_files(tmp_path):
    identity = extract_identity(tmp_path, None)
    assert identity == {}

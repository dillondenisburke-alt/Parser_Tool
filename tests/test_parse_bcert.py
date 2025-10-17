from importlib import util
from pathlib import Path

from src.ahsdp.parse_nonbb import parse_bcert


def _load_demo_generator():
    module_path = Path(__file__).parent / "fixtures" / "demo_data_generator.py"
    spec = util.spec_from_file_location("demo_data_generator", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load demo_data_generator module")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_bcert_populates_inventory(tmp_path):
    generator = _load_demo_generator()
    xml_path = generator.create_bcert_xml(tmp_path)

    parsed = parse_bcert(xml_path)

    for key, value in generator.EXPECTED_BCERT_METADATA.items():
        assert parsed[key] == value

    assert parsed["_source"] == Path(xml_path).name

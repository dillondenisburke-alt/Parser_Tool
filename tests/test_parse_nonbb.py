"""Smoke tests for parsing Non-BB customer info files."""

from pathlib import Path

from src.ahsdp.parse_nonbb import parse_cust_info


def create_cust_info_dat(tmp_path: Path) -> Path:
    """Create a demo CUST_INFO.DAT file with UTF-8 key=value lines."""
    lines = [
        "ContactEmail=customer@example.com",
        "ContactPhone=+1 555 123 4567",
        "Case=SR-123456",
    ]
    target = tmp_path / "CUST_INFO.DAT"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def test_parse_cust_info_returns_expected_fields(tmp_path):
    """parse_cust_info should extract all key=value fields from the fixture."""
    cust_info_path = create_cust_info_dat(tmp_path)

    result = parse_cust_info(cust_info_path)

    assert result["_source"] == "CUST_INFO.DAT"
    assert result["fields"] == {
        "ContactEmail": "customer@example.com",
        "ContactPhone": "+1 555 123 4567",
        "Case": "SR-123456",
    }

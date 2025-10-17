"""Utilities for synthesising demo AHS payloads used in tests."""

from pathlib import Path
from textwrap import dedent

BCERT_FILENAME = "bcert.pkg.xml"

EXPECTED_BCERT_METADATA = {
    "ProductName": "ProLiant DL380 Gen10",
    "SerialNumber": "CZJ12345AB",
    "ROMVersion": "U32 v2.72 (07/2024)",
    "ILO": "iLO 5 v2.77",
}


def create_bcert_xml(target_dir: Path) -> Path:
    """Create a demo BCERT XML file with inventory metadata fields.

    Parameters
    ----------
    target_dir:
        Directory that should contain the generated ``bcert.pkg.xml`` file.

    Returns
    -------
    Path
        Location of the generated XML file.
    """

    dest_dir = Path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    xml_path = dest_dir / BCERT_FILENAME

    xml_body = dedent(
        f"""
        <BCert>
          <ProductName>{EXPECTED_BCERT_METADATA['ProductName']}</ProductName>
          <SerialNumber>{EXPECTED_BCERT_METADATA['SerialNumber']}</SerialNumber>
          <ROMVersion>{EXPECTED_BCERT_METADATA['ROMVersion']}</ROMVersion>
          <ILOVersion>{EXPECTED_BCERT_METADATA['ILO']}</ILOVersion>
          <FactoryTests>PASS</FactoryTests>
          <ManufactureDate>2025-01-10</ManufactureDate>
        </BCert>
        """
    ).strip()

    xml_path.write_text(xml_body + "\n", encoding="utf-8")
    return xml_path


__all__ = ["BCERT_FILENAME", "EXPECTED_BCERT_METADATA", "create_bcert_xml"]

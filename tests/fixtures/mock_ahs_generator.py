#!/usr/bin/env python3
"""
Mock AHS File Generator - Creates test .ahs files for AHSDP parser testing.
Generates valid ZIP structures that mimic real HPE ProLiant AHS files.
"""

import gzip
import io
import os
import zipfile
from datetime import datetime, timedelta


def create_file_pkg_txt(bb_files):
    """Create file.pkg.txt - plain text listing of files in AHS."""
    content = "HPE Active Health System Log\n"
    content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    for bb_file in bb_files:
        content += f"{bb_file}\n"
    content += "bcert.pkg.xml\n"
    content += "clist.pkg\n"
    content += "counters.pkg\n"
    content += "CUST_INFO.DAT\n"
    return content.encode('utf-8')


def create_cust_info_dat():
    """Create CUST_INFO.DAT - binary customer metadata."""
    # Minimal binary structure - just padding
    return b'TEST_CUSTOMER_INFO' + b'\x00' * 100


def create_counters_pkg():
    """Create counters.pkg - binary counters metadata."""
    # Simple binary structure
    return b'\x00' * 50


def create_clist_pkg():
    """Create clist.pkg - binary blackbox file list."""
    # Minimal binary structure
    return b'\x01' + b'\x00' * 50


def create_bcert_xml():
    """Create bcert.pkg.xml - gzip-compressed XML with hardware test results."""
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<SystemTest>
  <Header>
    <GeneratedDate>{}</GeneratedDate>
    <ServerModel>ProLiant DL360 Gen10</ServerModel>
    <SerialNumber>TEST123456</SerialNumber>
  </Header>
  <HardwareTests>
    <SystemBoard status="PASS">
      <Test name="Memory">PASS</Test>
      <Test name="Processor">PASS</Test>
      <Test name="Storage">PASS</Test>
    </SystemBoard>
    <PowerSupply status="PASS">
      <PowerSupply1>OK</PowerSupply1>
      <PowerSupply2>OK</PowerSupply2>
    </PowerSupply>
    <Fans status="PASS">
      <Fan1>Normal</Fan1>
      <Fan2>Normal</Fan2>
      <Fan3>Normal</Fan3>
    </Fans>
  </HardwareTests>
  <SystemInfo>
    <Processors>2 x Intel Xeon</Processors>
    <Memory>256GB</Memory>
    <StorageCapacity>4TB</StorageCapacity>
  </SystemInfo>
</SystemTest>""".format(datetime.now().isoformat())

    # Compress with gzip
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as f:
        f.write(xml_content.encode('utf-8'))
    return buf.getvalue()


def create_bb_file(file_num, include_fault=False):
    """Create a .bb file - gzip-compressed BlackBox telemetry data.

    Args:
        file_num: Sequence number for the .bb file
        include_fault: If True, include patterns suggesting a hardware fault
    """
    # Old-style BlackBox format (0x3A header)
    bb_data = bytearray()
    bb_data.append(0x3A)  # Old-style header

    # Add mock field definitions
    # Format: type (1 byte) + flags (1 byte) + zeros + field name (null-terminated)
    fields = [
        b'\x88\x1d' + b'\x00' * 6 + b'IdleTask'.ljust(64, b'\x00'),
        b'\x88\x1f' + b'\x00' * 6 + b'iLO Kernel'.ljust(64, b'\x00'),
        b'\x84\x1d' + b'\x00' * 6 + b'Idle seconds in last minute'.ljust(64, b'\x00'),
        b'\x8c\x1f' + b'\x00' * 6 + b'Sleep time'.ljust(64, b'\x00'),
    ]

    if include_fault:
        fields.append(
            b'\x92\x31' + b'\x00' * 6 + b'EFUSE1_PF_FAULT'.ljust(64, b'\x00')
        )
        fields.append(
            b'\x8e\x31' + b'\x00' * 6 + b'System Board Fault'.ljust(64, b'\x00')
        )

    for field in fields:
        bb_data.extend(field)

    # Add some binary data blocks (mock telemetry values)
    for _ in range(10):
        bb_data.extend(b'\x31' + b'\x00' * 7)  # Mock sensor reading

    # Compress with gzip
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as f:
        f.write(bytes(bb_data))
    return buf.getvalue()


def create_ahs_file(output_path, filename, include_faults=False):
    """Create a complete AHS file (ZIP archive).

    Args:
        output_path: Directory to save the file
        filename: Name of the output .ahs file
        include_faults: If True, generate .bb files suggesting hardware faults
    """
    os.makedirs(output_path, exist_ok=True)
    full_path = os.path.join(output_path, filename)

    # Generate .bb filenames based on dates
    base_date = datetime.now() - timedelta(days=10)
    bb_files = []
    for i in range(5):
        date = base_date + timedelta(days=i)
        bb_files.append(date.strftime('%Y%m%d') + f'_{i:04d}.bb')

    # Create ZIP archive
    with zipfile.ZipFile(full_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add metadata files
        zf.writestr('file.pkg.txt', create_file_pkg_txt(bb_files))
        zf.writestr('CUST_INFO.DAT', create_cust_info_dat())
        zf.writestr('counters.pkg', create_counters_pkg())
        zf.writestr('clist.pkg', create_clist_pkg())
        zf.writestr('bcert.pkg.xml', create_bcert_xml())

        # Add BlackBox files
        for idx, bb_file in enumerate(bb_files):
            has_fault = include_faults and idx >= 3
            zf.writestr(bb_file, create_bb_file(idx, has_fault))

    return full_path


def main():
    """Generate sample AHS files for testing."""
    output_dir = 'tests/fixtures'

    print("🔧 Mock AHS File Generator")
    print("=" * 50)

    # Create valid, healthy AHS file
    print("\n✓ Generating valid_demo.ahs...")
    file1 = create_ahs_file(output_dir, 'valid_demo.ahs', include_faults=False)
    print(f"  Created: {file1}")

    # Create AHS file with fault indicators
    print("\n✓ Generating with_faults_demo.ahs...")
    file2 = create_ahs_file(output_dir, 'with_faults_demo.ahs', include_faults=True)
    print(f"  Created: {file2}")

    # Create a corrupted/minimal test file
    print("\n✓ Generating minimal.ahs...")
    os.makedirs(output_dir, exist_ok=True)
    minimal_path = os.path.join(output_dir, 'minimal.ahs')
    with zipfile.ZipFile(minimal_path, 'w') as zf:
        zf.writestr('file.pkg.txt', b'Test minimal AHS')
    print(f"  Created: {minimal_path}")

    print("\n" + "=" * 50)
    print("✅ Mock AHS files generated successfully!")
    print(f"\nTest files created in: {output_dir}/")
    print("\nUsage:")
    print("  python -m ahsdp.cli --in tests/fixtures/valid_demo.ahs --out ./exports/report.md")
    print("  python run_app.py  # Launch GUI to test with generated files")


if __name__ == '__main__':
    main()

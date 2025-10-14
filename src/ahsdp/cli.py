import argparse
import os
import sys

from .core import run_parser
from .faults import detect_hardware_faults


def build_findings(records):
    """CLI helper to construct hardware findings from parsed records."""
    return detect_hardware_faults(records)


def _parse_redactions(value: str):
    if value.strip().lower() == 'none':
        return []
    return [token.strip() for token in value.split(',') if token.strip()]


def _resolve_report_target(target: str):
    target_abs = os.path.abspath(target)
    if os.path.isdir(target_abs):
        return target_abs, 'report.md'
    if target_abs.lower().endswith('.md'):
        return os.path.dirname(target_abs) or '.', os.path.basename(target_abs)
    return target_abs, 'report.md'


def main():
    parser = argparse.ArgumentParser(
        prog='ahsdp', description='AHS Diagnostic Parser with BlackBox support.'
    )
    parser.add_argument('--in', '--input', dest='inp', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--export', default=None)
    parser.add_argument('--redact', default='email,phone,token')
    parser.add_argument('--temp-dir', default=None)
    args = parser.parse_args()

    redactions = _parse_redactions(args.redact)
    report_dir, report_name = _resolve_report_target(args.out)

    try:
        result = run_parser(
            args.inp,
            report_dir,
            export_dir=args.export,
            redactions=redactions,
            report_name=report_name,
            temp_dir=args.temp_dir,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(3)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(4)

    if result.get('preserved_temp'):
        print(f"Temporary extraction preserved at: {result['preserved_temp']}")

    print(f"Wrote report: {result['report_path']}")


if __name__ == '__main__':
    main()

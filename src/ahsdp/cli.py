import argparse
import os
import sys
from pathlib import Path

from .faults import detect_board_faults
from .identity import extract_identity
from .parse_bb import parse_bb_files
from .parse_nonbb import (
    parse_bcert,
    parse_counters_pkg,
    parse_cust_info,
    parse_filepkg_txt,
)
from .report import dump_json, write_markdown
from .safe_extract import SafeTempDir, extract_zip_safe


TRUTHY = {'1', 'true', 'yes', 'on'}
NON_BB_SUPPORTED = {
    'bcert.pkg.xml',
    'file.pkg.txt',
    'clist.pkg',
    'counters.pkg',
    'cust_info.dat',
}
BB_EXTS = ('.bb', '.zbb', '.bb.gz', '.bb.zip')


def _is_truthy(value):
    return str(value).strip().lower() in TRUTHY if value is not None else False


def discover(root):
    hits = {}
    bb_artifacts = []
    for base, _, files in os.walk(root):
        for fn in files:
            lower = fn.lower()
            full_path = os.path.join(base, fn)
            if lower in NON_BB_SUPPORTED:
                hits[lower] = full_path
            elif lower.endswith(BB_EXTS):
                bb_artifacts.append(full_path)
    return hits, bb_artifacts


def parse_non_bb(hits):
    inventory = {}
    summary = {'files': []}
    diagnostics = {}
    if 'bcert.pkg.xml' in hits:
        inventory = parse_bcert(hits['bcert.pkg.xml'])
    if 'file.pkg.txt' in hits:
        summary = parse_filepkg_txt(hits['file.pkg.txt'])
    if 'counters.pkg' in hits:
        diagnostics = parse_counters_pkg(hits['counters.pkg'])
    if 'cust_info.dat' in hits:
        parse_cust_info(hits['cust_info.dat'])
    return summary, inventory, diagnostics


def build_findings(events, enable_faults):
    if not enable_faults or not events:
        return []
    return detect_board_faults(events)


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

    enable_bb = _is_truthy(os.environ.get('AHS_BB'))
    enable_faults = _is_truthy(os.environ.get('AHS_FAULTS'))
    keep_tmp = _is_truthy(os.environ.get('AHS_KEEP_TMP'))

    redactions = (
        []
        if args.redact.strip().lower() == 'none'
        else [token.strip() for token in args.redact.split(',') if token.strip()]
    )

    preserved_temp = None
    with SafeTempDir(base=args.temp_dir, keep=keep_tmp) as tmp_dir:
        preserved_temp = tmp_dir
        if os.path.isdir(args.inp):
            workdir = args.inp
        elif args.inp.lower().endswith(('.zip', '.ahs')):
            extract_root = os.path.join(tmp_dir, 'extracted')
            os.makedirs(extract_root, exist_ok=True)
            workdir = extract_zip_safe(args.inp, extract_root)
        else:
            print('Unsupported input path.', file=sys.stderr)
            sys.exit(4)

        identity = extract_identity(Path(workdir), Path(args.inp))

        hits, bb_artifacts = discover(workdir)
        if not hits and not (enable_bb and bb_artifacts):
            print('No supported files found.', file=sys.stderr)
            sys.exit(3)

        summary, inventory, diagnostics = parse_non_bb(hits)
        events = []
        meta = {
            'bb_enabled': enable_bb,
            'bb_parsed': False,
            'bb_sources': [],
            'artifact_count': len(bb_artifacts),
        }
        if enable_bb and bb_artifacts:
            bb_result = parse_bb_files(bb_artifacts)
            events = bb_result['records']
            meta['bb_parsed'] = True
            meta['bb_sources'] = bb_result['sources']

        findings = build_findings(events, enable_faults)

        if args.export:
            os.makedirs(args.export, exist_ok=True)
            dump_json(inventory, os.path.join(args.export, 'inventory.json'))
            dump_json(events, os.path.join(args.export, 'events.json'))
            dump_json(diagnostics, os.path.join(args.export, 'diagnostics.json'))
            dump_json(findings, os.path.join(args.export, 'findings.json'))
            dump_json(meta, os.path.join(args.export, 'metadata.json'))
            dump_json(identity, os.path.join(args.export, 'identity.json'))

        write_markdown(
            summary,
            inventory,
            events,
            diagnostics,
            args.out,
            redactions,
            findings=findings,
            metadata=meta,
            identity=identity,
        )

    if keep_tmp and preserved_temp:
        print(f'Temporary extraction preserved at: {preserved_temp}')

    print(f'Wrote report: {args.out}')


if __name__ == '__main__':
    main()

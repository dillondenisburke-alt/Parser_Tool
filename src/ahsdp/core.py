import os
from typing import Dict, List, Optional

from .faults import detect_board_faults
from .parse_bb import parse_bb_files
from .parse_nonbb import (
    parse_bcert,
    parse_counters_pkg,
    parse_cust_info,
    parse_filepkg_txt,
)
from .report import write_markdown, dump_json
from .safe_extract import SafeTempDir, extract_zip_safe
from .diagnostics import evaluate_diagnostic_findings


TRUTHY = {'1', 'true', 'yes', 'on'}
NON_BB_SUPPORTED = {
    'bcert.pkg.xml',
    'file.pkg.txt',
    'clist.pkg',
    'counters.pkg',
    'cust_info.dat',
}
BB_EXTS = ('.bb', '.zbb', '.bb.gz', '.bb.zip')


def _coalesce_bool(value: Optional[bool], fallback_env: Optional[str]) -> bool:
    if value is not None:
        return bool(value)
    if fallback_env is None:
        return False
    return fallback_env.strip().lower() in TRUTHY


def _normalise_redactions(redactions: Optional[List[str]]) -> List[str]:
    if not redactions:
        return []
    return [token.strip() for token in redactions if token and token.strip().lower() != 'none']


def discover(root: str):
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


def parse_non_bb(hits: Dict[str, str]):
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


def _build_findings(events: List[dict], enable_faults: bool, diagnostics: Dict[str, object]):
    findings: List[Dict[str, object]] = []
    if enable_faults and events:
        findings.extend(detect_board_faults(events))
    findings.extend(evaluate_diagnostic_findings(diagnostics))
    return findings


def run_parser(
    input_path: str,
    out_dir: str,
    export_dir: Optional[str] = None,
    redactions: Optional[List[str]] = None,
    *,
    report_name: str = 'report.md',
    enable_bb: Optional[bool] = None,
    enable_faults: Optional[bool] = None,
    keep_temp: Optional[bool] = None,
    temp_dir: Optional[str] = None,
):
    """
    Execute the full parsing workflow against the supplied bundle or directory.

    Returns a dictionary containing the report path, metadata, and optional export paths.
    Raises ValueError on unsupported input or when no recognised artifacts are found.
    """
    if not input_path:
        raise ValueError('Input path is required.')
    resolved_input = os.path.abspath(input_path)
    resolved_out_dir = os.path.abspath(out_dir)

    # Allow callers to hand us a direct Markdown path (for CLI backwards compatibility)
    if resolved_out_dir.lower().endswith('.md'):
        report_path = resolved_out_dir
        resolved_out_dir = os.path.dirname(report_path) or '.'
        resolved_out_dir = os.path.abspath(resolved_out_dir)
    else:
        report_path = os.path.join(resolved_out_dir, report_name)

    os.makedirs(resolved_out_dir, exist_ok=True)
    report_path = os.path.abspath(report_path)

    redaction_tokens = _normalise_redactions(redactions)
    bb_enabled = _coalesce_bool(enable_bb, os.environ.get('AHS_BB'))
    faults_enabled = _coalesce_bool(enable_faults, os.environ.get('AHS_FAULTS'))
    keep_tmp_flag = _coalesce_bool(keep_temp, os.environ.get('AHS_KEEP_TMP'))

    preserved_temp = None
    metadata = {
        'bb_enabled': bb_enabled,
        'bb_parsed': False,
        'bb_sources': [],
        'artifact_count': 0,
    }

    with SafeTempDir(base=temp_dir, keep=keep_tmp_flag) as tmp_dir:
        preserved_temp = tmp_dir if keep_tmp_flag else None
        if os.path.isdir(resolved_input):
            workdir = resolved_input
        elif resolved_input.lower().endswith(('.zip', '.ahs')):
            extract_root = os.path.join(tmp_dir, 'extracted')
            os.makedirs(extract_root, exist_ok=True)
            workdir = extract_zip_safe(resolved_input, extract_root)
        else:
            raise ValueError('Unsupported input path. Provide a directory or .ahs/.zip bundle.')

        hits, bb_artifacts = discover(workdir)
        metadata['artifact_count'] = len(bb_artifacts)
        if not hits and not (bb_enabled and bb_artifacts):
            raise FileNotFoundError('No supported files were discovered in the supplied input.')

        summary, inventory, diagnostics = parse_non_bb(hits)
        events = []
        if bb_enabled and bb_artifacts:
            bb_result = parse_bb_files(bb_artifacts)
            events = bb_result['records']
            metadata['bb_parsed'] = True
            metadata['bb_sources'] = bb_result['sources']

        findings = _build_findings(events, faults_enabled, diagnostics)

        if export_dir:
            export_dir_abs = os.path.abspath(export_dir)
            os.makedirs(export_dir_abs, exist_ok=True)
            dump_json(inventory, os.path.join(export_dir_abs, 'inventory.json'))
            dump_json(events, os.path.join(export_dir_abs, 'events.json'))
            dump_json(diagnostics, os.path.join(export_dir_abs, 'diagnostics.json'))
            dump_json(findings, os.path.join(export_dir_abs, 'findings.json'))
            dump_json(metadata, os.path.join(export_dir_abs, 'metadata.json'))
        else:
            export_dir_abs = None

        write_markdown(
            summary,
            inventory,
            events,
            diagnostics,
            report_path,
            redaction_tokens,
            findings=findings,
            metadata=metadata,
        )

    return {
        'report_path': report_path,
        'export_dir': export_dir_abs,
        'metadata': metadata,
        'events': events,
        'inventory': inventory,
        'diagnostics': diagnostics,
        'findings': findings,
        'preserved_temp': preserved_temp,
    }

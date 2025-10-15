import os
import sys
import threading
import traceback
from datetime import datetime, timezone
import PySimpleGUI as sg

# Internal imports from your package
from ahsdp.utils import ensure_outdir
from ahsdp.safe_extract import safe_extract_ahs
from ahsdp.parse_nonbb import parse_extracted_nonbb
from ahsdp.report import build_report_markdown, write_report_files

APP_TITLE = "AHS Diagnostic Parser"
VERSION = "1.1.0"
DEFAULT_EXPORT_DIR = os.path.join(os.getcwd(), "exports")

def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

def run_pipeline(input_path: str, out_dir: str, log_cb):
    """
    Minimal pipeline: validate, (maybe) extract, parse non-bb, write report.
    """
    try:
        log_cb(f"🔎 Input: {input_path}")
        log_cb(f"📁 Output dir: {out_dir}")
        ensure_outdir(out_dir)

        src_is_dir = os.path.isdir(input_path)
        src_is_file = os.path.isfile(input_path)

        if not (src_is_dir or src_is_file):
            raise FileNotFoundError(f"Input path not found: {input_path}")

        # Only accept .ahs files (or a folder containing .ahs files)
        ahs_files = []
        if src_is_file:
            if not input_path.lower().endswith(".ahs"):
                raise ValueError("Only .ahs files are supported.")
            ahs_files = [input_path]
        else:
            for root, _, files in os.walk(input_path):
                for f in files:
                    if f.lower().endswith(".ahs"):
                        ahs_files.append(os.path.join(root, f))

        if not ahs_files:
            raise ValueError("No .ahs files found in the selected input.")

        log_cb(f"📦 Found {len(ahs_files)} .ahs bundle(s). Extracting…")

        extracted_roots = []
        for idx, ahs in enumerate(ahs_files, 1):
            log_cb(f"  • [{idx}/{len(ahs_files)}] {os.path.basename(ahs)}")
            dest = os.path.join(out_dir, os.path.splitext(os.path.basename(ahs))[0])
            os.makedirs(dest, exist_ok=True)
            root = safe_extract_ahs(ahs, dest)  # returns path containing extracted files
            extracted_roots.append(root)

        # Parse non-bb files from each extracted bundle
        all_findings = []
        inventory = []
        for root in extracted_roots:
            log_cb(f"🧩 Parsing extracted bundle at: {root}")
            inv, findings = parse_extracted_nonbb(root)
            inventory.append(inv)
            all_findings.extend(findings)

        # Build + write report
        log_cb("📝 Building report…")
        md = build_report_markdown(
            inventory_blocks=inventory,
            findings=all_findings,
            meta={
                "generated_utc": _utc_now_iso(),
                "source_count": len(ahs_files),
                "experimental_bb": False,
            },
        )
        written = write_report_files(md, out_dir)
        for p in written:
            log_cb(f"✅ Wrote: {p}")

        return True, written

    except Exception as e:
        log_cb("❌ Error during run:")
        log_cb("    " + str(e))
        tb = traceback.format_exc()
        for line in tb.splitlines():
            log_cb("    " + line)
        return False, []

def main():
    sg.theme("SystemDefault")
    layout = [
        [sg.Text(f"{APP_TITLE} — v{VERSION}", font=("Segoe UI", 14, "bold"))],
        [sg.Text("Select a .ahs file (or a folder containing .ahs files):")],
        [
            sg.Input(key="-INPUT-", enable_events=True, expand_x=True),
            sg.FileBrowse("Browse .ahs", file_types=(("AHS Bundles", "*.ahs"),)),
            sg.FolderBrowse("Browse folder"),
        ],
        [sg.Text("Output folder:"), sg.Input(DEFAULT_EXPORT_DIR, key="-OUT-", expand_x=True),
         sg.FolderBrowse("Choose…")],
        [sg.Multiline("", size=(88, 18), key="-LOG-", autoscroll=True, write_only=True, expand_x=True, expand_y=True)],
        [
            sg.Button("Run", key="-RUN-", bind_return_key=True),
            sg.Button("Open exports", key="-OPEN-"),
            sg.Push(),
            sg.Button("Quit")
        ]
    ]

    window = sg.Window(APP_TITLE, layout, resizable=True)

    busy = False
    worker = None

    def log(msg: str):
        window["-LOG-"].print(msg)

    while True:
        event, values = window.read(timeout=100)
        if event in (sg.WIN_CLOSED, "Quit"):
            break

        if event == "-RUN-":
            if busy:
                continue
            inp = (values.get("-INPUT-") or "").strip()
            outp = (values.get("-OUT-") or "").strip() or DEFAULT_EXPORT_DIR

            if not inp:
                sg.popup_error("Please select a .ahs file or a folder containing .ahs files.")
                continue

            busy = True
            window["-RUN-"].update(disabled=True)
            log("—" * 70)
            log("▶ Starting…")

            def do_work():
                ok, paths = run_pipeline(inp, outp, log)
                if ok:
                    log("🎉 Done.")
                else:
                    log("⚠️ Completed with errors.")
                window.write_event_value("-DONE-", ok)

            worker = threading.Thread(target=do_work, daemon=True)
            worker.start()

        if event == "-OPEN-":
            outp = values.get("-OUT-", DEFAULT_EXPORT_DIR)
            if outp and os.path.isdir(outp):
                try:
                    if sys.platform.startswith("win"):
                        os.startfile(outp)  # type: ignore[attr-defined]
                    elif sys.platform == "darwin":
                        os.system(f'open "{outp}"')
                    else:
                        os.system(f'xdg-open "{outp}"')
                except Exception:
                    sg.popup_error(f"Could not open folder:\n{outp}")

        if event == "-DONE-":
            busy = False
            window["-RUN-"].update(disabled=False)

    window.close()

if __name__ == "__main__":
    main()

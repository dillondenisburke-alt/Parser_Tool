"""PySimpleGUI front-end for the AHS Diagnostic Parser."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional

import PySimpleGUI as sg

from ahsdp.core import run_parser

APP_TITLE = "AHS Diagnostic Parser"
VERSION = "1.1.0"
DEFAULT_REPORT_TARGET = Path.cwd() / "exports" / "report.md"
DEFAULT_EXPORT_DIR = Path.cwd() / "exports" / "json"
DEFAULT_REDACTIONS = "email,phone,token"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalise_report_target(target: str) -> tuple[Path, str]:
    """Return (output_dir, report_name) for ``run_parser`` consumption."""

    candidate = Path(target).expanduser()
    if candidate.suffix.lower() == ".md":
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate.parent.resolve(), candidate.name

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate.resolve(), "report.md"


def _normalise_export_dir(path: Optional[str]) -> Optional[Path]:
    if not path:
        return None
    export_path = Path(path).expanduser()
    export_path.mkdir(parents=True, exist_ok=True)
    return export_path.resolve()


def _parse_redactions(tokens: str) -> list[str]:
    cleaned: list[str] = []
    for piece in (tokens or "").split(","):
        token = piece.strip()
        if token:
            cleaned.append(token)
    return cleaned


def _open_path(path: str | os.PathLike[str]) -> None:
    target = str(path)
    if not target:
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{target}"')
        else:
            os.system(f'xdg-open "{target}"')
    except Exception:
        sg.popup_error(f"Could not open path:\n{target}")


def run_pipeline(
    input_path: str,
    report_target: str,
    export_dir: Optional[str],
    enable_bb: bool,
    enable_faults: bool,
    keep_temp: bool,
    redactions: Iterable[str],
    log_cb: Callable[[str], None],
):
    """Execute :func:`ahsdp.core.run_parser` and stream progress to ``log_cb``."""

    try:
        resolved_input = Path(input_path).expanduser()
        if not resolved_input.exists():
            raise FileNotFoundError(f"Input path not found: {resolved_input}")

        out_dir, report_name = _normalise_report_target(report_target)
        export_path = _normalise_export_dir(export_dir)

        log_cb(f"🔎 Input: {resolved_input}")
        log_cb(f"📝 Report target: {out_dir / report_name}")
        if export_path:
            log_cb(f"📦 Export directory: {export_path}")
        log_cb(
            "⚙️  Options → BB parsing: {bb}, Fault detection: {faults}, Keep temp: {keep}".format(
                bb="ON" if enable_bb else "OFF",
                faults="ON" if enable_faults else "OFF",
                keep="ON" if keep_temp else "OFF",
            )
        )
        if redactions:
            log_cb(f"🔐 Redactions: {', '.join(redactions)}")
        else:
            log_cb("🔐 Redactions: (none)")

        result = run_parser(
            str(resolved_input),
            str(out_dir),
            export_dir=str(export_path) if export_path else None,
            redactions=list(redactions),
            report_name=report_name,
            enable_bb=enable_bb,
            enable_faults=enable_faults,
            keep_temp=keep_temp,
        )

        log_cb("✅ Report generated successfully.")
        log_cb(f"   • Markdown: {result['report_path']}")
        if result.get("export_dir"):
            log_cb(f"   • JSON exports: {result['export_dir']}")
        if result.get("metadata", {}).get("bb_parsed"):
            log_cb("   • BB artifacts parsed and included in report.")
        if result.get("findings"):
            log_cb(f"   • Findings detected: {len(result['findings'])}")
        log_cb(f"🕒 Completed at {_utc_now_iso()} UTC")

        return True, result

    except Exception as exc:  # noqa: BLE001 - surfacing to GUI log
        log_cb("❌ Error during run:")
        log_cb(f"    {exc}")
        tb = traceback.format_exc()
        for line in tb.splitlines():
            log_cb(f"    {line}")
        return False, {}


def main() -> None:
    sg.theme("SystemDefault")

    layout = [
        [sg.Text(f"{APP_TITLE} — v{VERSION}", font=("Segoe UI", 14, "bold"))],
        [sg.Text("Select an AHS bundle (.ahs/.zip) or a directory of extracted files:")],
        [
            sg.Input(key="-INPUT-", enable_events=True, expand_x=True),
            sg.FileBrowse(
                "Browse bundle",
                file_types=(("AHS Bundles", "*.ahs"), ("Zip archives", "*.zip")),
                target="-INPUT-",
            ),
            sg.FolderBrowse("Browse folder", target="-INPUT-"),
        ],
        [
            sg.Text("Report output (folder or .md file):"),
            sg.Input(str(DEFAULT_REPORT_TARGET), key="-OUT-", expand_x=True),
            sg.FolderBrowse("Select folder", target="-OUT-"),
        ],
        [
            sg.Checkbox(
                "Export JSON artifacts",
                key="-EXPORT-ENABLED-",
                default=True,
                enable_events=True,
            ),
            sg.Input(str(DEFAULT_EXPORT_DIR), key="-EXPORT-", expand_x=True),
            sg.FolderBrowse("Select export dir", target="-EXPORT-"),
        ],
        [
            sg.Text("Redaction tokens (comma separated):"),
            sg.Input(DEFAULT_REDACTIONS, key="-REDACT-", expand_x=True),
        ],
        [
            sg.Checkbox("Enable .bb parsing", key="-ENABLE-BB-", default=False),
            sg.Checkbox("Enable fault detection", key="-ENABLE-FAULTS-", default=True),
            sg.Checkbox("Preserve temp extraction", key="-KEEP-TMP-", default=False),
        ],
        [
            sg.Multiline(
                "",
                size=(88, 20),
                key="-LOG-",
                autoscroll=True,
                write_only=True,
                expand_x=True,
                expand_y=True,
            )
        ],
        [
            sg.Button("Run", key="-RUN-", bind_return_key=True),
            sg.Button("Open report", key="-OPEN-REPORT-", disabled=True),
            sg.Button("Open exports", key="-OPEN-EXPORT-", disabled=True),
            sg.Push(),
            sg.Button("Quit"),
        ],
    ]

    window = sg.Window(APP_TITLE, layout, resizable=True, finalize=True)

    busy = False
    last_result: dict | None = None

    def log(msg: str) -> None:
        window["-LOG-"].print(msg)

    while True:
        event, values = window.read(timeout=100)
        if event in (sg.WIN_CLOSED, "Quit"):
            break

        if event == "-EXPORT-ENABLED-":
            enabled = bool(values.get("-EXPORT-ENABLED-"))
            window["-EXPORT-"].update(disabled=not enabled)

        if event == "-RUN-":
            if busy:
                continue

            inp = (values.get("-INPUT-") or "").strip()
            if not inp:
                sg.popup_error("Please select an input bundle or folder to parse.")
                continue

            report_target = (values.get("-OUT-") or str(DEFAULT_REPORT_TARGET)).strip()
            export_enabled = bool(values.get("-EXPORT-ENABLED-"))
            export_dir = (values.get("-EXPORT-") or "").strip() if export_enabled else None
            redactions = _parse_redactions(values.get("-REDACT-", ""))
            enable_bb = bool(values.get("-ENABLE-BB-"))
            enable_faults = bool(values.get("-ENABLE-FAULTS-"))
            keep_temp = bool(values.get("-KEEP-TMP-"))

            busy = True
            window["-RUN-"].update(disabled=True)
            window["-OPEN-REPORT-"].update(disabled=True)
            window["-OPEN-EXPORT-"].update(disabled=True)
            log("―" * 70)
            log("▶ Starting run…")

            def do_work() -> None:
                ok, result = run_pipeline(
                    inp,
                    report_target,
                    export_dir,
                    enable_bb,
                    enable_faults,
                    keep_temp,
                    redactions,
                    log,
                )
                window.write_event_value("-DONE-", (ok, result))

            threading.Thread(target=do_work, daemon=True).start()

        if event == "-DONE-":
            busy = False
            window["-RUN-"].update(disabled=False)
            ok, result = values.get("-DONE-", (False, {}))
            last_result = result if ok else None
            if ok and result:
                window["-OPEN-REPORT-"].update(disabled=False)
                window["-OPEN-EXPORT-"].update(disabled=not result.get("export_dir"))
                log("🎉 Done.")
            else:
                log("⚠️ Completed with errors.")

        if event == "-OPEN-REPORT-" and last_result:
            _open_path(last_result.get("report_path"))

        if event == "-OPEN-EXPORT-" and last_result and last_result.get("export_dir"):
            _open_path(last_result.get("export_dir"))

    window.close()


if __name__ == "__main__":
    main()

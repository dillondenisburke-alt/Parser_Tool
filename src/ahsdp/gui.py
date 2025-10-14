import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    DND_AVAILABLE = True
except ImportError:
    TkinterDnD = None  # type: ignore
    DND_AVAILABLE = False

from .core import run_parser


def _default_output_dir():
    docs = os.path.join(os.path.expanduser('~'), 'Documents')
    target = os.path.join(docs, 'AHS Reports')
    os.makedirs(target, exist_ok=True)
    return target


class ParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title('AHS Diagnostic Parser')
        self.root.geometry('520x360')
        self.root.minsize(480, 320)

        self.queue = queue.Queue()

        self.output_dir_var = tk.StringVar(value=_default_output_dir())
        self.redactions_var = tk.StringVar(value='email,phone,token')
        self.bb_var = tk.BooleanVar(value=True)
        self.faults_var = tk.BooleanVar(value=True)
        self.keep_tmp_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value='Drop an AHS bundle (.ahs/.zip) to begin.')

        self._build_layout()
        self._poll_queue()

    # UI construction --------------------------------------------------
    def _build_layout(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        drop_frame = ttk.LabelFrame(main, text='Input Bundle')
        drop_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        if DND_AVAILABLE:
            self.drop_label = ttk.Label(
                drop_frame,
                text='Drag & drop bundle here',
                anchor=tk.CENTER,
                relief=tk.RIDGE,
                padding=18,
            )
            self.drop_label.pack(fill=tk.BOTH, expand=True)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind('<<Drop>>', self._handle_drop)
        else:
            ttk.Label(
                drop_frame,
                text='Drag & drop unavailable (tkinterdnd2 not installed).\nUse Browse… to pick a bundle.',
                anchor=tk.CENTER,
                padding=12,
                justify=tk.CENTER,
            ).pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(controls, text='Browse…', command=self._browse).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Label(controls, text='Output directory:').pack(side=tk.LEFT)
        output_entry = ttk.Entry(controls, textvariable=self.output_dir_var)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        options = ttk.Frame(main)
        options.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(options, text='Redactions (comma separated):').grid(row=0, column=0, sticky='w')
        ttk.Entry(options, textvariable=self.redactions_var).grid(
            row=0, column=1, sticky='ew', padx=(8, 0)
        )

        ttk.Checkbutton(options, text='Parse BlackBox (.bb)', variable=self.bb_var).grid(
            row=1, column=0, sticky='w', pady=(8, 0)
        )
        ttk.Checkbutton(options, text='Detect board faults', variable=self.faults_var).grid(
            row=1, column=1, sticky='w', pady=(8, 0)
        )
        ttk.Checkbutton(options, text='Keep temporary extraction', variable=self.keep_tmp_var).grid(
            row=2, column=0, sticky='w', pady=(8, 0)
        )

        options.columnconfigure(1, weight=1)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill=tk.X)

        ttk.Label(status_frame, textvariable=self.status_var, wraplength=460, foreground='#1f2933').pack(
            anchor='w'
        )

        self.links_frame = ttk.Frame(main)
        self.links_frame.pack(fill=tk.X, pady=(8, 0))

    # Event handling ---------------------------------------------------
    def _handle_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        if not paths:
            return
        self._start_job(paths[0])

    def _browse(self):
        file_path = filedialog.askopenfilename(
            title='Select AHS bundle',
            filetypes=[('AHS bundle', '*.ahs'), ('Zip archive', '*.zip'), ('All files', '*.*')],
        )
        if file_path:
            self._start_job(file_path)

    def _start_job(self, path):
        path = path.strip()
        if not path:
            return
        if not os.path.exists(path):
            messagebox.showerror('File not found', f'No such file: {path}')
            return
        self.status_var.set('Processing bundle…')
        self._set_controls_state(tk.DISABLED)
        self._clear_links()

        worker = threading.Thread(target=self._worker, args=(path,), daemon=True)
        worker.start()

    def _worker(self, path):
        exports_dir = os.path.join(self.output_dir_var.get(), 'exports')
        try:
            result = run_parser(
                path,
                self.output_dir_var.get(),
                export_dir=exports_dir,
                redactions=self._parse_redactions(),
                report_name='report.md',
                enable_bb=self.bb_var.get(),
                enable_faults=self.faults_var.get(),
                keep_temp=self.keep_tmp_var.get(),
            )
            self.queue.put(('success', result))
        except Exception as exc:  # noqa: BLE001
            self.queue.put(('error', str(exc)))

    def _parse_redactions(self):
        value = self.redactions_var.get()
        if not value:
            return []
        return [token.strip() for token in value.split(',') if token.strip()]

    def _poll_queue(self):
        try:
            kind, payload = self.queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_queue)
            return

        if kind == 'success':
            self._handle_success(payload)
        else:
            self._handle_error(payload)

        self.root.after(100, self._poll_queue)

    def _handle_success(self, result):
        self.status_var.set('Parsing complete.')
        self._set_controls_state(tk.NORMAL)

        report_path = result['report_path']
        exports_dir = result.get('export_dir')

        self._create_link('Open report folder', os.path.dirname(report_path))
        if exports_dir:
            self._create_link('Open exports folder', exports_dir)
        if result.get('preserved_temp'):
            self._create_link('Open temp extract', result['preserved_temp'])

    def _handle_error(self, message):
        self.status_var.set(f'Error: {message}')
        self._set_controls_state(tk.NORMAL)
        messagebox.showerror('AHS Parser Error', message)

    def _set_controls_state(self, state):
        for child in self.root.winfo_children():
            self._set_state_recursive(child, state)

    def _set_state_recursive(self, widget, state):
        if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Checkbutton)):
            widget.state(['!disabled'] if state == tk.NORMAL else ['disabled'])
        for child in widget.winfo_children():
            self._set_state_recursive(child, state)

    def _clear_links(self):
        for child in self.links_frame.winfo_children():
            child.destroy()

    def _create_link(self, label, path):
        def open_path(_event=None):
            try:
                os.startfile(path)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror('Unable to open', f'{path}\n\n{exc}')

        link = ttk.Label(self.links_frame, text=label, foreground='#1d4ed8', cursor='hand2')
        link.pack(anchor='w')
        link.bind('<Button-1>', open_path)


def main():
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()  # type: ignore[attr-defined]
    else:
        root = tk.Tk()

    try:
        root.iconname('ahsdp')
    except tk.TclError:
        pass

    app = ParserApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

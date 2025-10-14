import os, json, datetime
from .redact import mask
def write_markdown(summary, inventory, events, diag, out_path, redactions):
    ts = datetime.datetime.utcnow().isoformat()+'Z'
    def red(s): return mask(s, redactions) if isinstance(s,str) else s
    lines = [f'# AHS Diagnostic Parser Report', f'_Generated: {ts}_','',
             '## System Inventory (non-.bb sources)']
    for k in ('ProductName','SerialNumber','ROMVersion','ILO'):
        v = red(inventory.get(k))
        if v: lines.append(f'- **{k}:** {v}')
    lines += ['', '## Discovered Files']
    for f in summary.get('files',[]): lines.append(f'- {red(f)}')
    lines += ['', '## Diagnostics']
    for k,v in (diag.get('counters') or {}).items(): lines.append(f'- {k}: {v}')
    lines += ['', '## Notes','- Black Box (*.bb/*.zbb) parsing is intentionally excluded in this MVP.']
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    open(out_path,'wt',encoding='utf-8').write('\n'.join(lines))
def dump_json(obj, path):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    open(path,'wt',encoding='utf-8').write(json.dumps(obj, indent=2, ensure_ascii=False))

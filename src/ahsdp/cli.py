import argparse, os, sys
from .safe_extract import SafeTempDir, extract_zip_safe
from .parse_nonbb import parse_bcert, parse_filepkg_txt, parse_counters_pkg, parse_cust_info
from .report import write_markdown, dump_json
SUPPORTED = {'bcert.pkg.xml','file.pkg.txt','clist.pkg','counters.pkg','CUST_INFO.DAT'}
def discover(root):
    hits={}
    for base,_,files in os.walk(root):
        for fn in files:
            lower=fn.lower()
            if lower in SUPPORTED: hits[lower]=os.path.join(base,fn)
    return hits
def parse(hits):
    inventory={}; summary={'files':[]}; diag={}; events={}
    if 'bcert.pkg.xml' in hits: inventory=parse_bcert(hits['bcert.pkg.xml'])
    if 'file.pkg.txt' in hits: summary=parse_filepkg_txt(hits['file.pkg.txt'])
    if 'counters.pkg' in hits: diag=parse_counters_pkg(hits['counters.pkg'])
    if 'cust_info.dat' in hits: _=parse_cust_info(hits['cust_info.dat'])
    return summary, inventory, events, diag
def main():
    ap=argparse.ArgumentParser(prog='ahsdp', description='AHS Diagnostic Parser (non-.bb MVP).')
    ap.add_argument('--in','--input',dest='inp',required=True)
    ap.add_argument('--out',required=True)
    ap.add_argument('--export',default=None)
    ap.add_argument('--redact',default='email,phone,token')
    ap.add_argument('--temp-dir',default=None)
    a=ap.parse_args()
    reds=[] if a.redact.strip().lower()=='none' else [r.strip() for r in a.redact.split(',') if r.strip()]
    with SafeTempDir(base=a.temp_dir) as tmp:
        if os.path.isdir(a.inp): work=a.inp
        elif a.inp.lower().endswith(('.zip','.ahs')): work=extract_zip_safe(a.inp, os.path.join(tmp,'x'))
        else: print('Unsupported input path.', file=sys.stderr); sys.exit(4)
        hits=discover(work)
        if not hits: print('No supported files found.', file=sys.stderr); sys.exit(3)
        s,i,e,d=parse(hits)
        if a.export:
            os.makedirs(a.export, exist_ok=True)
            dump_json(i, os.path.join(a.export,'inventory.json'))
            dump_json(e, os.path.join(a.export,'events.json'))
            dump_json(d, os.path.join(a.export,'diagnostics.json'))
        write_markdown(s,i,e,d,a.out,reds)
        print(f'Wrote report: {a.out}')
if __name__=='__main__': main()

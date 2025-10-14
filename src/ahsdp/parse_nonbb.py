import os, json, gzip, re, struct
def _maybe_gzip_open(path):
    with open(path, 'rb') as f:
        if f.read(2)==b'\x1f\x8b': return gzip.open(path,'rt',encoding='utf-8',errors='replace')
    return open(path,'rt',encoding='utf-8',errors='replace')
def parse_bcert(path):
    text=_maybe_gzip_open(path).read()
    out={'_source': os.path.basename(path)}
    def g(tag):
        m=re.search(rf'<{tag}>(.*?)</{tag}>', text, re.I|re.S)
        return m.group(1).strip() if m else None
    out['ProductName']=g('ProductName'); out['SerialNumber']=g('SerialNumber')
    out['ROMVersion']=g('ROMVersion'); out['ILO']=g('ILOVersion')
    return out
def parse_filepkg_txt(path):
    files=[]
    with open(path,'rt',encoding='utf-8',errors='replace') as f:
        for line in f:
            line=line.strip()
            if line: files.append(line)
    return {'_source': os.path.basename(path), 'files': files}
def parse_counters_pkg(path):
    out={'_source': os.path.basename(path), 'counters': {}}
    with open(path,'rb') as f: buf=f.read()
    ints=[]
    for i in range(0, min(len(buf),12),4): ints.append(struct.unpack('<I', buf[i:i+4])[0])
    for k,v in zip(['write_errors','rotation','drops'], ints): out['counters'][k]=v
    return out
def parse_cust_info(path):
    out={'_source': os.path.basename(path), 'fields': {}}
    try:
        with open(path,'rt',encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    k,v=line.split('=',1); out['fields'][k.strip()]=v.strip()
    except UnicodeDecodeError:
        out['fields']['_size_bytes']=os.path.getsize(path)
    return out

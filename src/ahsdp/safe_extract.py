import os, zipfile, shutil, tempfile
class SafeTempDir:
    def __init__(self, base=None): self.base=base; self.path=None
    def __enter__(self): self.path=tempfile.mkdtemp(prefix='ahsdp_', dir=self.base); return self.path
    def __exit__(self, *a): 
        if self.path and os.path.isdir(self.path): shutil.rmtree(self.path, ignore_errors=True)
def extract_zip_safe(zip_path, dest_dir, size_limit_bytes=1024*1024*1024):
    with zipfile.ZipFile(zip_path) as zf:
        total=0
        for zi in zf.infolist():
            out_path=os.path.normpath(os.path.join(dest_dir, zi.filename))
            if not out_path.startswith(os.path.abspath(dest_dir)): continue
            if zi.is_dir():
                os.makedirs(out_path, exist_ok=True); continue
            total += zi.file_size
            if total>size_limit_bytes: break
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with zf.open(zi, 'r') as src, open(out_path,'wb') as dst:
                shutil.copyfileobj(src,dst,1024*128)
    return dest_dir

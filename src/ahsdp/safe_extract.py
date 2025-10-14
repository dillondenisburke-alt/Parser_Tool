import os
import shutil
import tempfile
import zipfile


class SafeTempDir:
    def __init__(self, base=None, keep=False):
        self.base = base
        self.keep = keep
        self.path = None

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix='ahsdp_', dir=self.base)
        return self.path

    def __exit__(self, *a):
        if self.keep:
            return
        if self.path and os.path.isdir(self.path):
            shutil.rmtree(self.path, ignore_errors=True)


def extract_zip_safe(zip_path, dest_dir, size_limit_bytes=1024 * 1024 * 1024):
    dest_root = os.path.abspath(dest_dir)
    with zipfile.ZipFile(zip_path) as zf:
        total = 0
        for zi in zf.infolist():
            candidate = os.path.normpath(os.path.join(dest_root, zi.filename))
            target_path = os.path.abspath(candidate)
            if os.path.commonpath([dest_root, target_path]) != dest_root:
                continue
            if zi.is_dir():
                os.makedirs(target_path, exist_ok=True)
                continue
            total += zi.file_size
            if total > size_limit_bytes:
                break
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with zf.open(zi, 'r') as src, open(target_path, 'wb') as dst:
                shutil.copyfileobj(src, dst, 1024 * 128)
    return dest_root

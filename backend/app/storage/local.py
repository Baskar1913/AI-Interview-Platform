from pathlib import Path
import re, uuid
from ..core.config import settings
class LocalFileStorage:
    def __init__(self):
        self.root=Path(settings.storage_path)
        for d in ("resumes","recordings","audio","reports"): (self.root/d).mkdir(parents=True,exist_ok=True)
    def save(self, category, filename, data):
        safe=re.sub(r"[^A-Za-z0-9._-]","_",filename)
        path=self.root/category/f"{uuid.uuid4()}_{safe}"
        path.write_bytes(data)
        return str(path)
    def read(self,path): return Path(path).read_bytes()

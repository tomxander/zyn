"""Package deliverables, excluding local runtime libraries and build caches."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'zyn-identity.zip'
def included(p):
    return p.is_file() and p!=target and 'python-libs' not in p.parts and '__pycache__' not in p.parts and p.name!='refine.py'
files=sorted(p for p in ROOT.rglob('*') if included(p))
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert {'index.html','README.md','sheets/01-construction.svg','sheets/03-icons-both.svg','source/validation.json','source/browser-review.json'}.issubset(z.namelist())
print(json.dumps({'archive':str(target),'files':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))

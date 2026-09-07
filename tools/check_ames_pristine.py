"""Compare Ames outputs with a fresh run of the pinned official executable.

Run the stock spcheck ctest for both executables first. Its historical golden
files are retained unchanged; this additional check separates a stale golden
dataset from a regression introduced by coupling.
"""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]

def main():
    reference=ROOT/'build/ames_pristine/Ames_sub1'
    coupled=ROOT/'build/coupled/data/Ames_sub1'
    selected=[s.strip() for s in (ROOT/'data/Ames_sub1/.testfiles.txt').read_text().splitlines()
              if s.strip() and not s.startswith('#')]
    checks={}
    for name in selected:
        a=(reference/name).read_text().splitlines()[1:]
        b=(coupled/name).read_text().splitlines()[1:]
        assert a==b, f'Fresh official vs coupling-off differs: {name}'
        checks[name]={'lines':len(a),'sha256_without_banner':hashlib.sha256('\n'.join(a).encode()).hexdigest()}
    result={'status':'pass','checks':checks,'historical_golden':'not modified; also differs from pinned official executable'}
    latest=ROOT/'build/ames_latest_run.json'
    if latest.exists():
        run=json.loads(latest.read_text())
        assert run['exit_code']==0
        assert hashlib.sha256(Path(run['executable']).read_bytes()).hexdigest()==run['sha256']
        result['coupling_off_run']=run
    target=ROOT/'reports/canada/ames_pristine.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

if __name__=='__main__':main()

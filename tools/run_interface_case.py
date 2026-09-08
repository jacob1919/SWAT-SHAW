"""Run an isolated post-review case with explicit inputs, switches and executable hashes."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'validation/canada'
OLD = ROOT.parent/'swatplus_addFT'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument('case')
    p.add_argument('--model', choices=['official','existing_ft','shaw','coupling_off'], default='shaw')
    p.add_argument('--inputs', choices=['original','awc'], default='awc')
    p.add_argument('--hru', type=int)
    p.add_argument('--radiation',choices=['legacy_north','aspect_or_horizontal','horizontal'],default='aspect_or_horizontal')
    p.add_argument('--forcing',choices=['legacy','fixed'],default='fixed')
    p.add_argument('--thermal',choices=['fixed','estimated'],default='fixed')
    p.add_argument('--rain-hours',type=int,choices=range(1,25),default=24)
    p.add_argument('--rain-start',type=int,choices=range(1,25),default=1)
    args=p.parse_args()
    assert re.fullmatch(r'[a-z0-9_]+',args.case), 'Case name must be a simple identifier'
    source=BASE/'inputs' if args.inputs=='original' else BASE/'interface_review/inputs_awc_corrected'
    manifest_path=BASE/'input_manifest.json' if args.inputs=='original' else BASE/'interface_review/input_manifest_awc_corrected.json'
    manifest=json.loads(manifest_path.read_text())['sha256']
    target=BASE/'interface_review'/args.case
    target.mkdir(exist_ok=False) # Never overwrite earlier results.
    for name,digest in manifest.items():
        original=source/name
        assert sha(original)==digest, ('Input drift',name)
        destination=target/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(original.read_bytes())
    builds={'official':OLD/'validation_baselines/swatplus_61c940f_clean/build_clean',
            'existing_ft':OLD/'build/debug','shaw':ROOT/'build/coupled','coupling_off':ROOT/'build/coupled'}
    if args.model in ('shaw','coupling_off'):
        # Read the active CMake target; older executables may coexist in the build.
        ninja=(builds[args.model]/'build.ninja').read_text()
        name,=re.findall(r'^build (swatplus-[^:]+\.exe):',ninja,re.M)
        exe=builds[args.model]/name
    else:
        exe,=builds[args.model].glob('swatplus-*.exe')
    env={k:v for k,v in os.environ.items() if not k.upper().startswith('SWAT_SHAW')}
    env.update(SWAT_SHAW='1' if args.model=='shaw' else '0',
               SWAT_SHAW_RADIATION=args.radiation,SWAT_SHAW_FORCING=args.forcing,
               SWAT_SHAW_THERMAL=args.thermal,SWAT_SHAW_RAIN_HOURS=str(args.rain_hours),
               SWAT_SHAW_RAIN_START=str(args.rain_start))
    if args.hru:
        assert args.model=='shaw' and args.hru>0
        env['SWAT_SHAW_HRU']=str(args.hru)
    metadata=dict(case=vars(args),executable=str(exe),executable_sha256=sha(exe),
                  coupling_repo_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  coupling_source_sha256_at_run={str(p.relative_to(ROOT)).replace('\\','/'):sha(p)
                    for p in sorted((ROOT/'src/shaw').glob('*.*'))+[ROOT/'src/shaw_swat_module.f90'] if p.is_file()},
                  input_sha256=manifest,environment={k:v for k,v in env.items() if k.startswith('SWAT_SHAW')},
                  scope='Selected HRU diagnostic; other HRUs remain SWAT' if args.hru else 'Full basin',
                  started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    (target/'run.json').write_text(json.dumps(metadata,indent=2)+'\n')
    start=time.monotonic()
    with (target/'console.log').open('wb') as log:
        result=subprocess.run([str(exe)],cwd=target,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    metadata.update(exit_code=result.returncode,seconds=time.monotonic()-start,
                    completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    (target/'run.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({k:metadata[k] for k in ('case','exit_code','seconds','executable_sha256')}))
    raise SystemExit(result.returncode)
if __name__=='__main__':
    main()

"""Run one Canadian experiment; preserve executable provenance, input checks, exit and log."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
import shutil

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'swatplus_addFT'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['official','existing_ft','shaw','coupling_off'])
    args=parser.parse_args()
    directory=ROOT/'validation/canada'/args.mode
    choices={
        'official':OLD/'validation_baselines/swatplus_61c940f_clean/build_clean',
        'existing_ft':OLD/'build/debug',
        'shaw':ROOT/'build/coupled','coupling_off':ROOT/'build/coupled'}
    exes=list(choices[args.mode].glob('swatplus-*.exe'))
    if len(exes)!=1:
        raise SystemExit(f'Expected one model executable: {exes}')
    exe=exes[0]
    manifest=json.loads((directory.parent/'input_manifest.json').read_text())['sha256']
    for name,digest in manifest.items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=digest:
            raise SystemExit(f'Input mismatch: {name}')
    env=os.environ.copy()
    env['SWAT_SHAW']='1' if args.mode=='shaw' else '0'
    env.pop('SWAT_SHAW_HRU',None) # Full comparison always uses all eligible HRUs.
    previous=directory/'run.json'
    if previous.exists():
        old=json.loads(previous.read_text())
        stamp=old['started_utc'].replace(':','').replace('+','_')
        history=directory/'history'/stamp
        history.mkdir(parents=True,exist_ok=True)
        for name in ('run.json','console.log','shaw_hru_daily.csv','shaw_failed_column.bin'):
            if (directory/name).exists():shutil.copy2(directory/name,history/name)
    metadata={'mode':args.mode,'executable':str(exe),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
              'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'input_files':len(manifest)}
    if args.mode in ('shaw','coupling_off'):
        sources=sorted((ROOT/'src/shaw').glob('*.*'))+[ROOT/'src/shaw_swat_module.f90',
            ROOT/'src/hru_control.f90',ROOT/'src/surface.f90',ROOT/'src/pl_waterup.f90']
        metadata['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_file()}
        metadata['source_base_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    start=time.monotonic()
    (directory/'run.json').write_text(json.dumps(metadata,indent=2))
    with (directory/'console.log').open('wb') as log:
        result=subprocess.run([str(exe)],cwd=directory,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    metadata.update(exit_code=result.returncode,seconds=time.monotonic()-start,
                    completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    (directory/'run.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(metadata))
    raise SystemExit(result.returncode)

if __name__=='__main__':
    main()

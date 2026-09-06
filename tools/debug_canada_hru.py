"""Run one selected SHAW HRU to isolate a failure; never publish this as the basin comparison."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('hru',type=int)
    args=parser.parse_args()
    source=ROOT/'validation/canada/inputs'
    target=source.parent/f'debug_hru_{args.hru}'
    target.mkdir(exist_ok=True)
    for name in json.loads((source.parent/'input_manifest.json').read_text())['sha256']:
        shutil.copy2(source/name,target/name)
    env=os.environ.copy();env['SWAT_SHAW']='1';env['SWAT_SHAW_HRU']=str(args.hru)
    exe,=list((ROOT/'build/coupled').glob('swatplus-*.exe'))
    start=time.monotonic()
    with (target/'console.log').open('wb') as log:
        result=subprocess.run([str(exe)],cwd=target,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    print(json.dumps({'hru':args.hru,'directory':str(target),'exit_code':result.returncode,'seconds':time.monotonic()-start}))

if __name__=='__main__':main()

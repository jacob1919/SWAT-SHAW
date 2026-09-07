"""Check native plant/weather diagnostics after restricting legacy transport to downward flux."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]


def inspect_plant_output(path, selected):
    rows=0;percolation=[];seen=set()
    with path.open() as stream:
        next(stream);headers=next(stream).split();next(stream)
        names=headers[7:32]
        if len(names)!=25 or names[12]!='percn':raise ValueError('Unexpected native plant/weather format')
        for line in stream:
            if not line.strip():continue
            hru=int(line[24:32])
            if hru not in selected:continue
            key=(int(line[18:24]),int(line[:6]),hru)
            if key in seen:raise ValueError(f'Duplicate plant/weather record: {key}')
            seen.add(key)
            values={name:float(line[58+12*i:70+12*i]) for i,name in enumerate(names)}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError(f'Nonfinite plant/weather diagnostic: {key}')
            if values['percn']<0:raise ValueError(f'Negative nitrate export from the bottom boundary: {key}')
            if values['bioms']<0 or values['nplt']<0:raise ValueError(f'Negative plant mass: {key}')
            rows+=1;percolation.append(values['percn'])
    if rows!=850*len(selected):raise ValueError(f'Incomplete plant/weather output: {rows}')
    return {'hru_daily_rows':rows,'finite_numeric_fields_per_row':25,'negative_bottom_nitrate_exports':0,
        'max_bottom_nitrate_export_kg_ha_day':max(percolation),
        'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def check_transport(hru=None):
    directory=ROOT/'validation/canada'/('shaw' if hru is None else f'debug_hru_{hru}')
    run=json.loads((directory/'run.json').read_text())
    if run.get('exit_code')!=0:raise ValueError('Complete the selected run first')
    with (directory/'shaw_hru_scope.csv').open() as stream:
        selected={int(row['hru']) for row in csv.DictReader(stream) if row['coupled'].strip()=='T'}
    if hru is not None and selected!={hru}:raise ValueError('Unexpected diagnostic HRU scope')
    result={'status':'pass','coupled_executable_sha256':run.get('sha256',run.get('executable_sha256')),
        'hrus':sorted(selected),'evaluation_days':850,
        'checks':inspect_plant_output(directory/'hru_pw_day.txt',selected),
        'scope':'Finite native plant/weather output and nonnegative nitrate export only; not validation of solute physics. SHAW retains signed water internally; legacy SWAT transport receives positive daily net downward water flux, including its vapor contribution. Upward solute transport is not represented.'}
    name='transport_compatibility.json' if hru is None else f'transport_compatibility_hru{hru}.json'
    (ROOT/'reports/canada'/name).write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hru',type=int)
    args=parser.parse_args()
    print(json.dumps(check_transport(args.hru),indent=2))

"""Create immutable, byte-matched Canadian experiment inputs without editing prior runs."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'swatplus_addFT'
SOURCE = OLD / 'validation_data/canada_swatplus_usergroup_2025-10-20/extracted/TxtInOut'
CORRECTED = OLD / 'validation_runs/canada_swatplus_usergroup_2025-10-20/clean_official_61c940f'
TARGET = ROOT / 'validation/canada'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    inputs = TARGET / 'inputs'
    inputs.mkdir(exist_ok=True)
    # Original archive includes old generated .out/.txt files and executables.
    files = [p for p in SOURCE.iterdir() if p.is_file() and p.suffix.lower() not in
             {'.exe', '.dll', '.out', '.txt', '.log', '.csv'}]
    if not files or not (SOURCE/'file.cio').exists():
        raise SystemExit('Missing original Canadian input files')
    for src in files:
        target = inputs/src.name
        if target.exists():
            continue
        shutil.copy2(CORRECTED/src.name if src.name == 'soils.sol' else src, target)
    prt = inputs/'print.prt'
    text = prt.read_text()
    daily = {'basin_wb','basin_pw','basin_aqu','basin_sd_cha','channel_sd','hru_wb','hru_pw','aquifer'}
    lines = text.splitlines()
    for i,line in enumerate(lines):
        fields=line.split()
        if fields and fields[0] in daily and len(fields)==5:
            fields[1]='y'
            lines[i]=' '.join(fields)
    prt.write_text('\n'.join(lines)+'\n',encoding='ascii')
    manifest = {p.name:sha(p) for p in sorted(inputs.iterdir()) if p.is_file()}
    for mode in ('official','existing_ft','shaw','coupling_off'):
        folder=TARGET/mode
        folder.mkdir(exist_ok=True)
        for name, digest in manifest.items():
            target=folder/name
            if target.exists() and sha(target)!=digest:
                raise SystemExit(f'Refusing to overwrite differing experiment input: {target}')
            if not target.exists():
                shutil.copy2(inputs/name,target)
    (TARGET/'input_manifest.json').write_text(json.dumps({
        'source':str(SOURCE),'soil_correction_source':str(CORRECTED/'soils.sol'),
        'changes':'hydrologic group 3 -> C from corrected prior run; identical daily output flags',
        'sha256':manifest},indent=2)+'\n')
    print(f'Prepared {len(manifest)} byte-matched inputs in four isolated run directories')

if __name__=='__main__':
    main()

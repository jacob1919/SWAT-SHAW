"""Verify Canadian AWC provenance and prepare a separate, unit-corrected input set.

Only QCBLF33000A with the exact documented four-layer match is accepted.
The original inputs and historical simulations are never modified.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/canada_awc'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def retention(layer, awc):
    # Analytical reproduction of soil_phys_init; not a binary32 runtime dump.
    bd, clay = layer[1], layer[5]
    por = 1. - bd / 2.65
    awc = min(.8, max(.005, awc))
    wp = max(.005, .4 * clay * bd / 100.)
    fc = wp + awc
    fallback = False
    if fc >= por:
        fc = por - .05
        wp = fc - awc
        if wp <= 0.:
            fc, wp, fallback = .75 * por, .25 * por, True
    b = math.log(153. / 3.36) / math.log(fc / wp)
    return dict(porosity=por, field_capacity=fc, wilting_point=wp,
                effective_awc=fc-wp, fallback=fallback,
                campbell_b=b, air_entry_m=-3.36*(fc/por)**b)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    source = json.loads((REPORT/'cansis_source.json').read_text())
    input_dir = ROOT/'validation/canada/inputs'
    original = (input_dir/'soils.sol').read_bytes()
    lines = original.decode('utf8').splitlines(keepends=True)
    header = lines[2].split()
    assert header[0] == source['soil_id'] and int(header[1]) == 4
    assert len([line for line in lines[3:] if line.strip()]) == 4
    findings = []
    corrected = list(lines)
    top = 0.
    for number, (line, ref) in enumerate(zip(lines[3:7], source['layers']), 1):
        tokens = list(re.finditer(r'\S+', line))
        vals = [float(token[0]) for token in tokens]
        expected = [ref[0]*10.,ref[1],ref[2]*10.,*ref[3:8]]
        observed = [vals[i] for i in (0,1,3,4,5,6,7,8)]
        assert observed == expected, (number, observed, expected)
        awc_percent = ref[8]-ref[9]
        assert vals[2] == awc_percent, (number, vals[2], awc_percent)
        awc = awc_percent/100.
        token = tokens[2]
        corrected[number+2] = line[:token.start()] + f'{awc:.5f}'.rjust(len(token[0])) + line[token.end():]
        findings.append(dict(layer=number,depth_bottom_mm=vals[0],thickness_mm=vals[0]-top,
                             non_awc_attributes_matched=8,kp33_percent=ref[8],kp1500_percent=ref[9],
                             raw_awc=vals[2],corrected_awc=awc,
                             raw_initialized=retention(vals,vals[2]),
                             corrected_initialized=retention(vals,awc)))
        top = vals[0]
    revised = ''.join(corrected).encode('utf8')
    result = dict(soil_id=source['soil_id'],source_file='cansis_source.json',
                  original_soil_sha256=digest(original),corrected_soil_sha256=digest(revised),
                  conclusion='Four exact layer matches support conversion of AWC percent to fraction.',
                  limitation='Export code not recovered; modal soil attributes are not local field measurements.',
                  layers=findings,
                  raw_available_capacity_mm=sum(r['thickness_mm']*r['raw_initialized']['effective_awc'] for r in findings),
                  corrected_available_capacity_mm=sum(r['thickness_mm']*r['corrected_initialized']['effective_awc'] for r in findings))
    (REPORT/'audit.json').write_text(json.dumps(result,indent=2)+ '\n')
    if args.prepare:
        target = input_dir.parent/'interface_review/inputs_awc_corrected'
        target.mkdir(parents=True,exist_ok=True)
        manifest = json.loads((input_dir.parent/'input_manifest.json').read_text())['sha256']
        updated = {}
        for name, expected in manifest.items():
            data = (input_dir/name).read_bytes()
            assert digest(data) == expected, ('Historical input drift', name)
            data = revised if name == 'soils.sol' else data
            destination = target/name
            if destination.exists():
                assert destination.read_bytes() == data, ('Refuse to overwrite differing input', destination)
            else:
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(data)
            updated[name] = digest(data)
        output = dict(source_manifest='../input_manifest.json',change='Only four AWC entries divided by 100',
                      evidence='reports/canada_awc/audit.json',sha256=updated)
        (target.parent/'input_manifest_awc_corrected.json').write_text(json.dumps(output,indent=2)+ '\n')
        print('Prepared', target)
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()

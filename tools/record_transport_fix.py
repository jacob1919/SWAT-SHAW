"""Record the preserved HRU-1 counterexample and current transport-interface checks."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder=ROOT/'validation/canada/debug_hru_1'
    prior_run=json.loads((folder/'run_before_transport.json').read_text())
    current=json.loads((folder/'run.json').read_text())
    old=folder/'pw_before_transport.txt'
    overflows=0;first=None
    with old.open() as stream:
        next(stream);header=next(stream).split();next(stream)
        index=header.index('percn')-7
        for line in stream:
            if not line.strip() or int(line[24:32])!=1:continue
            value=line[58+12*index:70+12*index].strip()
            if '*' not in value:continue
            overflows+=1
            if first is None:first={'year':int(line[18:24]),'jday':int(line[:6]),'hru':1,'printed_percn':value}
    assert overflows>0
    old_checks=json.loads(subprocess.check_output(['git','show',
        'fb75b4697f65ccf604c4e261b2ad018cbfdef578:reports/canada/canopy_solver_checks.json'],cwd=ROOT,text=True))
    new_checks=json.loads((ROOT/'reports/canada/canopy_solver_checks.json').read_text())
    parity={hru:{'daily_csv_sha256':record['daily_csv_sha256'],
        'equal_to_pre_transport_fix':record['daily_csv_sha256']==old_checks['hrus'][hru]['daily_csv_sha256']}
        for hru,record in new_checks['hrus'].items()}
    assert all(check['equal_to_pre_transport_fix'] for check in parity.values())
    transport={str(hru):json.loads((ROOT/f'reports/canada/transport_compatibility_hru{hru}.json').read_text()) for hru in (1,6,19,98)}
    assert all(item['status']=='pass' and item['coupled_executable_sha256']==current['executable_sha256'] for item in transport.values())
    result={'status':'pass','coupled_executable_sha256':current['executable_sha256'],
        'prior_executable_sha256':prior_run['executable_sha256'],
        'prior_hru1_percn_overflow_days':overflows,'first_prior_overflow':first,
        'prior_hru1_pw_sha256':digest(old),'isolated_transport_checks':transport,
        'four_hru_water_heat_trajectory_checks':parity,
        'method':'Map the positive daily net horizon water flux to legacy SWAT prk. Do not alter signed SHAW water/heat state. Upward solute transfer and vapor/liquid separation remain outside this compatibility restriction.',
        'scope':'The four complete isolated water/heat trajectories remain byte-identical in this case. This does not establish nutrient or water-quality accuracy, or substitute for a completed basin run.'}
    (ROOT/'reports/canada/transport_fix_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'overflow_days_before':overflows,'hrus_checked':list(parity),'water_heat_trajectories_unchanged':True,'current_sha256':current['executable_sha256']}))


if __name__=='__main__':main()

"""Compare complete basin HRU trajectories against the isolated diagnostic runs."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    basin=ROOT/'validation/canada/shaw'
    metadata=json.loads((basin/'run.json').read_text())
    assert metadata.get('exit_code')==0,'Complete the coupled basin run first'
    references={};seen={};hashes={}
    for hru in (1,6,19,98):
        directory=ROOT/f'validation/canada/debug_hru_{hru}'
        check=json.loads((directory/'run.json').read_text())
        assert check['exit_code']==0 and check['executable_sha256']==metadata['sha256']
        path=directory/'shaw_hru_daily.csv'
        with path.open() as stream:
            records=list(csv.DictReader(stream))
        assert len(records)==1216
        references[hru]={(r['year'],r['jday']):r for r in records}
        assert len(references[hru])==1216
        hashes[hru]=digest(path);seen[hru]=set()
    columns=None;path=basin/'shaw_hru_daily.csv'
    with path.open() as stream:
        for row in csv.DictReader(stream):
            hru=int(row['hru'])
            if hru not in references:continue
            key=row['year'],row['jday']
            assert key not in seen[hru]
            assert row==references[hru][key],f'Basin versus isolated HRU differs: {hru}/{key}'
            seen[hru].add(key);columns=len(row)
    assert all(len(keys)==1216 for keys in seen.values())
    result={'status':'pass','coupled_executable_sha256':metadata['sha256'],
        'days_per_hru':1216,'hrus':[1,6,19,98],'daily_rows_compared':sum(map(len,seen.values())),
        'columns_per_row':columns,'different_values':0,'comparison':'Exact printed daily states, fluxes and retry counters',
        'basin_daily_csv_sha256':digest(path),'isolated_daily_csv_sha256':hashes,
        'scope':'These HRUs have no upstream HRU surface-water or aquifer inflow in this Canadian case; exact parity is expected.'}
    target=ROOT/'reports/canada/basin_column_parity.json'
    target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()

"""Record complete isolated-column checks and their executable/data provenance."""
from pathlib import Path
import csv
import datetime as dt
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]

def read_csv(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    off=json.loads((ROOT/'validation/canada/coupling_off/run.json').read_text())
    assert off['exit_code']==0
    result={'scope':'Isolated HRU checks; other HRUs use original SWAT+. Not the full basin comparison.',
            'executable_sha256':off['sha256'],'hrus':{}}
    for hru in (1,6,19,98):
        directory=ROOT/f'validation/canada/debug_hru_{hru}'
        metadata=json.loads((directory/'run.json').read_text())
        assert metadata['exit_code']==0 and metadata['executable_sha256']==off['sha256']
        path=directory/'shaw_hru_daily.csv';rows=read_csv(path)
        dates=[dt.date(int(r['year']),1,1)+dt.timedelta(days=int(r['jday'])-1) for r in rows]
        assert dates==[dt.date(2020,1,1)+dt.timedelta(days=i) for i in range(1216)]
        assert {int(r['hru']) for r in rows}=={hru}
        maximum=max(abs(float(r['residual_mm'])) for r in rows)
        assert maximum<=.10001
        summary={'days':len(rows),'maximum_daily_water_residual_mm':maximum,
                 'totals_mm':{k:sum(float(r[k]) for r in rows) for k in
                              ('et_mm','runoff_mm','percolation_mm','lateral_mm','residual_mm')},
                 'retry_hours':int(sum(float(r['retry_hours']) for r in rows)),
                 'jacobian_retry_hours':int(sum(float(r['jacobian_retry_hours']) for r in rows)),
                 'maximum_hour_parts':int(max(float(r['max_hour_parts']) for r in rows)),
                 'seconds':metadata['seconds'],'daily_csv_sha256':digest(path)}
        hourly_path=directory/'shaw_hru_hourly.csv';hourly=read_csv(hourly_path)
        assert len(hourly)==24*len(rows)
        maximum_root_error=max(abs(float(r['root_uptake_mm'])-float(r['transpiration_mm'])) for r in hourly)
        assert maximum_root_error<=1.0001e-6
        summary['hourly_check']={'hours':len(hourly),
            'max_abs_root_uptake_minus_transpiration_mm':maximum_root_error,
            'max_abs_water_residual_mm':max(abs(float(r['residual_mm'])) for r in hourly),
            'csv_sha256':digest(hourly_path)}
        if hru==1:
            old_path=directory/'daily_before_root_partition.csv';old=read_csv(old_path)
            before=next(r for r in old if int(r['year'])==2021 and int(r['jday'])==197)
            after=next(r for r in rows if int(r['year'])==2021 and int(r['jday'])==197)
            summary['previous_budget_failure']={'year':2021,'jday':197,
                'before_root_fix_daily_residual_mm':float(before['residual_mm']),
                'current_daily_residual_mm':float(after['residual_mm']),
                'baseline_csv_sha256':digest(old_path)}
        if hru==98:
            old_path=directory/'shaw_hru_daily_before_damping.csv';old=read_csv(old_path)
            assert len(old)==len(rows)
            for a,b in zip(old,rows):
                assert all(a[k]==b[k] for k in ('year','jday','hru','precip_mm'))
            changes={}
            for k in ('et_mm','runoff_mm','percolation_mm'):
                a=sum(float(r[k]) for r in old);b=summary['totals_mm'][k]
                changes[k]={'before_conductance_retry_and_root_fix':a,'current':b,'percent_change':100*(b-a)/a}
            summary['limited_strategy_sensitivity']={'baseline_csv_sha256':digest(old_path),
                'scope':'Same HRU, forcing and selected tolerances; before versus after conductance-Jacobian retry, root active-set correction and minimum-step safeguards. Not grid/time convergence or field skill.',
                'totals':changes,'max_daily_topsoil_temperature_difference_C':
                    max(abs(float(a['tsoil_C'])-float(b['tsoil_C'])) for a,b in zip(old,rows))}
        result['hrus'][str(hru)]=summary
    target=ROOT/'reports/canada/canopy_solver_checks.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()

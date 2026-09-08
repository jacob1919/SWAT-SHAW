"""Audit completed interface cases without altering the historical comparison."""
from pathlib import Path
import csv
import datetime as dt
import json
import math
import hashlib

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'validation/canada/interface_review'
OUT=ROOT/'reports/interface_cases'
FIELDS=('precip_mm','et_mm','runoff_mm','percolation_mm','lateral_mm','snow_liquid_release_mm')
DATES=[(dt.date(2020,1,1)+dt.timedelta(days=d)) for d in range(1216)]

def read_native(path):
    with path.open() as f:
        next(f);header=next(f).split();next(f)
        if path.name.startswith('basin_') and header[-2:]==['plant_cov','mgt_ops']:
            header=header[:-2]
        rows=[]
        for line in f:
            v=line.split()
            if not v:continue
            assert len(v)==len(header),path
            row=dict(zip(header,v))
            rows.append(row)
    return rows

def ledger(directory):
    with (directory/'shaw_hru_scope.csv').open() as f:
        area={int(r['hru']):float(r['area_ha']) for r in csv.DictReader(f) if r['coupled']=='T'}
    total=sum(area.values())
    result=dict(hru_days=0,max_abs_residual_mm=0.,evaluation_totals_mm={k:0. for k in FIELDS},
                max_ice_mm=0.,max_swe_mm=0.,max_hour_parts=1,forcing_height=[],daily_precipitation_checked=False)
    seen=set();by_key={}
    with (directory/'shaw_hru_daily.csv').open() as f:
        for r in csv.DictReader(f):
            v={k:float(x) for k,x in r.items()}
            assert all(math.isfinite(x) for x in v.values())
            h=int(v['hru']);year=int(v['year']);day=int(v['jday'])
            date=dt.date(year,1,1)+dt.timedelta(days=day-1)
            key=(date,h)
            assert key not in seen and h in area and date in DATES
            seen.add(key);by_key[(year,day,h)]=v
            residual=v['storage_end_mm']-v['storage_start_mm']-v['precip_mm']-v['external_soil_mm']-v['surface_input_mm']-v['canopy_air_exchange_mm']+v['et_mm']+v['runoff_mm']+v['percolation_mm']+v['lateral_mm']
            assert abs(residual-v['residual_mm'])<2.e-6, (directory,key,residual)
            result['hru_days']+=1
            result['max_abs_residual_mm']=max(result['max_abs_residual_mm'],abs(v['residual_mm']))
            result['max_hour_parts']=max(result['max_hour_parts'],v['max_hour_parts'])
            if year>=2021:
                for k in FIELDS:result['evaluation_totals_mm'][k]+=v[k]*area[h]/total
                result['max_ice_mm']=max(result['max_ice_mm'],v['ice_mm'])
                result['max_swe_mm']=max(result['max_swe_mm'],v['swe_mm'])
    assert seen=={(d,h) for d in DATES for h in area},directory
    assert result['max_abs_residual_mm']<=.10001
    result['coupled_hrus']=sorted(area)
    result['snow_native_mapping_checked']=0
    for r in read_native(directory/'hru_wb_day.txt'):
        h=int(r['unit']);key=(int(r['yr']),int(r['jday']),h)
        if h in area:
            assert abs(float(r['snomlt'])-by_key[key]['snow_liquid_release_mm'])<=.0011,(directory,key,'snow mapping')
            result['snow_native_mapping_checked']+=1
    assert result['snow_native_mapping_checked']==850*len(area)
    hourly=directory/'shaw_hru_hourly.csv'
    if hourly.exists():
        rain={}
        with hourly.open() as f:
            for r in csv.DictReader(f):
                key=(int(r['year']),int(r['jday']),int(r['hru']))
                rain[key]=rain.get(key,0.)+float(r['precip_mm'])
        assert set(rain)==set(by_key)
        assert all(abs(v-by_key[k]['precip_mm'])<1.e-6 for k,v in rain.items())
        result['daily_precipitation_checked']=True
    result['configuration']=list(csv.DictReader((directory/'shaw_configuration.csv').open()))
    return result

def regression():
    a=DATA/'awc_official';b=DATA/'awc_coupling_off'
    if not all((d/'run.json').exists() and json.loads((d/'run.json').read_text()).get('exit_code')==0 for d in (a,b)):return None
    count=rows=0
    for path in a.glob('*.txt'):
        other=b/path.name
        x=path.read_text().splitlines();y=other.read_text().splitlines()
        assert x[1:]==y[1:],path.name
        count+=1;rows+=max(0,len(x)-3)
    assert count>=90
    return dict(files_identical_after_banner=count,data_rows=rows)

def legacy_parity():
    old=ROOT/'validation/canada/debug_hru_1/shaw_hru_daily.csv'
    new=DATA/'legacy_hru1/shaw_hru_daily.csv'
    status=DATA/'legacy_hru1/run.json'
    if not status.exists() or json.loads(status.read_text()).get('exit_code')!=0:return None
    with old.open() as a,new.open() as b:
        before=list(csv.DictReader(a));after=list(csv.DictReader(b))
    assert len(before)==len(after)==1216
    compared=0
    for x,y in zip(before,after):
        for k,v in x.items():
            assert float(v)==float(y[k]),(k,x['year'],x['jday'],v,y[k])
            compared+=1
    return dict(hru=1,days=1216,values_compared=compared,different_values=0)

def main():
    OUT.mkdir(exist_ok=True)
    result=dict(cases={},coupling_off_regression=regression(),legacy_configuration_parity=legacy_parity())
    for path in sorted(DATA.glob('*/run.json')):
        status=json.loads(path.read_text())
        case=dict(status='complete' if status.get('exit_code')==0 else 'running' if 'exit_code' not in status else 'failed',
                  settings=status['case'],executable_sha256=status['executable_sha256'],seconds=status.get('seconds'))
        result['cases'][path.parent.name]=case
        if case['status']!='complete':continue
        if status['case']['model']=='shaw':
            case['ledger']=ledger(path.parent)
        else:
            rows=read_native(path.parent/'basin_wb_day.txt')
            assert len(rows)==850
            case['basin_evaluation_totals_mm']={k:sum(float(r[k]) for r in rows) for k in ('precip','et','surq_gen','perc','latq')}
    result['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted((ROOT/'src/shaw').glob('*.*'))+[ROOT/'src/shaw_swat_module.f90'] if p.is_file()}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

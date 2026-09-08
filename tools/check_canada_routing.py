"""Identify the outlet drainage area and the reservoir rule controlling outlet pulses."""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]


def table(path):
    lines=path.read_text().splitlines()
    return lines[1].split(),[line.split() for line in lines[2:] if line.strip()]


def check_routing():
    data=ROOT/'validation/canada';inputs=data/'inputs'
    incoming=[];outlets=[]
    for path in inputs.glob('*.con'):
        headers,rows=table(path)
        if 'out_tot' not in headers:continue
        index=headers.index('out_tot')
        for row in rows:
            count=int(row[index])
            if path.name=='chandeg.con' and count==0:
                outlets.append({'id':int(row[0]),'area_ha':float(row[headers.index('area')])})
            for n in range(count):
                typ,target,hyd,frac=row[index+1+4*n:index+5+4*n]
                if typ=='sdc' and int(target)==76:
                    incoming.append({'file':path.name,'id':int(row[0]),'name':row[1],'hyd_type':hyd,'fraction':float(frac)})
    assert len(outlets)==1 and outlets[0]['id']==76
    assert {(r['file'],r['id']) for r in incoming}=={('aquifer.con',5),('reservoir.con',1),('rout_unit.con',97)},incoming
    with (data/'shaw/shaw_hru_scope.csv').open() as f:
        hru_area=sum(float(row['area_ha']) for row in csv.DictReader(f) if float(row['area_ha'])>0)
    headers,rows=table(inputs/'reservoir.con')
    reservoir_area=sum(float(row[headers.index('area')]) for row in rows)
    area=outlets[0]['area_ha']
    assert math.isclose(area,hru_area+reservoir_area,abs_tol=.01)
    headers,rows=table(inputs/'ls_unit.ele')
    land_weight=sum(float(row[headers.index('bsn_frac')]) for row in rows if row[headers.index('obj_typ')]=='hru')
    assert abs(land_weight-1)<1.e-4
    headers,rows=table(inputs/'hydrology.res')
    hydro=dict(zip(headers,rows[0]));pvol=float(hydro['vol_ps'])*10000.
    headers,rows=table(inputs/'reservoir.res')
    assert rows[0][headers.index('rel')]=='drawdown_days'
    lines=(inputs/'res_rel.dtl').read_text().splitlines()
    start=next(i for i,line in enumerate(lines) if line.split() and line.split()[0]=='drawdown_days')
    header=next(i for i in range(start+1,len(lines)) if lines[i].split() and lines[i].split()[0]=='act_typ')
    actions=[line.split() for line in lines[header+1:header+3]]
    assert [(r[4],float(r[5]),float(r[6]),r[7]) for r in actions]==[('days',15.,0.,'pvol'),('days',5.,0.,'evol')]
    peaks={}
    for mode in ('official','existing_ft','shaw'):
        headers,rows=table(data/mode/'channel_sd_day.txt')
        # The third line is units; skip it, retaining every null placeholder.
        selected=[row for row in rows[1:] if int(row[headers.index('unit')])==76]
        values=[float(row[headers.index('flo_out')]) for row in selected]
        assert len(values)==850
        large=[q for q in values if q>1.]
        peaks[mode]={'days_outlet_flow_above_1_m3s':len(large),
            'fraction_of_integrated_outlet_volume_on_those_days':sum(large)/sum(values),
            'minimum_on_those_days_m3s':min(large),'maximum_m3s':max(values)}
    names=('chandeg.con','reservoir.con','reservoir.res','hydrology.res','res_rel.dtl','ls_unit.ele')
    runs={mode:json.loads((data/mode/'run.json').read_text()) for mode in ('official','existing_ft','shaw')}
    assert all(run.get('exit_code')==0 and run.get('completed_utc') for run in runs.values())
    result={'status':'pass','coupled_executable_sha256':runs['shaw']['sha256'],
        'outlet_channel':76,'direct_upstream_objects':incoming,
        'outlet_drainage_area_ha':area,'outlet_drainage_area_km2':area/100,
        'hru_land_area_ha':hru_area,'reservoir_polygon_area_ha':reservoir_area,
        'area_rounding_difference_ha':area-hru_area-reservoir_area,'native_land_output_weight_sum':land_weight,
        'release_rule':'drawdown_days','principal_storage_m3':pvol,
        'days_above_principal':15,'days_above_emergency':5,'const2_storage_multiplier':0,
        'principal_threshold_release_scale_m3s':pvol/15/86400,
        'rule_interpretation':'In pinned res_hydro, days uses b_lo=reference_volume*const2. Here const2=0, so a triggered principal-storage action releases total current volume/15, not merely volume above principal storage. Refilling and triggering can produce pulses near 9 m3/s.',
        'outlet_high_flow_diagnostic':peaks,
        'scope':'Routing configuration and printed outlet diagnostics, not an observed flood attribution. Reservoir daily output was not enabled. HRU water/plant summaries use land fractions; outlet runoff depth uses terminal-channel drainage area.',
        'input_sha256':{name:hashlib.sha256((inputs/name).read_bytes()).hexdigest() for name in names}}
    (ROOT/'reports/canada/routing_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':print(json.dumps(check_routing(),indent=2))

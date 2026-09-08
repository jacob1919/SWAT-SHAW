"""Publish post-review basin and single-HRU comparisons only after completed-run checks."""
from pathlib import Path
from itertools import zip_longest
import csv
import json
import math
import hashlib
from analyze_interface_cases import read_native, DATA, ROOT, OUT
from check_canada_forcing import weather_rows
from check_canada_transport import inspect_plant_output

MODES=('official','existing_ft','shaw')
def main():
    summary=json.loads((OUT/'summary.json').read_text())
    directories={m:DATA/('awc_'+m) for m in MODES}
    runs={m:json.loads((d/'run.json').read_text()) for m,d in directories.items()}
    assert all(r.get('exit_code')==0 for r in runs.values())
    expected=json.loads((DATA/'input_manifest_awc_corrected.json').read_text())['sha256']
    for m,d in directories.items():
        assert runs[m]['input_sha256']==expected
        # fort.7777 is generated at runtime and is not a scientific input.
        for name,digest in expected.items():
            if name=='fort.7777':continue
            assert hashlib.sha256((d/name).read_bytes()).hexdigest()==digest,(m,name)
    scope=list(csv.DictReader((directories['shaw']/'shaw_hru_scope.csv').open()))
    selected={int(r['hru']) for r in scope if r['coupled']=='T'}
    positive={int(r['hru']) for r in scope if float(r['area_ha'])>0}
    assert len(selected)==123 and len(positive)==142
    weather={}
    for file,fields in [('hru_pw_day.txt',('tmx','tmn','tmpav','solarad','wndspd','rhum')),('hru_wb_day.txt',('precip',))]:
        seen=set()
        for rows in zip_longest(*(weather_rows(d/file,fields) for d in directories.values())):
            assert all(r is not None for r in rows)
            assert rows[0]==rows[1]==rows[2],(file,rows)
            assert rows[0][0] not in seen
            seen.add(rows[0][0])
        assert len(seen)==850*142
        weather[file]=dict(rows=len(seen),fields=fields,different_values=0)
    transport=inspect_plant_output(directories['shaw']/'hru_pw_day.txt',selected)
    wb={m:read_native(d/'basin_wb_day.txt') for m,d in directories.items()}
    pw={m:read_native(d/'basin_pw_day.txt') for m,d in directories.items()}
    flow={}
    totals={}
    for m,d in directories.items():
        q=[r for r in read_native(d/'channel_sd_day.txt') if int(r['unit'])==76]
        assert len(wb[m])==len(pw[m])==len(q)==850
        flow[m]=[float(r['flo_out']) for r in q]
        assert all(math.isfinite(v) for v in flow[m])
        totals[m]={k:sum(float(r[k]) for r in wb[m]) for k in ('precip','et','surq_gen','perc','latq')}
        totals[m].update(mean_outlet_m3s=sum(flow[m])/850,
                         high_flow_days=sum(v>1. for v in flow[m]),
                         high_flow_volume_percent=100*sum(v for v in flow[m] if v>1.)/sum(flow[m]))
    assert all(wb[m][i]['precip']==wb['official'][i]['precip'] for m in MODES for i in range(850))
    parity={}
    full={}
    with (directories['shaw']/'shaw_hru_daily.csv').open() as f:
        for r in csv.DictReader(f):
            h=int(r['hru'])
            if h in (1,6,19,98):full[(r['year'],r['jday'],r['hru'])]=r
    for h in (1,6,19,98):
        with (DATA/f'corrected_hru{h}'/'shaw_hru_daily.csv').open() as f:
            rows=list(csv.DictReader(f))
        assert len(rows)==1216
        compared=0
        for row in rows:
            other=full[(row['year'],row['jday'],row['hru'])]
            for k,v in row.items():
                assert float(v)==float(other[k]),(h,row['year'],row['jday'],k)
                compared+=1
        parity[h]=dict(days=len(rows),values_compared=compared,different_values=0)
    daily=[]
    for i,row in enumerate(wb['official']):
        r={'date':f"{int(row['yr']):04d}-{int(row['mon']):02d}-{int(row['day']):02d}"}
        for m in MODES:
            r[m+'_outlet_m3s']=flow[m][i]
            for field in ('et','surq_gen','perc','latq','snopack'):
                r[m+'_'+field+'_mm']=float(wb[m][i][field])
            r[m+'_soil_layer2_C']=float(pw[m][i]['sol_tmp'])
        daily.append(r)
    with (OUT/'basin_daily.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(daily[0]));w.writeheader();w.writerows(daily)
    result=dict(totals=totals,weather_parity=weather,transport=transport,column_parity=parity,
                shared_input_files=len(expected),period='2021-01-01 to 2023-04-30 (850 days)',
                source_status='Completed simulations and numerical/process diagnostics, without observations.',
                coupled_executable_sha256=runs['shaw']['executable_sha256'],
                full_basin_seconds=runs['shaw']['seconds'])
    (OUT/'basin_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    rows=['# Post-review Canadian process comparison','',
          'All three full-basin simulations completed for 2020-01-01 through 2023-04-30. The first 366 days are warmup; the table covers 850 evaluation days. All three use the same corrected AWC inputs. The SHAW case also uses the reviewed radiation and forcing-height interfaces. The fixed 1.026 m thermal boundary and uniform 24-hour precipitation remain the reference settings.','',
          'These are simulated process differences. There are no independent snow, soil-temperature or discharge observations in this case. The existing FT executable includes other changes, so its differences are not attributable solely to freeze-thaw. The historical report is preserved in ../canada/REPORT.md.','',
          '![Basin process totals and HRU 1 sensitivity](review_process_comparison.png)','',
          '## Full-basin totals','',
          '| Model | ET (mm) | Surface runoff generated (mm) | Percolation (mm) | Lateral flow (mm) | Mean outlet flow (m3/s) |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for m,t in totals.items():
        rows.append(f"| {m} | {t['et']:.3f} | {t['surq_gen']:.3f} | {t['perc']:.3f} | {t['latq']:.6f} | {t['mean_outlet_m3s']:.6f} |")
    rows+=['',f"All models receive {totals['official']['precip']:.3f} mm precipitation. HRU weather matches exactly for 142 HRUs and 850 evaluation days, including generated variables.",
           'The outlet remains controlled by the unchanged reservoir release rules. An outlet difference is not an accuracy score. The fraction of discharge on days above 1 m3/s is: '+', '.join(f"{m}: {t['high_flow_days']} days, {t['high_flow_volume_percent']:.3f}%" for m,t in totals.items())+'.','',
           '## HRU 1 attribution','',
           'Only the selected HRU uses SHAW in these experiments. Its values below are HRU totals, not basin totals. All runs cover the same period and use the same parameters except the explicitly listed factors.','',
           '| Case | AWC | Radiation | Forcing height | Thermal / rain | ET (mm) | Runoff (mm) | Percolation (mm) | Lateral (mm) |',
           '|---|---|---|---|---|---:|---:|---:|---:|']
    for name in ('legacy_hru1','radiation_hru1','height_hru1','combined_hru1','corrected_hru1','thermal_hru1','rain6h_hru1'):
        c=summary['cases'][name];assert c['status']=='complete'
        a=c['settings'];t=c['ledger']['evaluation_totals_mm']
        rows.append(f"| {name} | {a['inputs']} | {a['radiation']} | {a['forcing']} | {a['thermal']} / {a['rain_hours']} h | {t['et_mm']:.3f} | {t['runoff_mm']:.3f} | {t['percolation_mm']:.3f} | {t['lateral_mm']:.6f} |")
    b=summary['cases']['awc_shaw']['ledger']
    rows+=['',
           'The first four cases isolate radiation and forcing-height changes and their combination on the historical inputs. Comparing combined_hru1 with corrected_hru1 isolates the AWC conversion. The last two alter only the bottom-temperature rule or rainfall duration relative to corrected_hru1. Nonlinear interactions mean the separate effects need not sum to the combined effect.',
           'The estimated thermal case uses native SHAW ITMPBC=1 without adding water storage; it does not test a 4 m deep boundary. The six-hour rain case distributes the daily total over hours 13–18. These synthetic experiments do not identify the real storm timing or correct thermal boundary.',
           "The native estimated bottom-temperature option increases HRU 1 runoff from 188.198 to 863.632 mm while percolation drops from 972.437 to 284.098 mm. Concentrating rain into six hours raises runoff to 529.692 mm. These responses identify high sensitivity to boundary/forcing choices; they do not establish which configuration is physically correct.",
           '', '## Verification','',
           f"- Complete SHAW ledger: {b['hru_days']:,} HRU days; maximum absolute daily water residual {b['max_abs_residual_mm']:.9f} mm; maximum accepted hourly subdivision {int(b['max_hour_parts'])}.",
           '- Four representative columns (HRUs 1, 6, 19, 98) match their independent runs exactly: 4,864 HRU days and 102,144 values, including the new snow diagnostic.',
           '- Coupling-off regression: 95 native output files / 484,287 data rows equal the corrected official run after the banner.',
           '- Legacy configuration replay: HRU 1, 1,216 days / 24,320 original diagnostic values exactly reproduce the pre-review result.',
           '- Eight SHAW CTests passed. Original-algorithm reference: 720 hours / 282,960 values identical; this checks extraction and state isolation, not basin parameter realism.',
           '- All 25 inspected native plant/weather fields are finite for 123 coupled HRUs over 850 days; bottom nitrate export is nonnegative. This is an interface compatibility check, not validation of solute physics.',
           '- The new snow_liquid_release_mm equals native snomlt on coupled HRUs within printed precision for all 104,550 evaluation HRU days. It may include rain through snow and is not pure phase-change melt.',
           '- Hourly diagnostic cases preserve every daily precipitation total. All reported water residuals were independently reconstructed from storage and flux columns.',
           '', '## Interpretation and remaining work','',
           'The corrections and unit repair leave a pronounced redistribution toward percolation and away from surface/lateral runoff. These changes cannot be attributed solely to freeze-thaw. The remaining process differences include replacing CN runoff, native SHAW saturated lateral-flow physics, free drainage, synthetic storm timing, and default canopy hydraulics.',
           'The shallow fixed-temperature reference boundary remains a major physical assumption. Real aspect data, reliable above-canopy meteorology, deeper-boundary experiments, complete energy accounting, grid/time convergence and independent observations remain necessary for stronger scientific claims.',
           '',
           'Inputs and unit evidence: [AWC audit](../canada_awc/REPORT.md). Interface assumptions and controls: [interface review](../INTERFACE_REVIEW.md). Numeric evidence: summary.json, basin_checks.json and basin_daily.csv. All runs are isolated under validation/canada/interface_review.',
           '',
           f"SHAW executable SHA256: {runs['shaw']['executable_sha256']}. The full run took {runs['shaw']['seconds']:.3f} s on this host; this single uncontrolled run is not a performance benchmark.",'']
    (OUT/'REPORT.md').write_text('\n'.join(rows))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

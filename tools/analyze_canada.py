"""Reproducible numerical/process comparison. No discharge observations are supplied."""
from pathlib import Path
from collections import defaultdict
import csv
import datetime as dt
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from check_canada_forcing import check_forcing
from check_canada_transport import check_transport

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'validation/canada'
OUT=ROOT/'reports/canada'
MODES=('official','existing_ft','shaw')
SIMULATION_START=dt.date(2020,1,1)
EVALUATION_START=dt.date(2021,1,1)
SIMULATION_END=dt.date(2023,4,30)

def date_range(start,end):
    return [start+dt.timedelta(days=i) for i in range((end-start).days+1)]

def read_run_status():
    runs={};errors=[]
    for mode in (*MODES,'coupling_off'):
        try:
            runs[mode]=json.loads((DATA/mode/'run.json').read_text())
        except (OSError,ValueError) as exc:
            errors.append(f'{mode}: run metadata unavailable ({exc})')
            continue
        if runs[mode].get('exit_code')!=0 or not runs[mode].get('completed_utc'):
            errors.append(f"{mode}: incomplete or unsuccessful run (exit_code={runs[mode].get('exit_code')})")
    if all(m in runs for m in ('shaw','coupling_off')):
        if not runs['shaw'].get('sha256') or runs['shaw'].get('sha256')!=runs['coupling_off'].get('sha256'):
            errors.append('shaw and coupling_off must use the same executable SHA256; rerun the stale variant')
    return runs,errors

def read_scope():
    with (DATA/'shaw/shaw_hru_scope.csv').open() as f:
        raw=list(csv.DictReader(f))
    scope=[];seen=set();excluded=0
    for row in raw:
        hru=int(row['hru']);area=float(row['area_ha'])
        if hru in seen:raise ValueError(f'Duplicate HRU in scope: {hru}')
        seen.add(hru)
        if not math.isfinite(area) or area<0:raise ValueError(f'Invalid HRU area: {row}')
        if area==0:
            excluded+=1
            continue
        flag=row['coupled'].strip().upper()
        if flag not in ('T','F'):raise ValueError(f'Invalid coupled flag: {row}')
        scope.append({'hru':hru,'area_ha':area,'coupled':flag=='T','reason':row['reason'].strip()})
    if not scope or not any(r['coupled'] for r in scope):raise ValueError('No positive-area coupled HRUs')
    return scope,excluded

def water_budget(scope):
    """Area means use the coupled domain only; all depths are liquid-water equivalent."""
    areas={r['hru']:r['area_ha'] for r in scope if r['coupled']}
    coupled_area=sum(areas.values())
    periods={'full_simulation':(SIMULATION_START,SIMULATION_END),
             'warmup':(SIMULATION_START,EVALUATION_START-dt.timedelta(days=1)),
             'evaluation':(EVALUATION_START,SIMULATION_END)}
    by_day={};seen=set()
    fluxes=('precip_mm','external_soil_mm','surface_input_mm','et_mm','runoff_mm','percolation_mm','lateral_mm',
            'canopy_air_exchange_mm')
    with (DATA/'shaw/shaw_hru_daily.csv').open() as f:
        reader=csv.DictReader(f)
        required={'year','jday','hru','residual_mm','ice_mm','storage_start_mm','storage_end_mm',
                  'retry_hours','max_hour_parts','jacobian_retry_hours',*fluxes}-{'canopy_air_exchange_mm'}
        has_canopy_exchange='canopy_air_exchange_mm' in (reader.fieldnames or [])
        missing=required-set(reader.fieldnames or [])
        if missing:raise ValueError(f'SHAW daily diagnostics missing columns: {sorted(missing)}')
        for row in reader:
            hru=int(row['hru']);year=int(row['year']);jday=int(row['jday'])
            date=dt.date(year,1,1)+dt.timedelta(days=jday-1)
            if date.year!=year or jday<1 or not SIMULATION_START<=date<=SIMULATION_END:
                raise ValueError(f'Invalid SHAW diagnostic date: {year}/{jday}')
            if hru not in areas:raise ValueError(f'Daily diagnostic for an HRU outside the positive-area coupled scope: {hru}')
            key=(date,hru)
            if key in seen:raise ValueError(f'Duplicate SHAW HRU day: {key}')
            seen.add(key)
            values={name:float(row[name]) for name in required-{'year','jday','hru'}}
            values['canopy_air_exchange_mm']=float(row['canopy_air_exchange_mm']) if has_canopy_exchange else 0.
            if not all(math.isfinite(v) for v in values.values()):raise ValueError(f'Nonfinite SHAW diagnostic: {key}')
            retries=values['retry_hours'];parts=values['max_hour_parts']
            jacobian_retries=values['jacobian_retry_hours']
            if not jacobian_retries.is_integer() or not 0<=jacobian_retries<=retries:
                raise ValueError(f'Invalid Jacobian retry counter: {key}')
            if not retries.is_integer() or not 0<=retries<=24 or parts not in (1,2,4,8,16,32,64):
                raise ValueError(f'Invalid retry counters: {key}')
            if abs(values['residual_mm'])>.10001:raise AssertionError(f'Water-budget gate exceeded: {key}')
            reconstructed=(values['storage_end_mm']-values['storage_start_mm']-values['precip_mm']-
                values['external_soil_mm']-values['surface_input_mm']-values['canopy_air_exchange_mm']+
                values['et_mm']+values['runoff_mm']+values['percolation_mm']+values['lateral_mm'])
            if abs(reconstructed-values['residual_mm'])>2.e-6:
                raise ValueError(f'Water ledger does not reproduce reported residual: {key}')
            day=by_day.setdefault(date,defaultdict(float))
            weight=areas[hru]/coupled_area
            day['hru_days']+=1
            day['residual_mm']+=weight*values['residual_mm']
            day['mean_absolute_hru_residual_mm']+=weight*abs(values['residual_mm'])
            day['ice_mm']+=weight*values['ice_mm']
            day['max_abs_residual_mm']=max(day['max_abs_residual_mm'],abs(values['residual_mm']))
            day['retried_hru_hours']+=int(retries)
            day['jacobian_retry_hours']+=int(jacobian_retries)
            day['hru_days_requiring_retry']+=int(retries>0)
            day['max_hour_parts']=max(day['max_hour_parts'],int(parts))
            day['storage_change_mm']+=weight*(values['storage_end_mm']-values['storage_start_mm'])
            for name in fluxes:day[name]+=weight*values[name]
    expected=date_range(SIMULATION_START,SIMULATION_END)
    if sorted(by_day)!=expected or any(by_day[d]['hru_days']!=len(areas) for d in by_day):
        raise ValueError(f'Incomplete SHAW daily diagnostics: {len(seen)} HRU days; expected {len(expected)*len(areas)}')
    result={}
    for name,(start,end) in periods.items():
        days=[by_day[d] for d in date_range(start,end)]
        rows=int(sum(d['hru_days'] for d in days))
        retries=int(sum(d['retried_hru_hours'] for d in days))
        result[name]={'start':str(start),'end':str(end),'days':len(days),'hru_days':rows,
            'canopy_air_exchange_reported':has_canopy_exchange,
            'max_absolute_hru_daily_residual_mm':max(d['max_abs_residual_mm'] for d in days),
            'coupled_area_cumulative_signed_residual_mm':sum(d['residual_mm'] for d in days),
            'coupled_area_sum_absolute_daily_residual_mm':sum(abs(d['residual_mm']) for d in days),
            'coupled_area_cumulative_absolute_hru_residual_mm':sum(d['mean_absolute_hru_residual_mm'] for d in days),
            'max_coupled_area_ice_water_mm':max(d['ice_mm'] for d in days),
            'coupled_area_storage_change_mm':sum(d['storage_change_mm'] for d in days),
            'coupled_area_flux_totals_mm':{field:sum(d[field] for d in days) for field in fluxes},
            'retried_hru_hours':retries,'total_hru_hours':rows*24,
            'jacobian_retry_hours':int(sum(d['jacobian_retry_hours'] for d in days)),
            'retried_hru_hours_percent':100*retries/(rows*24),
            'hru_days_requiring_retry':int(sum(d['hru_days_requiring_retry'] for d in days)),
            'max_hour_parts':int(max(d['max_hour_parts'] for d in days))}
    return result,by_day

def read_output(path):
    with path.open() as f:
        next(f);headers=next(f).split();next(f)
        # Basin writers omit the HRU-only plant/management text fields that
        # their shared water-balance and plant/weather headings still include.
        if path.name in ('basin_wb_day.txt','basin_pw_day.txt') and headers[-2:]==['plant_cov','mgt_ops']:
            headers=headers[:-2]
        rows=[]
        for line in f:
            fields=line.split()
            if not fields:continue
            if len(fields)!=len(headers):
                raise ValueError(f'Output/header column count mismatch in {path}: {len(fields)} versus {len(headers)}')
            row={}
            for name,value in zip(headers,fields):
                if name=='name':row[name]=value
                else:
                    number=float(value)
                    if not math.isfinite(number):raise ValueError(f'Nonfinite {path}: {line}')
                    row[name]=number
            row['date']=dt.date(int(row['yr']),int(row['mon']),int(row['day']))
            rows.append(row)
    return rows

def outlet_ids():
    result=[]
    for line in (DATA/'inputs/chandeg.con').read_text().splitlines()[2:]:
        f=line.split()
        if int(f[12])==0:result.append(int(f[0]))
    if not result:raise ValueError('No terminal channel in routing topology')
    return result

def seasonal_results(wb,flow):
    """Meteorological seasons; December belongs to the following winter year."""
    output=[]
    for mode in MODES:
        groups=defaultdict(list)
        for row in wb[mode]:
            d=row['date'];month=d.month
            season='DJF' if month in (12,1,2) else 'MAM' if month<=5 else 'JJA' if month<=8 else 'SON'
            groups[(d.year+int(month==12),season)].append(row)
        for (year,season),rows in sorted(groups.items(),key=lambda x:(x[0][0],('DJF','MAM','JJA','SON').index(x[0][1]))):
            start={'DJF':dt.date(year-1,12,1),'MAM':dt.date(year,3,1),'JJA':dt.date(year,6,1),'SON':dt.date(year,9,1)}[season]
            stop={'DJF':dt.date(year,3,1),'MAM':dt.date(year,6,1),'JJA':dt.date(year,9,1),'SON':dt.date(year,12,1)}[season]
            peak=max(rows,key=lambda r:flow[mode][r['date']])
            output.append({'model':mode,'season_year':year,'season':season,'days':len(rows),
                'complete_season':len(rows)==(stop-start).days,'period_start':str(rows[0]['date']),
                'period_end':str(rows[-1]['date']),
                **{field+'_mm':sum(r[field] for r in rows) for field in ('precip','et','surq_gen','latq','perc','snomlt')},
                'mean_outlet_m3s':sum(flow[mode][r['date']] for r in rows)/len(rows),
                'peak_outlet_m3s':flow[mode][peak['date']],'peak_date':str(peak['date']),
                'max_snowpack_mm':max(r['snopack'] for r in rows)})
    return output

def regression():
    count=0;files=0
    for path in (DATA/'official').glob('*.txt'):
        other=DATA/'coupling_off'/path.name
        if not other.exists():raise AssertionError(f'Off regression missing output: {path.name}')
        try:
            with path.open() as a,other.open() as b:
                lines_a=a.readlines();lines_b=b.readlines()
        except UnicodeError:continue
        # Run banner has a build date; all subsequent output must agree.
        if len(lines_a)!=len(lines_b):raise AssertionError(f'Off regression length: {path.name}')
        if lines_a[1:]!=lines_b[1:]:raise AssertionError(f'Off regression values: {path.name}')
        count+=max(0,len(lines_a)-3);files+=1
    if files<10:raise AssertionError('Insufficient off-regression outputs')
    return {'files_identical_after_banner':files,'data_rows':count}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    runs,errors=read_run_status()
    reg=None
    if all(runs.get(m,{}).get('exit_code')==0 for m in ('official','coupling_off')):
        reg=regression()
        (OUT/'regression.json').write_text(json.dumps(reg,indent=2)+'\n')
    status={'status':'incomplete' if errors else 'validating_outputs','errors':errors,'runs':runs}
    (OUT/'analysis_status.json').write_text(json.dumps(status,indent=2)+'\n')
    if errors:
        raise SystemExit('Three-model comparison withheld:\n'+'\n'.join(errors)+
                         '\nAny existing comparison artifacts describe an earlier run; inspect analysis_status.json.')
    forcing=check_forcing()
    transport=check_transport()
    outlets=outlet_ids()
    wb={m:read_output(DATA/m/'basin_wb_day.txt') for m in MODES}
    pw={m:read_output(DATA/m/'basin_pw_day.txt') for m in MODES}
    flow={m:defaultdict(float) for m in MODES}
    for mode in MODES:
        seen=set()
        for row in read_output(DATA/mode/'channel_sd_day.txt'):
            channel=int(row['unit'])
            if channel in outlets:
                key=(row['date'],channel)
                if key in seen:raise ValueError(f'Duplicate outlet daily output: {mode}: {key}')
                seen.add(key)
                flow[mode][row['date']]+=row['flo_out']
        if len(seen)!=len(outlets)*len(date_range(EVALUATION_START,SIMULATION_END)):
            raise ValueError(f'Incomplete outlet daily output: {mode}')
    dates=[r['date'] for r in wb['official']]
    expected=date_range(EVALUATION_START,SIMULATION_END)
    assert dates==expected
    for mode in MODES:
        assert [r['date'] for r in wb[mode]]==dates
        assert [r['date'] for r in pw[mode]]==dates
        assert sorted(flow[mode])==dates
        if any(a['precip']!=b['precip'] for a,b in zip(wb['official'],wb[mode])):
            raise ValueError(f'Basin precipitation differs despite identical raw input files: {mode}')
        for field in ('tmx','tmn','tmpav','solarad','wndspd','rhum'):
            if any(a[field]!=b[field] for a,b in zip(pw['official'],pw[mode])):
                raise ValueError(f'Basin weather differs: {mode}/{field}')
    # Validate the complete diagnostic record before publishing comparative metrics.
    scope,excluded=read_scope()
    areas={r['hru']:r['area_ha'] for r in scope}
    coupled_area=sum(r['area_ha'] for r in scope if r['coupled'])
    budgets,budget_days=water_budget(scope)
    with (OUT/'hru_scope.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(scope[0]));writer.writeheader();writer.writerows(scope)
    scope_groups={}
    for row in scope:
        key='SHAW coupled' if row['coupled'] else row['reason']
        group=scope_groups.setdefault(key,{'hrus':0,'area_ha':0.})
        group['hrus']+=1;group['area_ha']+=row['area_ha']
    annual=[]
    for mode in MODES:
        for year in (2021,2022,2023):
            rows=[r for r in wb[mode] if r['date'].year==year]
            q=[(r['date'],flow[mode][r['date']]) for r in rows]
            peak=max(q,key=lambda x:x[1])
            annual.append({'model':mode,'year':year,'days':len(rows),
                'period_start':str(rows[0]['date']),'period_end':str(rows[-1]['date']),
                'complete_calendar_year':len(rows)==(dt.date(year+1,1,1)-dt.date(year,1,1)).days,
                **{name+'_mm':sum(r[name] for r in rows) for name in
                   ('precip','snofall','snomlt','surq_gen','latq','wateryld','perc','et')},
                'max_snowpack_mm':max(r['snopack'] for r in rows),
                'mean_outlet_m3s':sum(x[1] for x in q)/len(q),'peak_outlet_m3s':peak[1],'peak_date':str(peak[0])})
    with (OUT/'annual_comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(annual[0]));writer.writeheader();writer.writerows(annual)
    daily=[]
    for i,date in enumerate(dates):
        row={'date':str(date)}
        row['air_temperature_C']=pw['official'][i]['tmpav']
        row['shaw_coupled_soil_ice_mm']=budget_days[date]['ice_mm']
        for mode in MODES:
            row[mode+'_outlet_m3s']=flow[mode][date]
            row[mode+'_soil_layer2_C']=pw[mode][i]['sol_tmp']
            for field in ('surq_gen','latq','perc','et','snopack','sw_final'):
                row[mode+'_'+field+'_mm']=wb[mode][i][field]
        daily.append(row)
    with (OUT/'daily_comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(daily[0]));writer.writeheader();writer.writerows(daily)
    seasonal=seasonal_results(wb,flow)
    with (OUT/'seasonal_comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(seasonal[0]));writer.writeheader();writer.writerows(seasonal)
    differences={}
    reference=np.array([flow['official'][d] for d in dates])
    for mode in MODES[1:]:
        q=np.array([flow[mode][d] for d in dates])
        differences[mode]={'outlet_daily_rmse_vs_official_m3s':float(np.sqrt(np.mean((q-reference)**2))),
            'outlet_mean_change_percent':float(100*(q.mean()/reference.mean()-1)) if reference.mean()!=0 else None}
    fig,axs=plt.subplots(4,1,figsize=(12,10),sharex=True,layout='constrained')
    labels={'official':'Official SWAT+','existing_ft':'Existing freeze-thaw','shaw':'SWAT+SHAW (experimental)'}
    for mode in MODES:
        axs[0].plot(dates,[flow[mode][d] for d in dates],lw=.85,label=labels[mode])
        for ax,field in zip(axs[1:],('snopack','et','perc')):
            ax.plot(dates,[r[field] for r in wb[mode]],lw=.85)
    for ax,label in zip(axs,('Outlet flow (m³/s)','Basin mean SWE (mm)','ET (mm/day)','Percolation (mm/day)')):
        ax.set_ylabel(label);ax.grid(alpha=.2)
    axs[0].legend(ncol=3,fontsize=9)
    fig.suptitle('Canadian case: identical forcing, uncalibrated process comparison\n2020 warm-up; no observed discharge supplied')
    fig.savefig(OUT/'process_comparison.png',dpi=180);fig.savefig(OUT/'process_comparison.pdf');plt.close(fig)
    fig,axs=plt.subplots(2,3,figsize=(14,6),sharey='row',layout='constrained')
    for col,year in enumerate((2021,2022,2023)):
        for mode in MODES:
            rows=[r for r in wb[mode] if r['date'].year==year and r['date'].month<=5]
            x=[r['date'] for r in rows]
            axs[0,col].plot(x,[flow[mode][d] for d in x],lw=1.,label=labels[mode])
            axs[1,col].plot(x,[r['snopack'] for r in rows],lw=1.)
        axs[0,col].set_title(str(year)+(' (through April)' if year==2023 else ''))
        for ax in axs[:,col]:
            ax.set_xlim(dt.date(year,1,1),dt.date(year,5,31))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            ax.grid(alpha=.2)
    axs[0,0].set_ylabel('Outlet flow (m³/s)');axs[1,0].set_ylabel('Basin mean SWE (mm)')
    axs[0,0].legend(fontsize=7)
    fig.suptitle('Winter–spring process comparison: January–May windows\nUncalibrated model results; no observed discharge supplied')
    fig.savefig(OUT/'winter_spring_comparison.png',dpi=180)
    fig.savefig(OUT/'winter_spring_comparison.pdf');plt.close(fig)
    fig,axs=plt.subplots(2,1,figsize=(12,6),sharex=True,layout='constrained')
    axs[0].plot(dates,[r['tmpav'] for r in pw['official']],color='.65',lw=.6,label='Daily mean air')
    for mode in MODES:
        axs[0].plot(dates,[r['sol_tmp'] for r in pw[mode]],lw=1.,label=labels[mode])
    axs[0].axhline(0,color='.25',ls='--',lw=.7)
    axs[0].set_ylabel('Basin mean layer-2 soil T (°C)');axs[0].legend(ncol=2,fontsize=8)
    axs[1].fill_between(dates,[budget_days[d]['ice_mm'] for d in dates],color='tab:blue',alpha=.65)
    axs[1].set_ylabel('Soil ice water equivalent (mm)')
    axs[1].set_title('SHAW soil ice only: mean over the 123 coupled HRUs',fontsize=10)
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle('Soil thermal response and SHAW ice storage\nModel diagnostics; no observed soil temperature or ice supplied')
    fig.savefig(OUT/'thermal_comparison.png',dpi=180)
    fig.savefig(OUT/'thermal_comparison.pdf');plt.close(fig)
    thermal={mode:{'mean_soil_layer2_C':float(np.mean([r['sol_tmp'] for r in pw[mode]])),
        'min_soil_layer2_C':min(r['sol_tmp'] for r in pw[mode]),
        'max_soil_layer2_C':max(r['sol_tmp'] for r in pw[mode]),
        'days_basin_mean_layer2_below_zero':sum(r['sol_tmp']<0 for r in pw[mode])} for mode in MODES}
    summary={'status':'complete','period':'2020-01-01 to 2023-04-30','simulation_days':len(date_range(SIMULATION_START,SIMULATION_END)),
             'evaluation_days':len(expected),'evaluation_period':f'{EVALUATION_START} to {SIMULATION_END}',
             'warmup':'2020','outlet_channel_ids':outlets,'total_area_ha':sum(areas.values()),
             'total_area_km2':sum(areas.values())/100,
             'coupled_area_ha':coupled_area,'coupled_hrus':sum(r['coupled'] for r in scope),
             'scope_groups':scope_groups,
             'total_hrus':len(scope),'regression':reg,'water_budget':budgets,'model_differences':differences,
             'soil_thermal_response':thermal,
             'forcing_parity':forcing,
             'transport_compatibility':transport,
             'excluded_zero_area_scope_rows':excluded,
             'units':{'outlet_flow':'m3/s; sum of terminal channel daily mean flows',
                      'annual_depths':'mm accumulated over the reported dates; 2023 is partial',
                      'daily_flux_depths':'mm per day; basin area means',
                      'daily_storage_depths':'mm; basin area means',
                      'soil_layer2_C':'area mean of SWAT soil(j)%phys(2)%tmp; not surface temperature or a uniform physical depth across HRUs',
                      'shaw_coupled_soil_ice_mm':'liquid-water equivalent of soil ice over the 123 coupled HRUs only; excludes snow',
                      'water_budget':'mm liquid-water equivalent over the positive-area coupled domain only',
                      'canopy_air_exchange_mm':'signed atmospheric water input caused by changes to canopy-air control volume',
                      'retry_hours':'count of HRU hours requiring subdivision or the additional conductance Jacobian; not elapsed wall-clock hours',
                      'jacobian_retry_hours':'count of accepted HRU hours using the additional conductance Jacobian after complete rollback',
                      'max_hour_parts':'largest accepted subdivision count for one HRU hour'},
             'interpretation':'Uncalibrated model differences, not observational skill scores; no discharge observations supplied.',
             'runs':runs}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    status['status']='complete'
    (OUT/'analysis_status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

"""Compare printed daily HRU weather, including generated radiation, humidity and wind."""
from pathlib import Path
from itertools import zip_longest
import csv
import datetime as dt
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]
MODES=('official','existing_ft','shaw')
FILES={'hru_pw_day.txt':('tmx','tmn','tmpav','solarad','wndspd','rhum'),
       'hru_wb_day.txt':('precip',)}


def weather_rows(path, fields):
    with path.open() as stream:
        next(stream);headers=next(stream).split();next(stream)
        indices={name:headers.index(name) for name in fields}
        for line in stream:
            if not line.strip():continue
            # Pinned hru_output formats: 4i6,2i8,2x,a16, then f12.3.
            # An unrelated overflowing nutrient field can join its neighbor
            # with asterisks; whitespace splitting would shift the weather.
            ids=[int(line[6*i:6*(i+1)]) for i in range(4)]
            key=(ids[3],ids[1],ids[2],int(line[24:32]))
            values=tuple(float(line[58+12*(indices[name]-7):58+12*(indices[name]-6)]) for name in fields)
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f'Nonfinite HRU weather: {path}/{key}')
            yield key,values


def check_forcing():
    data=ROOT/'validation/canada'
    runs={mode:json.loads((data/mode/'run.json').read_text()) for mode in MODES}
    if any(run.get('exit_code')!=0 or not run.get('completed_utc') for run in runs.values()):
        raise ValueError('Complete the three basin runs before comparing HRU weather')
    with (data/'shaw/shaw_hru_scope.csv').open() as stream:
        hrus={int(row['hru']) for row in csv.DictReader(stream) if float(row['area_ha'])>0}
    start=dt.date(2021,1,1)
    dates={start+dt.timedelta(days=i) for i in range(850)}
    expected={(d.year,d.month,d.day,hru) for d in dates for hru in hrus}
    checks={}
    for name,fields in FILES.items():
        seen=set()
        streams=[weather_rows(data/mode/name,fields) for mode in MODES]
        for rows in zip_longest(*streams):
            if any(row is None for row in rows):raise ValueError(f'Weather output length differs: {name}')
            if any(row!=rows[0] for row in rows[1:]):
                raise ValueError(f'HRU weather differs across models: {name}/{rows}')
            key=rows[0][0]
            if key in seen:raise ValueError(f'Duplicate HRU weather record: {name}/{key}')
            seen.add(key)
        if seen!=expected:raise ValueError(f'Incomplete HRU weather dates/scope: {name}')
        checks[name]={'fields':fields,'hru_daily_rows':len(seen),'different_values':0,
            'sha256':{mode:hashlib.sha256((data/mode/name).read_bytes()).hexdigest() for mode in MODES}}
    result={'status':'pass','evaluation_days':850,'hrus':len(hrus),'checks':checks,
        'coupled_executable_sha256':runs['shaw']['sha256'],
        'scope':'Exact printed HRU daily weather in the 850-day evaluation period. The 2020 warm-up is not printed; input file hashes cover the full simulation.'}
    (ROOT/'reports/canada/forcing_parity.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':print(json.dumps(check_forcing(),indent=2))

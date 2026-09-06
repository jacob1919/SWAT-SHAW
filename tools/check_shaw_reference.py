"""Compare physical states/fluxes against the test-only official SHAW solver."""
from pathlib import Path
import csv
import json
import math

ROOT=Path(__file__).resolve().parents[1]

def main():
    paths=[ROOT/'build/shaw_official/reference.csv',ROOT/'build/coupled/src/shaw/reference.csv']
    rows=[[[v for v in row if v.strip()] for row in csv.reader(p.open())] for p in paths]
    assert len(rows[0])==len(rows[1])==720
    maximum=0.;different=0;compared=0
    for a,b in zip(*rows):
        assert len(a)==len(b)
        for col,(x,y) in enumerate(zip(a,b)):
            if col==len(a)-2:continue # Added bridge retry counter, not a physical quantity.
            x=float(x);y=float(y)
            assert math.isfinite(x) and math.isfinite(y)
            error=abs(x-y)
            maximum=max(maximum,error);compared+=1
            different+=x!=y
            assert error<=2.e-6*max(1.,abs(x)), (a[0],col,x,y)
    result={'hours':720,'values_compared':compared,'different_values':different,'max_absolute_difference':maximum,
            'scope':'one canopy column; no solutes; original SAVE storage versus isolated extracted kernel; matched adapter inputs'}
    (ROOT/'build/shaw_reference_check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

if __name__=='__main__':main()

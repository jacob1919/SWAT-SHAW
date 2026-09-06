"""Prepare a test-only official SHAW solver, preserving its original SAVE and solute code.

Only symbols are namespaced, the standalone PROGRAM is omitted, and return-value
diagnostics are inserted. This reference is not linked into SWAT+ or distributed
as the water/heat port. It verifies the extraction/state refactoring separately.
"""
from pathlib import Path
import re
from extract_shaw import statements, emit, canopy_air_water_source

ROOT=Path(__file__).resolve().parents[1]

def main():
    lines=(ROOT/'vendor/shaw303/Shaw303.original.for').read_text(encoding='latin-1').splitlines(True)
    stmts=statements([line.rstrip('\r\n') for line in lines])
    names={'MATVLC','MATVL1','MATVL2','MATVL3'}
    for st in stmts:
        m=re.match(r'\s*SUBROUTINE\s+(\w+)',st['text'],re.I)
        if m:names.add(m[1].upper())
    start=next(st['start'] for st in stmts if re.match(r'\s*SUBROUTINE\s+GOSHAW\b',st['text'],re.I))
    insert={}
    def add_insert(index, text):
        insert[index] = insert.get(index, '') + text
    canopy_sites = 0
    exchange_initializations = 0
    in_goshaw=False
    for st in stmts:
        if re.match(r'\s*SUBROUTINE\s+GOSHAW\b',st['text'],re.I):in_goshaw=True
        if in_goshaw and re.match(r'\s*COMMON\s*/TIMEWT/',st['text'],re.I):
            add_insert(st['start'], emit('COMMON /SHP_RESULT/ SHP_RESULT_VALUES(320)')
                       +emit('REAL SHP_RESULT_VALUES')
                       +emit('REAL SHP_CANOPY_EXCHANGE, SHP_CANOPY_BEFORE, SHP_CANOPY_AIR_WATER')
                       +emit('EXTERNAL SHP_CANOPY_AIR_WATER'))
        if in_goshaw and re.match(r'\s*BCKSPACE\s*=\s*CHAR\(8\)',st['text'],re.I):
            add_insert(st['start'], emit('SHP_CANOPY_EXCHANGE=0.'))
            exchange_initializations += 1
        if in_goshaw and (re.search(r'\bCALL\s+CANOPY\b',st['text'],re.I)
                          or re.sub(r'\s+', '', st['text']).upper() == 'NC=0'):
            add_insert(st['start'], emit('SHP_CANOPY_BEFORE=SHP_CANOPY_AIR_WATER(NC,ZC,VAPCDT)'))
            add_insert(st['end'], emit('SHP_CANOPY_EXCHANGE=SHP_CANOPY_EXCHANGE+'
                                      '(SHP_CANOPY_AIR_WATER(NC,ZC,VAPCDT)-SHP_CANOPY_BEFORE)'))
            canopy_sites += 1
        if in_goshaw and re.match(r'\s*RETURN\s*$',st['text'],re.I):
            fields={1:'RUNOFF',2:'EVAP1',3:'ETSUM',4:'MELT',5:'RAIN',6:'TSEEP',7:'THFLUX',8:'TGFLUX',
                    9:'TSWDWN-TSWUP+TLWDWN-TLWUP',10:'REAL(MAXSTP)','21:20+NS':'TOTFLO(1:NS)',
                    '120:119+NS':'TOTLAT(1:NS)','219:218+NS':'ROOTXT(1:NS)',318:'SHP_CANOPY_EXCHANGE'}
            add_insert(st['start'], emit('SHP_RESULT_VALUES=0.')+''.join(emit(f'SHP_RESULT_VALUES({i})={v}') for i,v in fields.items()))
        if in_goshaw and re.match(r'\s*END\s*$',st['text'],re.I):in_goshaw=False
    assert canopy_sites == 5 and exchange_initializations == 1, (canopy_sites, exchange_initializations)
    output=[]
    for index,line in enumerate(lines[start:],start):
        if index in insert:output.append(insert[index])
        if line.strip() and line[0] not in 'cC*!':
            line=re.sub(r'\bCOMMON\s*/(\w+)/',lambda m:'COMMON /SHP_'+m[1].upper()+'/',line,flags=re.I)
            chunks=re.split(r"('(?:[^']|'')*'|\"(?:[^\"]|\"\")*\")",line)
            for k in range(0,len(chunks),2):
                chunks[k]=re.sub(r'\b\w+\b',lambda m:'SHP_'+m[0].upper() if m[0].upper() in names else m[0],chunks[k])
            line=''.join(chunks)
        output.append(line)
    output.append('\n'+canopy_air_water_source())
    target=ROOT/'build/shaw_reference_source'
    target.mkdir(parents=True,exist_ok=True)
    (target/'shaw_official_reference.for').write_text(''.join(output),encoding='ascii')
    print(target/'shaw_official_reference.for')

if __name__=='__main__':main()

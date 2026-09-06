"""Reproducibly extract the SHAW 3.0.3 water/heat kernel and isolate legacy state.

The numerical statements are retained in fixed form. Solute transport and all
standalone I/O drivers are excluded. Named COMMON and mutable SAVE storage are
snapshotted as 32-bit storage units, under a serial load/call/save contract.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import math

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {'SHAW303', 'IOFILES', 'INPUT', 'DAYINP', 'DAY2HR', 'SOLUTE', 'SALTK',
           'WBALNC', 'ENERGY', 'OUTPUT', 'SNOWTEMP', 'FROST', 'PESTOUTPUT'}
OUTPUT_CALLS = {'WBALNC', 'ENERGY', 'OUTPUT', 'SNOWTEMP', 'FROST'}
# DATA implies SAVE even without a SAVE statement. RAINSL changes PSAT while
# solving infiltration; capture both objects in its grouped DATA initializer.
IMPLICIT_SAVED_DATA = {'RAINSL': ['PSATK', 'PSAT']}

# Upstream canopy residuals integrate the full single-node/bottom control
# volume, but these four diagonal Jacobian terms use a shorter centered width.
# The optional correction changes only those derivatives, not the residuals.
# Keep the original statements in the OFF branch for pristine reference runs.
CANOPY_JACOBIAN_PATCHES = {
    ('EBCAN', 'B1(N)'): ('NC .EQ. 1', '(ZC(2)-ZC(1))/(2.*DT)', '(ZC(2)-ZC(1))/DT'),
    ('EBCAN', 'B1(I)'): ('J .EQ. NC', '(ZC(J+1)-ZC(J-1))/(2.*DT)',
                        '(ZC(J+1)-ZC(J)+(ZC(J)-ZC(J-1))/2.)/DT'),
    ('WBCAN', 'B2(N)'): ('NC .EQ. 1', '(ZC(2)-ZC(1))/2/DT', '(ZC(2)-ZC(1))/DT'),
    ('WBCAN', 'B2(I)'): ('J .EQ. NC', '(ZC(J+1)-ZC(J-1))/2/DT',
                        '(ZC(J+1)-ZC(J)+(ZC(J)-ZC(J-1))/2.)/DT'),
}

def split_list(text):
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif c == ',' and depth == 0:
            parts.append(text[start:i].strip()); start = i + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]

def statements(lines):
    result = []
    for index, line in enumerate(lines):
        if not line.strip() or line[0] in 'cC*!':
            continue
        line = line.ljust(6)
        code = line[6:].rstrip()
        # Existing inline comments occur outside literals in these sources.
        if '!' in code:
            code = code.split('!', 1)[0].rstrip()
        if line[5] not in ' 0':
            result[-1]['text'] += ' ' + code
            result[-1]['end'] = index + 1
        else:
            result.append({'start': index, 'end': index+1, 'label': line[:5].strip(), 'text': code})
    return result

def emit(text, label=''):
    # Split only at token boundaries, preserving literal strings.
    prefix = label.rjust(5) + ' '
    tokens = re.findall(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|[^'\"\s,]+,?|,", text)
    lines, current = [], prefix
    for token in tokens:
        if len(current) + len(token) + 1 > 120 and len(current) > 6:
            lines.append(current); current = '     >'
        current += (' ' if len(current) > 6 else '') + token
    lines.append(current)
    return '\n'.join(lines) + '\n'

def canopy_air_water_source():
    """Observation-only air-vapor storage, using the WBCAN residual volumes.

    Shared with the untouched-SAVE reference generator so diagnostic 318 has
    identical arithmetic. Vapor density is kg/m3; return m water equivalent.
    """
    code = [
        'REAL FUNCTION SHP_CANOPY_AIR_WATER(NC,ZC,VAPCDT)',
        'INTEGER NC,I', 'REAL ZC(11),VAPCDT(11),SHP_DZ',
        'SHP_CANOPY_AIR_WATER=0.',
        'DO I=1,NC',
        'IF (NC .EQ. 1) THEN', 'SHP_DZ=ZC(2)-ZC(1)',
        'ELSE IF (I .EQ. 1) THEN', 'SHP_DZ=(ZC(2)-ZC(1))/2.',
        'ELSE IF (I .EQ. NC) THEN', 'SHP_DZ=ZC(I+1)-ZC(I)+(ZC(I)-ZC(I-1))/2.',
        'ELSE', 'SHP_DZ=(ZC(I+1)-ZC(I-1))/2.', 'END IF',
        'SHP_CANOPY_AIR_WATER=SHP_CANOPY_AIR_WATER+SHP_DZ*VAPCDT(I)/1000.',
        'END DO', 'RETURN', 'END',
    ]
    return ('C     Observation-only canopy air storage; also used by the official reference fixture.\n'
            + ''.join(emit(line) for line in code))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    data = args.source.read_bytes()
    lines = data.decode('latin-1').splitlines()
    stmts = statements(lines)
    units, current = {}, None
    for st in stmts:
        match = re.match(r'\s*(PROGRAM|SUBROUTINE|BLOCK\s+DATA)\s*(\w+)?', st['text'], re.I)
        if match:
            name = (match[2] or 'CONSTANTS').upper()
            current = {'name': name, 'statements': [], 'kind': match[1].upper()}
            units[name] = current
        if current:
            current['statements'].append(st)
    selected = {k:v for k,v in units.items() if k not in EXCLUDE}
    common, saved, replacements, moved_data = {}, {}, {}, []
    symbols = {}
    for name, unit in selected.items():
        decls = {}
        for st in unit['statements']:
            m = re.match(r'\s*(REAL|INTEGER|LOGICAL|CHARACTER(?:\*\d+)?|DOUBLE PRECISION)\s+(.+)', st['text'], re.I)
            if m:
                for item in split_list(m[2].upper()):
                    match = re.fullmatch(r'(\w+)\s*(\([^)]*\))?', item)
                    if match:
                        decls[match[1]] = (m[1].upper(), match[2] or '')
        unit['decls'] = decls
        for st in unit['statements']:
            match = re.match(r'\s*COMMON\s*/(\w+)/\s*(.*)', st['text'], re.I)
            if match:
                block, fields = match[1].upper(), split_list(match[2].upper())
                entries = []
                for field in fields:
                    m = re.fullmatch(r'(\w+)\s*(\([^)]*\))?', field)
                    typ, dims = decls.get(m[1], ('INTEGER' if m[1][0] in 'IJKLMN' else 'REAL', ''))
                    dims = m[2] or dims
                    count = math.prod(int(v) for v in dims[1:-1].split(',')) if dims else 1
                    if typ == 'REAL': count *= 2  # binary64 REAL in 32-bit snapshot words.
                    assert typ in ('REAL','INTEGER','LOGICAL'), (block,field,typ)
                    entries.append((m[1], typ, dims, count))
                if block in common:
                    assert sum(e[3] for e in common[block]) == sum(e[3] for e in entries), block
                else:
                    common[block] = entries
            match = re.match(r'\s*SAVE\s+(.+)', st['text'], re.I)
            if match:
                fields = split_list(match[1].upper())
                block = 'SV_' + name
                entries = []
                for field in fields:
                    assert '/' not in field
                    typ, dims = decls.get(field, ('INTEGER' if field[0] in 'IJKLMN' else 'REAL', ''))
                    count = math.prod(int(v) for v in dims[1:-1].split(',')) if dims else 1
                    if typ == 'REAL': count *= 2
                    assert typ in ('REAL','INTEGER','LOGICAL'), (block,field,typ)
                    entries.append((field,typ,dims,count))
                common[block] = entries
                saved[name] = set(fields)
                replacements[st['start']] = emit('COMMON /SHP_' + block + '/ ' + ','.join(fields))
        if name in IMPLICIT_SAVED_DATA:
            assert name not in saved, 'Merge explicit and implicit SAVE lists before adding another routine'
            fields = IMPLICIT_SAVED_DATA[name]
            entries = []
            for field in fields:
                typ, dims = decls.get(field, ('INTEGER' if field[0] in 'IJKLMN' else 'REAL', ''))
                count = math.prod(int(v) for v in dims[1:-1].split(',')) if dims else 1
                if typ == 'REAL': count *= 2
                assert typ in ('REAL', 'INTEGER', 'LOGICAL'), (name, field, typ)
                entries.append((field, typ, dims, count))
            common['SV_' + name] = entries
            saved[name] = set(fields)
        # DATA for mutable saved scalars/arrays belongs in a BLOCK DATA unit.
        for st in unit['statements']:
            if re.match(r'\s*DATA\b', st['text'], re.I):
                groups = re.findall(r'([^/]+)/([^/]+)/', re.sub(r'^\s*DATA\s*','',st['text'],flags=re.I))
                targets = {v.strip().upper() for group,_ in groups for v in split_list(group)}
                if targets & saved.get(name,set()):
                    assert targets <= saved[name], (name,targets)
                    moved_data.append((name,st['text']))
                    replacements[st['start']] = 'C     Mutable SAVE initialization moved to SHP_SAVE_INITIAL_VALUES.\n'
    # New explicit kernel diagnostics use a common block to avoid changing the
    # upstream argument order. Arrays are returned in native SHAW SI units.
    common['RESULT'] = [('RESULT','REAL','(320)',640)]
    common['OPTIONS'] = [('CANOPY_WATER_TOL','REAL','',2), ('CANOPY_JACOBIAN','INTEGER','',1)]
    routines = set(selected) | {'MATVLC','MATVL1','MATVL2','MATVL3'}
    rename = {name: 'SHP_' + name for name in routines if name != 'CONSTANTS'}
    body = ['C     GENERATED by tools/extract_shaw.py; see vendor/shaw303/PROVENANCE.json.\n']
    source_map, jacobian_transforms, canopy_exchange_sites = [], [], []
    canopy_exchange_initializations = 0
    leaf_elimination_corrections = 0
    for name, unit in selected.items():
        source_map.append({'routine':name,'original_line':unit['statements'][0]['start']+1})
        body.append('C     USDA-ARS SHAW 3.0.3: '+name+'\n')
        skipping_solute = False
        for st in unit['statements']:
            text = st['text']
            if name == 'GOSHAW' and 'ABS(DELTA(N)/VAPCDT(I))' in text.upper():
                text = text.replace(' .GT. 0.01)', ' .GT. SHP_CANOPY_WATER_TOL)')
            if name == 'GOSHAW' and re.search(r'IF\s*\(NSALT\s*\.LE\.\s*0\)\s*GO TO 400',text,re.I):
                skipping_solute = True
            if skipping_solute:
                if st['label'] == '400':
                    skipping_solute = False
                else:
                    continue
            call = re.search(r'\bCALL\s+(\w+)',text,re.I)
            if call and call[1].upper() in OUTPUT_CALLS:
                body.append(emit('CONTINUE',st['label'])); continue
            # No interactive waits are permitted in an embedded model.
            if re.match(r'\s*READ\s*\(5',text,re.I):
                body.append(emit('CONTINUE',st['label'])); continue
            if re.match(r'\s*STOP\s*$',text,re.I):
                text = 'STOP 71'
            # The host owns Fortran unit numbers; send legacy diagnostics to stdout.
            text = re.sub(r'\bWRITE\s*\(21\s*,', 'WRITE (6,', text, flags=re.I)
            if name == 'GOSHAW' and re.match(r'\s*ITER\s*=\s*0\s*$',text,re.I) and 1200 < st['start'] < 1230:
                # Upstream sometimes continues with an unconverged solution.
                # Fail explicitly so basin comparisons cannot accept it silently.
                body.append(emit('SHP_RESULT_VALUES = 0.0'))
                body.append(emit('SHP_RESULT_VALUES(320) = -1.0'))
                body.append(emit('RETURN'))
            if st['start'] in replacements:
                body.append(replacements[st['start']]); continue
            text = re.sub(r'\bCOMMON\s*/(\w+)/',lambda m:'COMMON /SHP_'+m[1].upper()+'/',text,flags=re.I)
            # Rename identifiers outside string literals.
            chunks = re.split(r"('(?:[^']|'')*'|\"(?:[^\"]|\"\")*\")",text)
            for k in range(0,len(chunks),2):
                chunks[k] = re.sub(r'\b\w+\b',lambda m:rename.get(m[0].upper(),m[0]),chunks[k])
            text = ''.join(chunks)
            if name == 'GOSHAW' and re.match(r'\s*COMMON\s*/SHP_TIMEWT/',text,re.I):
                body.append(emit('COMMON /SHP_RESULT/ SHP_RESULT_VALUES(320)'))
                body.append(emit('REAL SHP_RESULT_VALUES'))
                body.append(emit('REAL SHP_CANOPY_EXCHANGE, SHP_CANOPY_BEFORE, SHP_CANOPY_AIR_WATER'))
                body.append(emit('EXTERNAL SHP_CANOPY_AIR_WATER'))
                body.append(emit('INTEGER SHP_FORCED_REFINEMENT'))
            if name == 'GOSHAW' and re.match(r'\s*BCKSPACE\s*=\s*CHAR\(8\)',text,re.I):
                # Reset once per GOSHAW call, before initialization or remapping.
                body.append(emit('SHP_CANOPY_EXCHANGE=0.'))
                canopy_exchange_initializations += 1
            if name in ('GOSHAW', 'EBCAN', 'WBCAN', 'LEAFT') and re.match(r'\s*COMMON\s*/SHP_TIMEWT/',text,re.I):
                body.append(emit('COMMON /SHP_OPTIONS/ SHP_CANOPY_WATER_TOL, SHP_CANOPY_JACOBIAN'))
                body.append(emit('REAL SHP_CANOPY_WATER_TOL'))
                body.append(emit('INTEGER SHP_CANOPY_JACOBIAN'))
            if name in IMPLICIT_SAVED_DATA and re.match(r'\s*COMMON\s*/SHP_TIMEWT/',text,re.I):
                body.append(emit('COMMON /SHP_SV_' + name + '/ ' + ','.join(IMPLICIT_SAVED_DATA[name])))
            if name == 'GOSHAW' and re.match(r'\s*RETURN\s*$',text,re.I):
                body += [emit('SHP_RESULT_VALUES = 0.0'), emit('SHP_RESULT_VALUES(1) = RUNOFF'),
                    emit('SHP_RESULT_VALUES(2) = EVAP1'),emit('SHP_RESULT_VALUES(3) = ETSUM'),
                    emit('SHP_RESULT_VALUES(4) = MELT'),emit('SHP_RESULT_VALUES(5) = RAIN'),
                    emit('SHP_RESULT_VALUES(6) = TSEEP'),emit('SHP_RESULT_VALUES(7) = THFLUX'),
                    emit('SHP_RESULT_VALUES(8) = TGFLUX'),
                    emit('SHP_RESULT_VALUES(9) = TSWDWN-TSWUP+TLWDWN-TLWUP'),
                    emit('SHP_RESULT_VALUES(10) = REAL(MAXSTP)'),
                    # SUMDT initializes only 1:NS. Never export uninitialized
                    # local array tails from a differently sized prior column.
                    emit('SHP_RESULT_VALUES(21:20+NS) = TOTFLO(1:NS)'),
                    emit('SHP_RESULT_VALUES(120:119+NS) = TOTLAT(1:NS)'),
                    emit('SHP_RESULT_VALUES(219:218+NS) = ROOTXT(1:NS)'),
                    emit('SHP_RESULT_VALUES(318) = SHP_CANOPY_EXCHANGE')]
            compact = re.sub(r'\s+', '', text).upper()
            if name == 'GOSHAW' and compact == 'ITER=0':
                body.append(emit(text,st['label']))
                body.append(emit('SHP_FORCED_REFINEMENT=0'))
                continue
            if name == 'GOSHAW' and compact == 'ITER=11':
                body.append(emit('SHP_FORCED_REFINEMENT=1',st['label']))
                body.append(emit(text))
                continue
            if name == 'GOSHAW' and compact == 'IF(ITER.LE.10)GOTO200':
                # Large-increment guards still force native time refinement.
                # Otherwise finish the nonlinear iteration before subdividing;
                # repeated subdivision is not a substitute for enough iterations.
                body.append(emit(text,st['label']))
                body.append(emit('IF (SHP_CANOPY_JACOBIAN .NE. 0 .AND. SHP_FORCED_REFINEMENT .EQ. 0 .AND. ITER .LT. 40) GO TO 200'))
                continue
            if name == 'LEAFT' and compact == 'F1(I)=F1(I)-(DF1DT(I)/DF2DT(I))*F1(I)':
                # Eliminating leaf temperature from the water equation must
                # subtract the temperature coefficient times the ENERGY residual.
                # The upstream RHS multiplies F1 twice; it is dimensionally
                # inconsistent and prevents the leaf Newton solve from converging.
                body.append('C     Optional correction to leaf Newton elimination RHS (F2 is the energy residual).\n')
                body.append(emit('IF (SHP_CANOPY_JACOBIAN .NE. 0) THEN',st['label']))
                body.append(emit('F1(I)=F1(I)-(DF1DT(I)/DF2DT(I))*F2(I)'))
                body.append(emit('ELSE'))
                body.append(emit(text))
                body.append(emit('END IF'))
                leaf_elimination_corrections += 1
                continue
            if name == 'GOSHAW' and ((call and call[1].upper() == 'CANOPY') or compact == 'NC=0'):
                # Observe initialization, growth/remapping, snow-driven changes,
                # and complete removal without changing canopy physics.
                body.append(emit('SHP_CANOPY_BEFORE=SHP_CANOPY_AIR_WATER(NC,ZC,VAPCDT)'))
                body.append(emit(text,st['label']))
                body.append(emit('SHP_CANOPY_EXCHANGE=SHP_CANOPY_EXCHANGE+'
                                 '(SHP_CANOPY_AIR_WATER(NC,ZC,VAPCDT)-SHP_CANOPY_BEFORE)'))
                canopy_exchange_sites.append({'original_line':st['start']+1,
                                               'kind':'remove' if compact == 'NC=0' else 'call'})
                continue
            lhs = compact.split('=', 1)[0]
            patch_key = (name, lhs)
            if (patch_key in CANOPY_JACOBIAN_PATCHES and
                    CANOPY_JACOBIAN_PATCHES[patch_key][1] in compact):
                condition, old_width, new_width = CANOPY_JACOBIAN_PATCHES[patch_key]
                assert compact.count(old_width) == 1, (patch_key, compact)
                corrected = compact.replace(old_width, new_width)
                body.append('C     Optional canopy storage Jacobian correction; residual volume is unchanged.\n')
                body.append(emit('IF (SHP_CANOPY_JACOBIAN .NE. 0 .AND. ' + condition + ') THEN', st['label']))
                body.append(emit(corrected))
                body.append(emit('ELSE'))
                body.append(emit(text))
                body.append(emit('END IF'))
                jacobian_transforms.append({'routine':name, 'original_line':st['start']+1,
                    'condition':condition, 'original_statement':st['text'].strip(),
                    'corrected_statement':corrected})
                continue
            body.append(emit(text,st['label']))
    assert len(jacobian_transforms) == len(CANOPY_JACOBIAN_PATCHES), jacobian_transforms
    assert canopy_exchange_initializations == 1, canopy_exchange_initializations
    assert leaf_elimination_corrections == 1, leaf_elimination_corrections
    assert len(canopy_exchange_sites) == 5, canopy_exchange_sites
    body.append(canopy_air_water_source())
    if moved_data:
        body.append(emit('BLOCK DATA SHP_SAVE_INITIAL_VALUES'))
        body.append(emit('REAL SHP_CANOPY_WATER_TOL'))
        body.append(emit('INTEGER SHP_CANOPY_JACOBIAN'))
        body.append(emit('COMMON /SHP_OPTIONS/ SHP_CANOPY_WATER_TOL, SHP_CANOPY_JACOBIAN'))
        body.append(emit('DATA SHP_CANOPY_WATER_TOL /0.01/ SHP_CANOPY_JACOBIAN /0/'))
        for name in sorted({n for n,_ in moved_data}):
            entries = common['SV_'+name]
            for field,typ,dims,count in entries:
                body.append(emit(typ+' '+name+'_'+field+dims))
            body.append(emit('COMMON /SHP_SV_'+name+'/ '+','.join(name+'_'+e[0] for e in entries)))
            for n,d in moved_data:
                if n==name:
                    body.append(emit(re.sub(r'\b\w+\b',lambda m:name+'_'+m[0] if m[0].upper() in saved[name] else m[0],d)))
        body.append(emit('END'))
    offsets, cursor = {}, 0
    for block, entries in common.items():
        count = sum(e[3] for e in entries)
        offsets[block] = {'offset':cursor,'count':count,'fields':entries}
        cursor += count
    state = ['! Generated serial COMMON/SAVE context. No concurrent SHAW calls.\n',
             'module shaw_legacy_state\n  use iso_fortran_env, only: int32\n  implicit none\n',
             f'  integer, parameter :: shaw_state_words = {cursor}\n',
             '  type :: shaw_snapshot\n    integer(int32) :: words(shaw_state_words) = 0\n  end type\ncontains\n']
    for action in ['load','save']:
        state.append('  subroutine shaw_'+action+'_state(state)\n    type(shaw_snapshot), intent('+('in' if action=='load' else 'out')+') :: state\n')
        for block,info in offsets.items():
            state.append(f'    integer(int32) :: raw_{block.lower()}({info["count"]})\n    common /SHP_{block}/ raw_{block.lower()}\n    save /SHP_{block}/\n')
        for block,info in offsets.items():
            mem=f'state%words({info["offset"]+1}:{info["offset"]+info["count"]})'
            raw='raw_'+block.lower()
            state.append('    '+(raw+' = '+mem if action=='load' else mem+' = '+raw)+'\n')
        state.append('  end subroutine\n')
    state.append('end module shaw_legacy_state\n')
    out = ROOT/'src'/'shaw'
    out.mkdir(parents=True,exist_ok=True)
    (out/'shaw_water_heat.for').write_text(''.join(body),encoding='ascii')
    (out/'shaw_legacy_state.f90').write_text(''.join(state),encoding='ascii')
    access = ['! Generated typed access to the same serial legacy storage.\nmodule shaw_common_access\n  implicit none\n']
    for block,entries in common.items():
        access_names=[]
        for field,typ,dims,count in entries:
            access_name=block.lower()+'_'+field.lower()
            access_names.append(access_name)
            access.append('  '+typ.lower()+' :: '+access_name+dims+'\n')
        access.append('  common /SHP_'+block+'/ &\n    '+', &\n    '.join(access_names)+'\n  save /SHP_'+block+'/\n')
    access.append('end module shaw_common_access\n')
    (out/'shaw_common_access.f90').write_text(''.join(access))
    gos=selected['GOSHAW']
    argtext=gos['statements'][0]['text']
    argnames=split_list(argtext[argtext.index('(')+1:argtext.rindex(')')].upper())
    types=['! Generated typed SHAW driver state; dimensions follow official GOSHAW.\n',
           'module shaw_column_types\n  use shaw_legacy_state\n  implicit none\n  type :: shaw_column\n',
           '    type(shaw_snapshot) :: memory\n    real :: flux(320) = 0.\n']
    for arg in argnames:
        typ,dims=gos['decls'].get(arg,('INTEGER' if arg[0] in 'IJKLMN' else 'REAL',''))
        types.append('    '+typ.lower()+' :: '+arg.lower()+dims+' = 0\n')
    types.append('  end type\ncontains\n  subroutine shaw_call(c)\n    use shaw_common_access, only: result_result\n    type(shaw_column), intent(inout) :: c\n    call shaw_load_state(c%memory)\n    call SHP_GOSHAW( &\n')
    types.append(', &\n'.join('      c%'+arg.lower() for arg in argnames)+')\n')
    types.append('    c%flux = result_result\n    c%inital = 1\n    call shaw_save_state(c%memory)\n  end subroutine\nend module shaw_column_types\n')
    (out/'shaw_column_types.f90').write_text(''.join(types))
    vendor=ROOT/'vendor'/'shaw303'
    vendor.mkdir(parents=True,exist_ok=True)
    # Retain the official file only as an unmodified provenance/reference fixture.
    (vendor/'Shaw303.original.for').write_bytes(data)
    manifest={'official_source':'https://www.ars.usda.gov/pacific-west-area/boise-id/northwest-watershed-research-center/docs/shaw-model/',
              'source_sha256':hashlib.sha256(data).hexdigest(),'excluded_routines':sorted(EXCLUDE),
              'included_routines':source_map,'common_storage':offsets,'state_words':cursor,
              'implicit_saved_data':IMPLICIT_SAVED_DATA,
              'diagnostic_array_contract':'Zero-pad all outputs; copy only initialized TOTFLO/TOTLAT/ROOTXT(1:NS).',
              'canopy_air_exchange':{'result_index':318, 'units':'m water equivalent',
                  'sign':'Positive adds canopy air-vapor storage; negative removes it.',
                  'original_sites':canopy_exchange_sites,
                  'method':'Sum air-vapor storage after minus before each CANOPY call and explicit NC=0 using WBCAN residual control-volume widths; observation only.'},
              'optional_canopy_jacobian':{'option':'options_canopy_jacobian', 'default':0,
                  'meaning':'Nonzero uses the same single-node/bottom canopy storage widths in diagonal Jacobians and residuals.',
                  'transforms':jacobian_transforms},
              'optional_leaf_elimination':{'option':'options_canopy_jacobian','original_line':6494,
                  'original':'F1(I)=F1(I)-(DF1DT(I)/DF2DT(I))*F1(I)',
                  'corrected':'F1(I)=F1(I)-(DF1DT(I)/DF2DT(I))*F2(I)'},
              'optional_iteration_extension':{'option':'options_canopy_jacobian',
                  'max_iterations_without_forced_refinement':40,'convergence_criteria':'unchanged; native large-increment guards still force time refinement'},
              'contract':'64-bit default REAL, 32-bit INTEGER/LOGICAL; packed COMMON; serial load/call/save; no solute or CO2 simulation'}
    (vendor/'PROVENANCE.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Extracted {len(selected)} units, {len(common)} COMMON/SAVE blocks, {cursor*4} bytes/context')

if __name__=='__main__': main()

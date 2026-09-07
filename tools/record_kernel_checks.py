"""Record observed SHAW fixture results and their executable/source provenance."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    log_path=ROOT/'build/coupled/Testing/Temporary/LastTest.log'
    log=log_path.read_text()
    assert log.count('Test Passed.')==4 and 'Test Failed.' not in log
    assert 'PASS: conservative nonnegative root supply' in log
    column=float(re.search(r'max hourly residual\s+mm=\s*([\d.E+-]+)',log).group(1))
    canopy=float(re.search(r'max hourly water residual mm=\s*([\d.E+-]+)',log).group(1))
    derivative=float(re.search(r'maximum scaled difference=\s*([\d.E+-]+)',log).group(1))
    assert max(column,canopy)<=.002 and derivative<=1.e-5
    off=json.loads((ROOT/'validation/canada/coupling_off/run.json').read_text())
    assert off['exit_code']==0 and digest(Path(off['executable']))==off['sha256']
    for name,expected in off['source_sha256'].items():assert digest(ROOT/name)==expected,name
    reference=json.loads((ROOT/'build/shaw_reference_check.json').read_text())
    assert reference['different_values']==0 and reference['hours']==720
    fixture_names=('test_shaw_columns','test_shaw_canopy','test_shaw_conductance','test_shaw_roots','ported_shaw_reference')
    result={'coupled_executable_sha256':off['sha256'],'source_sha256':off['source_sha256'],
        'ctest_log_sha256':digest(log_path),'shaw_tests_passed':4,
        'fixture_executable_sha256':{name:digest(ROOT/f'build/coupled/src/shaw/{name}.exe') for name in fixture_names},
        'persistent_state':{'blocks':34,'bytes':82800,'real_bits':64,'integer_bits':32},
        'shaw_column_test':{'hours':240,'max_abs_hourly_residual_mm':column},
        'shaw_canopy_test':{'hours':288,'max_abs_hourly_residual_mm':canopy},
        'shaw_conductance_test':{'max_scaled_derivative_difference':derivative,'acceptance_limit':1.e-5},
        'shaw_root_test':{'status':'pass','cases':['dry-layer counterexample','node ordering','fully active roots',
            'zero demand','root-free wet layer','small hydraulic flux'],
            'bridge_hourly_uptake_transpiration_gate_mm':1.e-6},
        'official_reference':reference,
        'corrected_path':{'soil_tolerance':1.e-4,'canopy_relative_vapor_tolerance':1.e-3,
            'canopy_storage_jacobian_correction':True,'leaf_F2_elimination_correction':True,
            'max_iterations_without_forced_refinement':40,'conductance_derivative_retry':True,
            'consistent_root_active_set':True,'maximum_external_hour_parts':64}}
    target=ROOT/'reports/canada/kernel_checks.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(f'Recorded four SHAW fixtures and original-reference parity for {off["sha256"]}')


if __name__=='__main__':main()

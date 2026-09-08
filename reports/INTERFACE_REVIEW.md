# Interface corrections after 4aac926

The historical report in reports/canada remains a pre-correction research baseline. These changes address the interface review; they do not establish observational accuracy or energy closure.

## Implemented interface policy

- Radiation: hydraulic slope and solar-incidence slope are separate. An optional shaw_aspect.csv supplies columns hru,aspect_degrees, clockwise from north in [0,360]. Without an aspect, the default uses horizontal radiation and retains actual hydraulic slope. No aspect was recovered for the Canadian case. The new radiation option is stored independently for each HRU.
- Forcing: the default common SHAW reference height is fixed per HRU at max(10 m, maximum canopy height of its initialized plant community + 2 m). Wind is converted from an explicit 10 m source reference using the existing SWAT 0.2 power approximation. Vegetation updates cannot change the measurement height. A canopy reaching the reference height stops with a diagnostic. Temperature and RH are assumed vertically uniform because source heights are not carried in these weather inputs. This is still an above-canopy forcing approximation, especially for forests.
- Snow: the extra daily field snow_liquid_release_mm reports native SHAW MELT. The legacy SWAT snomlt field on coupled HRUs retains the same numerical value for compatibility. Both may include rain through snow and are explicitly documented in each run's shaw_output_semantics.txt. No pure phase-change melt diagnostic is claimed.
- AWC: the official CanSIS record establishes four exact layer matches supporting conversion from percent to fraction. See [the provenance audit](canada_awc/REPORT.md). Revised runs share an isolated, corrected input set; historical inputs remain intact.
- Thermal boundary: the fixed-temperature baseline remains available. The independent estimated option uses native SHAW ITMPBC=1 with annual mean temperature as TSAVG, without extending the water profile. This is not a 4 m deep-boundary experiment.
- Rainfall: explicit duration/start-hour options preserve each daily total while testing synthetic hourly distributions.

Each run writes shaw_configuration.csv with geometry, forcing reference heights, bottom depth/temperature and rainfall timing.

## Reproducible controls

| Environment variable | Default | Alternatives / meaning |
|---|---|---|
| SWAT_SHAW_RADIATION | aspect_or_horizontal | horizontal; legacy_north reproduces the reviewed geometry assumption |
| SWAT_SHAW_FORCING | fixed | legacy reproduces dynamic canopy+2 m height and unconverted wind |
| SWAT_SHAW_WIND_HEIGHT | 10 | Positive source wind height in metres |
| SWAT_SHAW_FORCING_HEIGHT | automatic | Positive fixed reference height override in metres |
| SWAT_SHAW_THERMAL | fixed | estimated selects native estimated bottom temperature |
| SWAT_SHAW_RAIN_HOURS | 24 | Integer 1..24, synthetic rainfall duration |
| SWAT_SHAW_RAIN_START | 1 | Integer 1..24; active hours wrap within the day |

Legacy controls are for attribution, not the recommended physical setup. They preserve a way to separate interface corrections from the AWC change.

Run independent cases with tools/run_interface_case.py. It refuses to overwrite an existing case and records input hashes, executable hash, coupled source hashes and explicit switches. All post-review cases live under validation/canada/interface_review. Use tools/audit_canada_awc.py --prepare first.

## Validation status

The rebuilt code passes all eight SHAW CTests: original column isolation, dynamic canopy, conductance derivatives and root supply, plus new radiation/height behavior and three invalid-input rejection cases. The original-algorithm fixture was rebuilt and rerun: 720 hours and 282,960 compared values are identical. Its original algorithm settings do not validate the corrected basin physics.

Post-review three-model basin simulations and all seven HRU 1 attribution cases are complete; see [the report](interface_cases/REPORT.md). The old 4aac926 executable is preserved under build/pre_review_4aac926 with SHA256 64a9a05974e0bfe950779d70217b996a1fd41101b8f62131a8e71a9532a8fb56. The new per-HRU snapshot includes an additional 8-byte radiation option (82,808 bytes of COMMON/SAVE storage); old binary column dumps must not be replayed with this new layout.

Still required: controlled deeper thermal-boundary experiments and observational rainfall timing, energy ledgers including externally supplied water, grid/time convergence, and independent observations of snow, soil temperature and streamflow. A small water residual alone is insufficient for those conclusions.

Primary interface reference: [SHAW 3.0 user manual](https://www.ars.usda.gov/ARSUserFiles/20520500/SHAW/ShawUsers.30x.pdf), site characteristics and lower boundary conditions.

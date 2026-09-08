# Canadian AWC provenance audit

The four AWC inputs in the historical Canadian case require a percent-to-fraction conversion. This conclusion is supported by an exact soil identifier and four matching layers, rather than by the magnitude of AWC alone.

The case uses QCBLF33000A (BLANDFORD). The [Canadian government soil record](https://sis.agr.gc.ca/cansis/soils/qc/BLF/33000/A/description.html) matches all four layer depths, bulk densities, hydraulic conductivities, organic carbon, clay, silt, sand and coarse-fragment values after the documented cm-to-mm conversions. Its retention values give:

| Layer bottom (mm) | KP33 (%) | KP1500 (%) | Difference in source units | Original SWAT AWC | Corrected AWC (mm/mm) |
|---:|---:|---:|---:|---:|---:|
| 180 | 24 | 9 | 15 | 15 | 0.15 |
| 240 | 23 | 9 | 14 | 14 | 0.14 |
| 300 | 22 | 8 | 14 | 14 | 0.14 |
| 1000 | 19 | 11 | 8 | 8 | 0.08 |

[KP33](https://sis.agr.gc.ca/cansis/nsdb/soil/v2/slt/kp33.html) and [KP1500](https://sis.agr.gc.ca/cansis/nsdb/soil/v2/slt/kp1500.html) are volume percentages. [SWAT AWC](https://swatplus.gitbook.io/io-docs/introduction-1/soils/soils.sol/awc) is field capacity minus wilting point as a fraction. The original export script was not recovered, so the precise point where conversion was omitted remains an inference; the required unit conversion is strongly evidenced.

## Consequence for initialized properties

An analytical reproduction of the pinned SWAT initialization and SHAW retention mapping gives the following results. These are calculations from the input, not a new runtime state dump.

| Layer | Original fallback | Original Campbell b | Corrected Campbell b | Original air entry (m) | Corrected air entry (m) |
|---:|:---:|---:|---:|---:|---:|
| 1 | Yes | 3.47575 | 3.41377 | -1.23619 | -0.19962 |
| 2 | Yes | 3.47575 | 3.64371 | -1.23619 | -0.16802 |
| 3 | Yes | 3.47575 | 3.15313 | -1.23619 | -0.19659 |
| 4 | Yes | 3.47575 | 5.82615 | -1.23619 | -0.07341 |

The initialized available water capacity of the 1 m profile changes from 187.54717 to 99.8 mm. All corrected layers avoid the porosity fallback. SWAT still estimates wilting point from clay and bulk density, so the corrected initialization does not exactly reproduce both CanSIS retention endpoints. Applying those endpoints directly would be a separate parameterization change.

## Reproducibility and limits

Run python -S tools/audit_canada_awc.py --prepare from the repository. It verifies every non-AWC match, checks the historical input hashes, and changes only the four AWC tokens in an isolated copy at validation/canada/interface_review/inputs_awc_corrected. The original archive, baseline inputs and historical three-model outputs are preserved. The revised inputs must be shared by all three models in any new comparison.

Evidence and calculated properties are recorded in cansis_source.json and audit.json. The original soil input SHA256 is cdad1d53bde3eca61b8c3b215b7dac88eacf4b406f415df9b765a67bc054ea75; the corrected SHA256 is a2b1190eb70e5ec3be2ac83d524bf717ed7bd1cd57c533e40d7d7240794c0136.

The [CanSIS layer-table documentation](https://sis.agr.gc.ca/cansis/nsdb/soil/v2/slt/index.html) describes modal attributes, many estimated. They are not a measured local pedon. Resolving this unit error therefore improves input consistency but does not establish site representativeness or observational accuracy.

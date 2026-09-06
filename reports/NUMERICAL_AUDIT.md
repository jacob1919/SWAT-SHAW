# SHAW numerical and state audit

The coupled kernel is derived from the unmodified USDA-ARS SHAW 3.0.3 source in `vendor/shaw303/Shaw303.original.for`. The extraction manifest records the SHA256, original routine locations, and transformed statements. The scientific equations and the adaptations below must be distinguished when reporting results.

## Persistent state and diagnostics

All named COMMON blocks, explicit SAVE objects, and the mutable DATA-initialized RAINSL `PSAT` array are saved separately for each HRU. DATA implies persistent storage even without SAVE; `PSATK` is included with `PSAT` to preserve their grouped initializer. A snapshot currently contains 82,160 bytes across 33 blocks. The adapter checks its REAL64/INTEGER32 storage contract at initialization; the compiler is instructed to leave COMMON blocks unpadded. Calls remain serial.

The upstream `SUMDT` initializes only entries 1:NS of its local flux arrays. Exported arrays are therefore zero-padded outside 1:NS. Uninitialized tails are neither physical output nor valid evidence of execution-order dependence.

## Optional canopy Jacobian correction

For a canopy vapor residual containing `-(v_new-v_old)*dz/dt`, the corresponding diagonal storage derivative is `-dz/dt`. The original WBCAN diagonal uses a different width from its own residual when there is one canopy node or at the lowest node of a multilayer canopy. EBCAN has the analogous discrepancy, multiplied by air density and heat capacity.

| Node | Original diagonal width | Residual width used by the correction |
|---|---|---|
| NC = 1 | `(z2-z1)/2` | `z2-z1` |
| Bottom node, NC > 1 | `(z(NC+1)-z(NC-1))/2` | `z(NC+1)-z(NC)+(z(NC)-z(NC-1))/2` |

The guarded correction changes these four derivatives, leaving the balance residuals intact. `options_canopy_jacobian=0` preserves the original numerical statements; the SWAT bridge explicitly enables the correction. Shorter steps increase the importance of the storage term, so an inconsistent derivative can undermine convergence during time refinement. These are engineering changes in this fork, not an upstream USDA release.

The same option corrects a second algebraic error in original LEAFT line 6494. Eliminating leaf temperature from Newton row 1 requires `F1 -= (DF1DT/DF2DT)*F2`. The original multiplies by F1 a second time, although F2 is the energy residual belonging to the eliminated row. The neighboring coefficient elimination and subsequent temperature back-substitution confirm the required F2 term.

The corrected solver permits up to 40 outer iterations instead of the original 11. Original large-increment guards still force immediate time refinement; otherwise the nonlinear iteration can finish before the model subdivides time. Convergence criteria remain unchanged. Full-hour rollback and subdivision still reject unsuccessful attempts. A captured Canadian HRU 98 hour (2020 day 197, hour 20) then passed at soil and canopy tolerances of `1e-4`, without external hour subdivision, and a water residual of about `0.000211 mm`. Before iteration extension it still failed after 64 subdivisions. The isolated HRU's first 148 days had been checked equal to its full-basin run, so the diagnostic reproduced an actual basin failure.

An intermediate strategy allowed the extra iterations only at the smallest native step. Both strategies completed all 1,216 days for HRU 98. The final strategy reduced this isolated basin-run wall time from 94.922 to 59.844 seconds on this host. Relative to the intermediate strategy, accumulated ET changed by approximately +0.11%, runoff +0.70%, and percolation -0.36%; results are in `canada/iteration_sensitivity_hru98.json`. This is a limited solver-strategy sensitivity check, not a formal grid/time convergence study or a whole-basin performance claim.

## Moving canopy air volume

The canopy initializer and geometry update create, remove, and redistribute atmospheric vapor as plants grow or snow covers them. The adapter measures signed vapor storage change immediately around every canopy geometry call, including complete removal, using the same control volumes as the residual. Diagnostic flux 318 records this exchange in metres of water equivalent. It is an atmospheric control-volume exchange, reported separately from precipitation and physical evaporation. The daily water ledger subtracts this signed input. Leaf removal transfers intercepted liquid to surface pond storage.

## Verified fixtures

- Original-algorithm path: 720 hours, 282,960 reported values exactly equal to an independently compiled reference retaining the original SAVE storage and solute routines, with zero solutes and the same adapter inputs. Both copies include the same observation-only diagnostics. The corrected algorithm is not asserted to reproduce the original trajectory exactly.
- Corrected path: two different soil-node counts and canopies, 240 hours each, independently and interleaved. Temperatures, liquid, ice and returned flux arrays agree exactly. Maximum hourly residual in the budgeted column: `9.75569e-5 mm`.
- Corrected dynamic canopy: 288 hours, bare/single/multiple canopy nodes, height changes, wet-canopy leaf removal, snow and freeze/thaw. Maximum hourly residual: `1.46265e-4 mm`.
- Both conservation fixtures retain their `0.002 mm/hour` acceptance limit. An unconverged hourly attempt is rejected and its full state restored before shorter-step retries. The basin gate remains `0.1 mm/HRU/day`; cumulative residuals must also be reported.
- Fresh official SWAT+ comparison: the coupling-off Ames outputs match all 42 selected files after the build banner. The repository's historical golden outputs differ even for the pinned official executable; those files have not been overwritten.

These checks establish the tested numerical properties only. Energy-budget closure, temporal and spatial convergence, plant hydraulic calibration, and validation against field observations remain separate research requirements.

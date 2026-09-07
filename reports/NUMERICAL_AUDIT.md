# SHAW numerical and state audit

The coupled kernel is derived from the unmodified USDA-ARS SHAW 3.0.3 source in `vendor/shaw303/Shaw303.original.for`. The extraction manifest records the SHA256, original routine locations, and transformed statements. The scientific equations and the adaptations below must be distinguished when reporting results.

## Persistent state and diagnostics

All named COMMON blocks, explicit SAVE objects, and the mutable DATA-initialized RAINSL `PSAT` array are saved separately for each HRU. DATA implies persistent storage even without SAVE; `PSATK` is included with `PSAT` to preserve their grouped initializer. A snapshot currently contains 82,800 bytes across 34 blocks. The adapter checks its REAL64/INTEGER32 storage contract at initialization; the compiler is instructed to leave COMMON blocks unpadded. Calls remain serial.

The COMMON parser accepts whitespace inside block delimiters, including the upstream `COMMON / CANLWR/` spelling. Both declarations of `CANLWR` are renamed and its 80 REAL64 values are now captured. The extractor rejects unmatched COMMON declarations instead of silently omitting them. The former 33-block layout missed this block; `LWRBAL` rewrites it before its normal use, but complete state ownership must not depend on that call ordering. Binary diagnostic dumps are compiler/layout specific and must be regenerated when the state layout changes.

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

An intermediate strategy allowed the extra iterations only at the smallest native step. Both strategies completed all 1,216 days for HRU 98. Allowing extra iterations before forced subdivision reduced this isolated basin-run wall time from 94.922 to 59.844 seconds on this host. Relative to the intermediate strategy, accumulated ET changed by approximately +0.11%, runoff +0.70%, and percolation -0.36%; results are in `canada/iteration_sensitivity_hru98.json`. This historical study predates the conductance and root corrections below. It is a limited solver-strategy sensitivity check, not a formal grid/time convergence study or a whole-basin performance claim.

The bridge retains soil tolerance `1e-4` and selects canopy relative-vapor tolerance `1e-3` (ten times stricter than the official `0.01`). A further complete HRU 98 test compared canopy tolerances `1e-4` and `1e-3`: cumulative ET changed +0.0023%, runoff +0.0118%, and percolation -0.0012%. The largest daily top-soil-temperature difference was 0.114 °C. At that checkpoint the selected run's cumulative signed water residual was -0.252 mm and maximum absolute daily residual 0.0959 mm, with the original 0.1 mm daily gate retained. Wall time was 42.765 seconds. Detailed values are in `canada/tolerance_sensitivity_hru98.json`. This historical tolerance study predates the following fixes and does not establish field accuracy; current isolated-column results are recorded separately.

## Conductance derivative and rollback strategy

Canadian HRU 6 failed during a sparse-canopy, low-humidity period (2021 day 135). Native `CANTK` depends strongly on the Richardson number when the canopy wind difference is small. Holding this conductance fixed in the energy Jacobian can produce oscillations even after time subdivision. `shaw_canopy_jacobian.f90` differentiates the original constitutive law at fixed wind and geometry, without changing its flux or stability caps:

- `Ri = g * dz * (T_top - T_bottom) / ((T_top + 273.16) * delta_wind**2)`.
- Stable branch, `0 < Ri < 1/6`: `dK/dRi = -5*K/(1-5*Ri)`.
- Unstable branch, `-2 < Ri < 0`: `dK/dRi = -8*K/(1-16*Ri)`.
- Derivative zero at the native stability caps and molecular-conduction floor.

Product-rule terms are added to the donor canopy and receiving soil energy rows, including the latent flux contribution to the latter. This extra correction is restricted to snow-free, residue-free canopy/soil boundaries (`NSP=0, NR=0`); other boundary formulations retain the existing matrix. Finite differences of the original `CANTK` across stable, unstable, capped and multiple-node fixtures agree with the analytic derivatives to a maximum scaled difference of `1.31934e-7`, below the `1e-5` test limit.

At each attempted hour division (1, 2, 4, ... 64), the adapter first uses the corrected storage/leaf matrix (`option=1`). If it fails, the complete pre-hour state is restored and the same division is retried with the conductance derivatives (`option=2`). If both fail, subdivision increases. The requested option is restored after acceptance. The physical residuals and convergence tolerances are identical; original half damping of reversing increments remains in use. Flux 319 reports accepted parts, and positive flux 320 records acceptance using the extra Jacobian. Reference option 0 preserves the original statements and does not use this fallback.

## Conservative root supply

The next basin attempt stopped at HRU 1, 2021 day 197, with a daily residual of `-0.1200223095 mm`. An observation-only hourly trace showed that excess root extraction over transpiration accounted for the loss. For example, hour 6 extracted `0.028526323 mm` while transpiring `0.010678074 mm`; its water residual was approximately `-0.017848342 mm`.

After solving leaf demand, upstream `LEAFT` selects supplying roots once, updates xylem potential, and discards any newly negative root fluxes without solving again. A counterexample uses soil potentials `[-100,-10,-1]`, unit root conductances, demand 1, and an initial xylem potential -50. The one-pass selection retains the last two roots, calculates xylem potential -6, then clips the second root's negative flux; the surviving uptake is 5 for a demand of 1.

For corrected options, `shaw_root_partition.f90` solves `sum(g_i * max(M_i - P_xylem, 0)) = demand`. It starts with all conducting roots, recalculates xylem potential, and removes negative-flow roots until the set is consistent. Each removal raises xylem potential, so removed roots cannot re-enter; at most NS removals are needed. The counterexample gives potential -2 and uptake `[0,0,1]`. Tests also cover node permutation, fully active roots, zero demand, a wet root-free layer and small conductances. Original root-fraction scaling is retained. The bridge limits root depth to the storage domain, so `RTDIST` sums the in-domain fraction to exactly 1 and the bottom boundary node supplies no water.

Every accepted bridge hour additionally checks `abs(root uptake - transpiration) <= 1e-6 mm`. This is an independent invariant, not a water-ledger adjustment. At the current executable checkpoint, isolated HRUs 1, 6 and 98 each complete 1,216 days with maximum daily residuals of 0.006053, 0.003612 and 0.007808 mm, respectively. At the previously failing HRU 1 day the residual is now `0.000152668 mm`. Hourly output precision shows zero uptake/transpiration differences in all three runs. The larger hourly residuals in these basin profiles (up to 0.003314 mm) are reported explicitly; the 0.002 mm/hour limit applies to the controlled kernel fixtures, while the basin acceptance gate remains 0.1 mm/HRU/day.

`canada/canopy_solver_checks.json` records executable and output hashes, cumulative fluxes, hourly invariants and the earlier failing day. HRU 98 changes relative to the pre-conductance/pre-root-fix checkpoint are approximately +0.0151% ET, -0.0105% runoff and +0.0144% percolation. These isolated checks do not substitute for a completed basin comparison or formal convergence study.

## Safe rejection at the native minimum timestep

The root-corrected basin run subsequently stopped at HRU 19, 2022 day 196, hour 16. An isolated replay reproduced a floating invalid operation in `CONDUC`, called by `QVSOIL/WBSOIL`. Diagnostic output showed an intermediate surface-node temperature of `7600.08117` °C, liquid fraction 0.222637 and no ice. This was an unconverged Newton candidate, not an accepted model temperature. Extrapolating the saturation-vapor polynomial at that candidate produced negative transport coefficients, whose geometric mean caused the invalid square root.

Six existing `GOSHAW` large-update guards are conditional on `NDT < MAXNDT`: four energy-row corrections with magnitude above 25, an ice correction above 1, and a relative matric-potential correction above 100. Thus the same unsafe updates are allowed when the native minimum timestep is reached, before the later nonconvergence handling can return control to the adapter.

Corrected options now reject the call before applying an update that violates one of these existing limits at `NDT >= MAXNDT`. The returned failure flag activates the existing complete-hour rollback and subdivision. Original option 0 remains unchanged. No temperature clipping, constitutive-law replacement or tolerance relaxation is introduced; hourly weather stays constant across retries and precipitation is divided conservatively.

The captured hour now passes with two external parts: final surface-node temperature 21.380586 °C, liquid fraction 0.221701, zero ice, net ET 0.387877 mm and water residual `-0.0001163995 mm`. HRU 19 completes all 1,216 days with maximum daily residual 0.005894 mm. Its first 926 daily records remain exactly equal to the pre-guard trajectory; complete HRUs 1, 6 and 98 are also unchanged. Capture, executable hashes and replay results are in `canada/minimum_step_guard_check.json`. The binary state itself remains local and requires the matching compiler/layout.

For isolated diagnosis, set `SWAT_SHAW_HRU` and optionally `SWAT_SHAW_CAPTURE_HOUR` to a space-separated year, Julian day and hour. The bridge writes the corresponding starting state and new hourly forcing to `shaw_failed_column.bin` before entering the kernel; `replay_shaw_column` can then reproduce that hour independently of SWAT+ routing.

## Legacy constituent interface

A subsequent output audit found asterisks in the native `percn` diagnostic. Directly assigning signed SHAW horizon water flux to SWAT's `ly%prk` violates `nut_nlch`'s one-way drainage assumption. Its top-down loop subtracts a negative nitrate flux from the donor, then clamps the receiving layer's negative nitrate inventory before continuing; repeated upward flow can create nitrate. An illustrative two-layer case with initial nitrate [1,0], effective mixing storage 10 and water fluxes [-1,1] creates about 0.10517 additional units of nitrate relative to [0,1], on top of the native 0.0001 stock floor shared by both cases.

The bridge now exports `max(0, daily net horizon water flux)` to legacy `prk`; SHAW's signed water flux, storage and budget remain intact. The change is a compatibility restriction, not a SHAW solute port: upward solute transport is absent and the exported total water flux still includes vapor. Positive and negative subdaily crossings are not separately transported. Water-quality accuracy remains unvalidated, but the previous artificial nutrient creation must not be accepted even in a water/heat experiment because nutrient state can feed back on vegetation.

Native plant/weather output uses adjacent fixed-width fields. An overflowing nitrate field can join its preceding number without whitespace and shift all later weather columns in a naive parser. The forcing comparison therefore reads the documented `4i6,2i8,2x,a16,25f12.3` layout. The report additionally requires finite values in all 25 numeric plant/weather fields and nonnegative bottom nitrate export for each coupled HRU in the complete evaluation period. Failed or manually stopped basin outputs are withheld from comparison.

The preserved HRU 1 run had overflowing `percn` on all 850 printed evaluation days. The restricted interface removes those overflows in complete HRUs 1, 6, 19 and 98; their 25 numeric plant/weather fields are finite and bottom nitrate export is nonnegative. Their full 1,216-day water/heat diagnostic CSVs are byte-identical to the preceding version, showing that the water/heat solver itself was not clipped in these four profiles. Source/output hashes and exact trajectory comparisons are recorded in `canada/transport_fix_check.json`. The whole basin still requires its own completed run and checks.

## Atmospheric snowfall diagnostic

Snowfall reporting now applies native `WTBULB`, pressure and snow-classification settings to atmospheric precipitation before canopy interception. A dry, above-freezing air temperature can therefore still produce diagnosed snow under the original wet-bulb rule. Tests cover this case, warm saturated rain and cold-air snow. The correction changes phase reporting, not SHAW's precipitation physics.

## Moving canopy air volume

The canopy initializer and geometry update create, remove, and redistribute atmospheric vapor as plants grow or snow covers them. The adapter measures signed vapor storage change immediately around every canopy geometry call, including complete removal, using the same control volumes as the residual. Diagnostic flux 318 records this exchange in metres of water equivalent. It is an atmospheric control-volume exchange, reported separately from precipitation and physical evaporation. The daily water ledger subtracts this signed input. Leaf removal transfers intercepted liquid to surface pond storage.

## Verified fixtures

- Original-algorithm path: 720 hours, 282,960 reported values exactly equal to an independently compiled reference retaining the original SAVE storage and solute routines, with zero solutes and the same adapter inputs. Both copies include the same observation-only diagnostics. The corrected algorithm is not asserted to reproduce the original trajectory exactly.
- Corrected path at the selected tolerances: two different soil-node counts and canopies, 240 hours each, independently and interleaved. Temperatures, liquid, ice and returned flux arrays agree exactly. Maximum hourly residual in the budgeted column: `0.000982 mm`.
- Corrected dynamic canopy at the selected tolerances: 288 hours, bare/single/multiple canopy nodes, height changes, wet-canopy leaf removal, snow and freeze/thaw. Maximum hourly residual: `0.001318 mm`.
- Both conservation fixtures retain their `0.002 mm/hour` acceptance limit. An unconverged hourly attempt is rejected and its full state restored before shorter-step retries. The basin gate remains `0.1 mm/HRU/day`; cumulative residuals must also be reported.
- Fresh official SWAT+ comparison: the coupling-off Ames outputs match all 42 selected files after the build banner. The repository's historical golden outputs differ even for the pinned official executable; those files have not been overwritten.

These checks establish the tested numerical properties only. Energy-budget closure, temporal and spatial convergence, plant hydraulic calibration, and validation against field observations remain separate research requirements.

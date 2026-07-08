# XRD Phase Finder 1.1.1

- Added the foundation for separate `Match (%)` and experimental `Gain (%)` candidate metrics. These values are now visible separately and will be tuned further.
- Added local residual scoring infrastructure for mixtures, intended to help rank possible second and third phases after a first phase is selected.
- Kept `Match (%)`, `Gain (%)` and `I/Ic` as separate candidate-table values.
- Finder profile calculations now explicitly include Cu Kα1/Kα2 doublet contributions.
- Finder background estimation now uses the shared robust XRD background estimator.
- Added a `Normalize` checkbox that scales observed XRD patterns to Imax = 100 for display and phase search without changing the original data.

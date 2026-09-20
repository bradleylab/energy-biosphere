# v13 computational corrections and reproduction

This v1.2 release starts from release v1.1, commit `c7bd37c`. The original
numerical input values are unchanged. Metadata corrections in
`data/provenance.json` distinguish adopted ocean temperatures from measurements,
correct the exoplanet download date from the CSV header, and document the exact
stored tidal duration.

## Scientific conventions retained

- The notebook remains the canonical model. `build_v13_artifacts.py` executes its
  code cells in order and calls its existing `compute_ise_temperature` function.
  It does not fit a new prefactor or substitute rounded physical constants.
- The diffuse-radiation efficiency is Landsberg and Tonge's simplified Eq. 9.1,
  with the Eq. A.11 entropy approximation. No proposed quartic term is added.
  The alternate quartic calculation is explicitly a non-adopted diagnostic.
- Main-sequence lifetimes in the catalog use `10 M/L` Gyr with solar-normalized
  mass and luminosity. The `10 M^-3` relation remains confined to the controlled
  Earth-twin examples. All per-planet integration windows are exported.
- Raw accretional energy is not part of the exergy supply. Radiogenic heating
  uses the stored Frank lookup rates, the stored isotope half-lives, the whole
  body mass, and the Gyr-to-second conversion. Tidal heating keeps the original
  constant-power approximation and stored durations.

## Confirmed corrections

1. The Earth-history plot now uses the same Frank radiogenic integral and Earth
   tidal row as the body-budget calculation. Its previous separate radiogenic
   path and Moon-heating row were inconsistent with that calculation. The plot
   remains raw energy; it has not been relabeled or converted into exergy.
2. Historical free-energy denominators in the era table integrate from formation
   to each era boundary, rather than integrating a recent interval of the same
   duration backward from today. The full-age result matches the canonical total.
3. The conditional Landauer curve is exactly one erasure per bit per year; the
   unrelated cellular-metabolic addend was removed. This is a conditional
   reference, not a universal minimum maintenance-power law.
4. `REFERENCE_INTERVAL_YR` and `ARCHEAN_TURNOVER_YR` are distinct. Empirical demand
   is `ISE * cumulative_bit_years / REFERENCE_INTERVAL_YR`. The cumulative
   information ceiling includes the reciprocal normalization consistently.
5. Figure and diagnostic labels distinguish assumed capture fraction, required
   utilization, and Earth-relative versus absolute 100% thresholds.

The default inputs and all canonical body budgets/utilizations remain unchanged.
The accompanying audit quantifies the changed historical plot and era values.

## Reproduce

From the analysis repository, use the pinned requirements and Python 3.11:

```bash
uv run --python 3.11 --with-requirements requirements.txt \
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 \
  --output executed.ipynb biosphere_size_model.ipynb

uv run --python 3.11 --with-requirements requirements.txt \
  python scripts/build_v13_artifacts.py --output-dir results/v13-audit
```

The second command regenerates all analysis plots and the new 250–320 K figure,
exports the curve and marker provenance, checks Equation 15 on the entire plot
grid, independently checks integration identities, and re-executes the actual
normalization/history/demand cells for alternative reference intervals and
Archean turnover times. Assertions fail rather than silently repairing inputs.

Optional `--baseline-dir PATH` compares against a baseline ledger. Optional
`--manuscript-dir PATH` copies regenerated main-text figures and Dataset S1
into `main/figures` and `main/data`, and the SI figure into
`supplement/figures`, within the dated release directory. It refuses a target
that does not have that release structure.

To reproduce the manuscript build, use the supplied AGU classes and bibliography:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error Hinkston_energy_v13.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error Hinkston_SI_v13.tex
```

Build the main text first: the supplement imports its labels with `xr` so the
new figure reference follows automatic numbering. The existing conceptual
Figure 1 is a supplied manuscript asset, not a notebook-generated plot.

## Interpretation and unresolved audit questions

Successful reproduction establishes internal numerical agreement, not validation
of every physical assumption. The audit explicitly retains source-access gaps
for the original Gough formula and textbook lifetime source;
the synchronous low-eccentricity tidal approximation is used outside its formal
domain for some targets. Neither the audit nor the plot turns the Earth-anchored
Arrhenius scaling into a fundamental biological law. Do not promote these checks
to unconditional scientific acceptance or publish a replacement release without
author review and explicit commit/release authorization.

## September 19 source follow-up and label revision

The Frank S2 workbook confirms that the lookup rates are W/kg mantle;
all 125 numerical rows match the adopted CSV to floating-point precision.
Whole-body multiplication therefore implements the stated all-silicate assumption.
The independently adopted isotope half-lives were retained, rather than replaced
with Frank Table 1's rounded values. The optional
`scripts/verify_frank_source.py` can compare a legitimately obtained S2 workbook
with the released CSV; the publisher-supplied workbook is not redistributed.
No scientific constants or input values changed.

The temperature-figure labels are horizontally aligned with their markers, and
the shaded-region annotation does not use the word “caution.” Equation 15 and
marker-value assertions passed again. The figure is regenerated by
`scripts/build_v13_artifacts.py`.

## Traceability utilities

Version 1.2.1 accepts explicit paths instead of relying on the former audit
directory structure. No model parameters or scientific calculations changed.

`scripts/audit_tidal_influence.py --ledger-dir PATH --output-dir PATH` consumes
the ledger produced above and performs an exploratory zero-tide omission test.

`scripts/verify_frank_source.py --source-workbook PATH --output-dir PATH`
requires a legitimately obtained Frank S2 workbook and `openpyxl==3.1.5`.
It writes exports only to the output directory, preserving the source workbook.

`scripts/verify_v13_manuscript.py --manuscript-dir PATH --baseline-dir PATH
--ledger-dir PATH --output-dir PATH` accepts a dated release or a compiled flat
Overleaf bundle. The baseline contains the v12 main text, v10 SI, and v1.1
analysis directory. Generate the ledger with `build_v13_artifacts.py
--baseline-dir PATH` to supply before/after budget comparisons. Optional
`--originals-dir PATH` separately verifies preservation of the original draft.
CSV comparison excludes explicitly identified leading-# metadata comments but
retains every header, data value, row, and row order; both file hashes are logged.
These checks require the manuscript and baseline, which are not distributed
with the public software archive.

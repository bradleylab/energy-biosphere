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

`scripts/audit_tidal_influence.py` is an exploratory omission diagnostic, not
an alternative tidal model. It expects the v13 audit workspace containing the
precomputed `revised_numerical` ledger. `scripts/verify_v13_manuscript.py`
checks a supplied dated manuscript directory against a supplied baseline
directory and is retained to document the manuscript-fidelity check. Neither
utility is part of the fresh-clone reconstruction command above. Together with
the optional Frank source comparison, they preserve the review trail without
redistributing publisher-supplied supplementary material or the manuscript
working directory.

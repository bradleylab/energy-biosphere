# v13 equation-audit summary

This release records the September 2026 audit of the 19 numbered manuscript
equations. The canonical implementation is `biosphere_size_model.ipynb`.
`scripts/audit_equations.py` executes that notebook, writes a body-budget ledger,
and checks the dimensional identities and numerical invariants used in the
manuscript. `scripts/build_v13_artifacts.py` additionally regenerates the
temperature-dependent ISE figure using the notebook's existing
`compute_ise_temperature` function.

## Outcome

The audit found and corrected inconsistencies in the Earth-history producer,
historical-era denominators, the conditional Landauer curve, figure labels, and
some manuscript interpretation. The current 28-body Solar System table, the
1,463-planet dataset, the Earth-calibrated demand, and their canonical
utilizations are reproduced by the released notebook. The verification uses
assertions; it does not silently repair inputs or replace the model.

The accompanying manuscript specifies that the Archean productivity interval is
a broad sensitivity envelope, that the Europa and Enceladus temperatures are
adopted near-freezing assumptions, and that radiogenic rates from Frank et al.'s
Supplementary Table S2 are per unit mantle mass. Applying those rates to whole
body mass is the explicit optimistic assumption `f_sil = 1`.

## Scope

Passing the audit establishes internal consistency and reproducibility. It does
not validate every physical assumption. In particular, the tidal expression is
the synchronous, low-eccentricity approximation and is only an
order-of-magnitude calculation for targets outside that domain. The Gough solar
luminosity parameterization and the main-sequence lifetime cap are corroborated
and implemented consistently, but the original cited source pages were not
available for direct page-level transcription checks. The Arrhenius--Landauer
ISE relation remains an Earth-anchored semi-empirical sensitivity scaling, not a
universal biological-energy law.

## Reproduction

From the repository root:

```bash
uv run --python 3.11 --with-requirements requirements.txt \
  python scripts/audit_equations.py --output-dir results/equation-audit

uv run --python 3.11 --with-requirements requirements.txt \
  python scripts/build_v13_artifacts.py --output-dir results/v1.2
```

The second command checks Eq. 15 over the plotted 250--320 K grid, exports the
curve and marker provenance, and writes the publication figure under `plots/`.

# hinkston-energy-biosphere

Code and data for Hinkston & Bradley, *Free Energy Budgets as
Thermodynamic Constraints on Maximum Biosphere Size* (in preparation,
JGR: Planets).

## What this repo contains

- `biosphere_size_model_v5.ipynb` — analysis notebook that reproduces
  every figure and table in the manuscript. Computes cumulative free
  energy budgets for 28 Solar System bodies, applies source-specific
  exergy efficiencies (Petela for stellar, Carnot for radiogenic,
  unity for tidal, zero for accretional), and compares each body's
  free energy supply to the energy a biosphere would require under
  both an Earth-calibrated information-specific energy and a
  Landauer-limit floor. Also runs the same analysis for a hypothetical
  Earth-twin around stars of different spectral types and for 579
  exoplanets from the NASA Exoplanet Archive.
- `data/` — input data: Solar System body parameters, exoplanet
  table, radiogenic isotope parameters, tidal parameters, Frank et al.
  heating rates, physical constants, and a `provenance.json` record
  for each value.

## Running the notebook

Run `biosphere_size_model_v5.ipynb` top-to-bottom from the repo root.
Figures are written to `plots/`.

Dependencies: `numpy`, `pandas`, `matplotlib`. Tested with Python 3.11.

## Citation

If you use this code or data, please cite the manuscript (citation
to be added on acceptance).

## Contact

Maggie Hinkston <hinkston.m@wustl.edu>
Alex Bradley <abradley@wustl.edu>
Department of Earth, Environmental, and Planetary Sciences,
Washington University in St. Louis

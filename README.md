# energy-biosphere

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

Install the tested Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run `biosphere_size_model_v5.ipynb` top-to-bottom from the repo root.
Figures are written to `plots/`, which the notebook creates automatically.

The command-line reproducibility check is:

```bash
python -m jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 --output executed.ipynb biosphere_size_model_v5.ipynb
```

Tested with Python 3.11.9; package versions are recorded in `requirements.txt`.

## Citation

If you use this code or data, please cite the manuscript and this repository.
Citation metadata are provided in `CITATION.cff`; DOI information will be added
after archival release.

## License

The analysis code is released under the MIT License; see `LICENSE`.
Input data tables compile values from NASA and cited literature sources.
Source data retain their original terms and attribution requirements; file-level
provenance is recorded in `data/provenance.json`.

## Contact

Maggie Hinkston <hinkston.m@wustl.edu>
Alex Bradley <abradley@wustl.edu>
Department of Earth, Environmental, and Planetary Sciences,
Washington University in St. Louis

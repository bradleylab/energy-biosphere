"""Fetch the exoplanet sample from the NASA Exoplanet Archive.

Pulls the archive's *default parameter set* — the PSCompPars composite table,
which carries exactly one row per confirmed planet, populated with the
archive's curated best-available value for each parameter. This replaces an
earlier export of the raw Planetary Systems (PS) table, which held one row per
publication and was collapsed to one row per planet by an arbitrary
file-order rule (``drop_duplicates(keep="first")``); that rule made the
selected parameter set depend on row order rather than on any documented
criterion.

The query and the download date are written into the output file header so the
sample is reproducible. Re-running this script re-queries the archive and will
pick up planets discovered (and parameter revisions published) since the last
pull, so the download date is the provenance that pins a given analysis.

Usage
-----
    python scripts/fetch_exoplanets.py            # writes data/exoplanet_data.csv
    python scripts/fetch_exoplanets.py --dry-run  # print row count only

Sample selection (single-star systems, complete stellar/orbital/planetary
parameters) is applied downstream in the notebook, not here, so the raw pull
stays visible and the filtering logic lives with the analysis.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TAP_SYNC = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

# Columns consumed by biosphere_size_model.ipynb. st_lum is log10(L/L_sun);
# st_age is in Gyr; st_teff in K; st_rad in R_sun; pl_masse/pl_rade in Earth
# units; pl_orbsmax in AU; pl_orbper in days; pl_orbeccen dimensionless.
COLUMNS = [
    "pl_name", "hostname", "pl_masse", "pl_rade", "pl_orbsmax", "pl_orbper",
    "pl_orbeccen", "st_mass", "st_rad", "st_teff", "st_lum", "st_age", "sy_snum",
]

# Default parameter set = PSCompPars (one row per planet). No sample filtering
# here; the notebook drops rows missing any required field and keeps single-star
# systems (sy_snum == 1).
ADQL = f"select {','.join(COLUMNS)} from pscomppars"

OUT = Path(__file__).resolve().parent.parent / "data" / "exoplanet_data.csv"


def fetch(adql: str) -> str:
    params = urllib.parse.urlencode({"query": adql, "format": "csv"})
    url = f"{TAP_SYNC}?{params}"
    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 (fixed host)
        return resp.read().decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print row count, do not write")
    args = ap.parse_args()

    csv_text = fetch(ADQL)
    n_rows = csv_text.count("\n") - 1  # minus header
    today = _dt.date.today().isoformat()

    if args.dry_run:
        print(f"PSCompPars rows returned: {n_rows} (as of {today})")
        return 0

    header = (
        f"# NASA Exoplanet Archive — PSCompPars (default parameter set)\n"
        f"# Source: {TAP_SYNC}\n"
        f"# ADQL: {ADQL}\n"
        f"# Downloaded: {today}\n"
        f"# Rows: {n_rows} (one row per confirmed planet)\n"
        f"# Sample filtering (single-star, complete parameters) applied in the notebook.\n"
    )
    OUT.write_text(header + csv_text)
    print(f"Wrote {n_rows} planets to {OUT} (downloaded {today})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

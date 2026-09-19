"""Exploratory zero-tide influence diagnostic; does not replace the tidal model.

Run with Python 3 from any directory. Uses the existing v13 numerical ledger,
whose canonical notebook sets tidal exergy efficiency to one. Holding all other
terms and biological demand fixed, subtract tidal energy and rescale utilization.
This is an omission test, NOT a bound on omitted high-eccentricity tidal heating.
No rows are dropped or imputed. Outputs go to a separate audit directory.
"""

from pathlib import Path
import csv
import hashlib
import json
import math


def main() -> None:
    audit = Path(__file__).resolve().parents[2]
    source = audit / "revised_numerical"
    output = audit / "tidal_followup_2026-09-19"
    paths = [
        source / "body_budgets.csv",
        source / "all_exoplanet_integration_windows.csv",
    ]
    with paths[0].open() as handle:
        rows = list(csv.DictReader(handle))
    with paths[1].open() as handle:
        exoplanets = {r["pl_name"]: r for r in csv.DictReader(handle)}
    results = []
    for row in rows:
        total, internal, tide = (
            float(row[k]) for k in ("F_total_J", "F_internal_J", "raw_tidal_J")
        )
        assert all(math.isfinite(x) for x in (total, internal, tide))
        assert 0 <= tide < internal <= total
        result = {
            "name": row["name"],
            "exoplanet": row["name"] in exoplanets,
            "tidal_fraction_total": tide / total,
            "tidal_fraction_internal": tide / internal,
        }
        for field, denominator in (
            ("U_total_pct", total),
            ("eta_power_pct", total),
            ("U_internal_pct", internal),
        ):
            value = float(row[field])
            assert math.isfinite(value)
            result[field] = value
            result[field + "_no_tide"] = value * denominator / (denominator - tide)
        results.append(result)
    earth = next(r for r in results if r["name"] == "Earth")
    exo = [r for r in results if r["exoplanet"]]
    summary = {
        "status": "exploratory diagnostic; manuscript and model unchanged",
        "row_count": len(results),
        "exoplanet_count": len(exo),
        "input_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths
        },
        "largest_exoplanet_tidal_fractions": sorted(
            exo, key=lambda r: r["tidal_fraction_total"], reverse=True
        )[:10],
        "selected_bodies": [
            r for r in results if r["name"] in ("Earth", "Europa", "Enceladus")
        ],
    }
    for suffix in ("", "_no_tide"):
        key = "eta_power_pct" + suffix
        summary["above_Earth_power" + suffix] = [
            r["name"] for r in exo if r[key] > earth[key]
        ]
        summary["above_100pct_power" + suffix] = [
            r["name"] for r in exo if r[key] > 100
        ]
    output.mkdir(exist_ok=True)
    with (output / "tidal_influence.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

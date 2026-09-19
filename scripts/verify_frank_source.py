"""Compare published Frank S2 workbook with adopted CSV; export raw sheet for Gemini.

Requires openpyxl. Does not modify the source workbook or scientific model.
The complete sheet export retains empty cells; the verification explicitly
selects rows with numeric present-day isotope rates, excluding blank/header rows.
"""

import csv
import hashlib
import json
import math
from pathlib import Path

import openpyxl


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    audit = root.parent
    source = audit / "sources/frank_2014/1-s2.0-S0019103514004473-mmc2.xlsx"
    target = root / "data/frank_heating_rates.csv"
    sheet = openpyxl.load_workbook(source, data_only=True).worksheets[0]
    rows = list(sheet.values)
    export = source.with_name("Frank2014_S2_complete_sheet.csv")
    with export.open("w") as handle:
        csv.writer(handle).writerows(rows)
    with target.open() as handle:
        adopted = list(
            csv.DictReader(line for line in handle if not line.startswith("#"))
        )
    selected = [
        (i, [row[0], *row[2:7]])
        for i, row in enumerate(rows, 1)
        if all(isinstance(row[j], (int, float)) for j in (0, 2, 3, 4, 5, 6))
    ]
    assert len(selected) == len(adopted), (len(selected), len(adopted))
    errors = []
    for (index, values), row in zip(selected, adopted):
        for expected, actual in zip(values, map(float, row.values())):
            assert math.isfinite(expected) and math.isfinite(actual)
            assert math.isclose(expected, actual, rel_tol=1e-14, abs_tol=0), (
                index,
                expected,
                actual,
            )
            errors.append(
                abs(expected - actual) / abs(expected) if expected else abs(actual)
            )
    params = json.loads((root / "data/radiogenic_isotope_params.json").read_text())
    # Frank et al. 2014, Table 1, half-lives in Ga, citing Turcotte & Schubert 2002.
    published = {"K40": 1.25, "Th232": 14.0, "U235": 0.704, "U238": 4.47}
    summary = {
        "source_header": rows[1][2],
        "source_sheet": sheet.title,
        "raw_sheet_rows": len(rows),
        "selected_numeric_rows": len(selected),
        "excluded_from_comparison_rows": [
            i for i in range(1, len(rows) + 1) if i not in {x[0] for x in selected}
        ],
        "compared_numeric_values": len(errors),
        "max_relative_difference": max(errors),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "adopted_csv_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "half_lives_Gyr": {
            k: {"Frank_Table_1": v, "adopted": params["isotopes"][k]["half_life_Gyr"]}
            for k, v in published.items()
        },
        "method_unchanged": True,
    }
    (source.parent / "source_verification.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

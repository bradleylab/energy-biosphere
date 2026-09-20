"""Check v13 fidelity, record provenance, and render review contact sheets."""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def citation_keys(text: str) -> set[str]:
    return {key.strip() for group in re.findall(
        r"\\cite\w*(?:\[[^\]]*\])*\{([^}]+)\}", text
    ) for key in group.split(",")}


def manuscript_file(root: Path, name: str) -> Path:
    """Resolve a supplied flat bundle or the dated main/SI directory layout."""
    if (root / name).is_file():
        return root / name
    if name == 'references.bib':
        return root / 'shared/bibliography' / name
    section = 'supplement' if name.startswith('Hinkston_SI') or name == 'efficiency_mult_exo.png' else 'main'
    folder = ('source' if name.endswith('.tex') else 'data' if name.endswith('.csv')
              else 'build' if name.startswith('Hinkston_') else 'figures')
    return root / section / folder / name


def check_printed_tables(text: str, ledger: Path) -> int:
    """Compare printed body and twin values within half their displayed last digit."""
    with (ledger / "body_budgets.csv").open() as stream:
        bodies = {r["name"]: r for r in csv.DictReader(stream)}
    snapshot = json.loads((ledger / "audit_values.json").read_text())
    checked = 0

    def check(field: str, expected: float) -> None:
        nonlocal checked
        match = re.search(r"([\d.]+)(?:\s*\\times\s*10\^\{(-?\d+)\})?", field)
        assert match, field
        mantissa, exponent = match[1], int(match[2] or 0)
        printed = float(mantissa) * 10 ** exponent
        decimals = len(mantissa.split(".")[1]) if "." in mantissa else 0
        tolerance = 0.50001 * 10 ** (exponent - decimals)
        assert abs(printed - expected) <= tolerance, (field, expected, tolerance)
        checked += 1

    tables = re.findall(r"\\begin\{table\}(.*?)\\end\{table\}", text, re.S)
    for table in tables:
        twin_index = 0
        for line in table.splitlines():
            fields = [part.strip() for part in line.split("&")]
            if "tab:ssbudgets" in table and len(fields) == 6 and fields[0] in bodies:
                row = bodies[fields[0]]
                expected = [float(row["raw_solar_J"]), sum(float(row[k]) for k in
                            ["raw_radio_J", "raw_tidal_J", "raw_accretion_J"]),
                            float(row["F_total_J"]), float(row["U_total_pct"])]
                for field, value in zip(fields[2:], expected):
                    check(field, value)
            elif "tab:oceanworlds" in table and len(fields) == 8 and fields[0] in bodies:
                row = bodies[fields[0]]
                for index, key in [(2, "F_total_J"), (3, "F_internal_J"),
                                   (5, "U_total_pct"), (6, "U_internal_pct")]:
                    check(fields[index], float(row[key]))
                check(fields[7], float(row["F_total_J"]) / float(bodies["Earth"]["F_total_J"]) * 100)
            elif "tab:hypothetical_exo" in table and fields[0] in {"G2V", "K2V", "M2V", "M5V"}:
                data = snapshot["fixed_distance_twins"] + snapshot["equal_insolation_twins"]
                row = data[twin_index]
                assert row["type"] == fields[0]
                values = [row["M_star"], row["L_star_solar"], row.get("a_eq_AU", 1),
                          row["E_ext_raw"], row["F_total"], row["U_req_pct"]]
                for field, value in zip(fields[1:], values):
                    check(field, value)
                twin_index += 1
    assert checked == 190, checked
    return checked


def verify(manuscript: Path, baseline: Path, output: Path, ledger: Path, originals_dir: Path | None = None) -> dict:
    """Fail on missing equations, altered disclosure or unresolved references."""
    main_path = manuscript_file(manuscript, "Hinkston_energy_v13.tex")
    si_path = manuscript_file(manuscript, "Hinkston_SI_v13.tex")
    old_path = baseline / "Hinkston_energy_v12.tex"
    main, si, old = [p.read_text() for p in [main_path, si_path, old_path]]
    eq_pattern = r"\\begin\{equation\}(.*?)\\end\{equation\}"
    old_eq, new_eq = [re.findall(eq_pattern, s, re.S) for s in [old, main]]
    assert len(old_eq) == len(new_eq) == 19
    normalize = lambda s: re.sub(r"\s+", "", re.sub(r"\\label\{[^}]+\}", "", s))
    changed = [i for i, (a, b) in enumerate(zip(old_eq, new_eq), 1) if normalize(a) != normalize(b)]
    assert changed == [7, 13, 16], changed
    disclosure = lambda s: re.search(r"During the preparation.*?solely responsible for the work\.", s, re.S)[0]
    assert disclosure(old) == disclosure(main), "Author's disclosure changed"
    main_cites = citation_keys(main.split("\\bibliography")[0])
    si_cites = citation_keys(si)
    bib = manuscript_file(manuscript, "references.bib").read_text()
    bib_keys = set(re.findall(r"@\w+\s*\{([^,]+),", bib))
    assert not ((main_cites | si_cites) - bib_keys)
    extras = set(re.findall(r"\\APACinsertmetastar\s*\{%\s*([^}]+)\}", main))
    extras = {k.strip() for k in extras}
    assert extras == si_cites - main_cites, (extras, si_cites - main_cites)
    aux = manuscript_file(manuscript, "Hinkston_energy_v13.aux").read_text()
    expected = {"eq:ise_temperature": "15", "eq:information_rate": "19",
                "fig:conceptual": "1", "fig:ise_temperature": "2",
                "fig:biosphere_efficiency": "4"}
    for label, value in expected.items():
        assert re.search(r"\\newlabel\{" + re.escape(label) + r"\}\{\{" + value + r"\}", aux), label
    build_warnings, pages = {}, {}
    for stem in ["Hinkston_energy_v13", "Hinkston_SI_v13"]:
        log = manuscript_file(manuscript, f"{stem}.log").read_text()
        assert "undefined" not in log.lower(), f"Unresolved reference in {stem}"
        assert "multiply defined" not in log.lower(), f"Duplicate label in {stem}"
        overfull = [float(x) for x in re.findall(r"Overfull \\hbox \(([\d.]+)pt", log)]
        build_warnings[stem] = {"incomplete_conditionals": log.count("was incomplete"),
                                "max_overfull_hbox_pt": max(overfull, default=0)}
        pdf_text = subprocess.check_output(["pdftotext", "-layout", str(manuscript_file(manuscript, f"{stem}.pdf")), "-"], text=True)
        pdf_pages = pdf_text.rstrip("\f\n").split("\f")
        pages[stem] = {"count": len(pdf_pages), "figure_pages": [i for i, p in enumerate(pdf_pages, 1) if "Figure " in p]}
        (output / f"{stem}.txt").write_text(pdf_text)
    # All main and SI references are present, but pre-existing abbreviated author
    # lists can still produce APA-style BibTeX warnings; report rather than hide.
    warnings = re.findall(r"Warning--.*", manuscript_file(manuscript, "Hinkston_energy_v13.blg").read_text())
    for old_name, new_path in [("Hinkston_energy_v12.tex", main_path), ("Hinkston_SI_v10.tex", si_path)]:
        before = (baseline / old_name).read_text()
        diff = difflib.unified_diff(before.splitlines(True), new_path.read_text().splitlines(True),
                                    fromfile=old_name, tofile=new_path.name)
        (output / f"{new_path.stem}.diff").write_text("".join(diff))
    repo = Path(__file__).resolve().parents[1]
    before_notebook = json.loads((baseline / "analysis" / "biosphere_size_model.ipynb").read_text())
    after_notebook = json.loads((repo / "biosphere_size_model.ipynb").read_text())
    code = lambda n: "\n\n".join(f"# Cell {c['id']}\n{''.join(c['source'])}" for c in n["cells"] if c["cell_type"] == "code")
    (output / "notebook_code.diff").write_text("".join(difflib.unified_diff(
        code(before_notebook).splitlines(True), code(after_notebook).splitlines(True), fromfile="v1.1", tofile="v13")))
    assert not [o for c in after_notebook["cells"] for o in c.get("outputs", []) if o.get("output_type") == "error"]
    assert all(c.get("execution_count") is not None for c in after_notebook["cells"] if c["cell_type"] == "code" and "".join(c["source"]).strip())
    baseline_data = baseline / "analysis" / "data"
    input_names = ["constants.json", "solar_system_bodies.csv", "exoplanet_data.csv",
                   "tidal_parameters.csv", "frank_heating_rates.csv", "radiogenic_isotope_params.json"]
    input_comparison = {}
    for name in input_names:
        before, after = baseline_data / name, repo / "data" / name
        if name.endswith('.csv'):
            # Only leading-# metadata lines are excluded; headers, rows, order,
            # missing values, and every stored value must remain identical.
            def records(path):
                with path.open() as stream:
                    return list(csv.reader(line for line in stream if not line.startswith('#')))
            assert records(before) == records(after), name
        else:
            assert before.read_bytes() == after.read_bytes(), name
        input_comparison[name] = {'baseline_sha256': digest(before),
                                  'current_sha256': digest(after),
                                  'comparison': 'CSV records excluding # comments' if name.endswith('.csv') else 'bytes'}
    table_checks = check_printed_tables(main, ledger)
    with (ledger / "before_after_all_bodies.csv").open() as stream:
        comparisons = list(csv.DictReader(stream))
    assert all(float(row["absolute_change"]) == 0 for row in comparisons)
    originals = {}
    if originals_dir is not None:
        for name in ["Hinkston_energy_v12.tex", "Hinkston_SI_v10.tex", "references.bib"]:
            originals[name] = digest(originals_dir / name)
            assert originals[name] == digest(baseline / name), f"Original changed: {name}"
    files = [main_path, si_path, manuscript_file(manuscript, "references.bib"), repo / "biosphere_size_model.ipynb"]
    files += [repo / "data" / name for name in input_names]
    files += list((repo / "scripts").glob("*v13*.py")) + [repo / "scripts" / "audit_equations.py"]
    files += [manuscript_file(manuscript, name) for name in ["Hinkston_energy_v13.pdf", "Hinkston_SI_v13.pdf",
              "ise_temperature.pdf", "earth_e.png", "earths_ise.png", "Dataset_S1_v13.csv"]]
    result = {"checks": "passed", "equation_count": 19, "equations_changed": changed,
              "printed_table_values_checked": table_checks,
              "disclosure_unchanged": True, "numerical_inputs_unchanged": input_names,
              "body_quantity_comparisons_unchanged": len(comparisons),
              "SI_only_references": sorted(extras), "build_warnings": build_warnings,
              "bibtex_warnings": warnings, "PDF_pages": pages,
              "original_file_sha256": originals,
              "original_preservation_check": 'passed' if originals_dir is not None else 'not requested',
              "input_comparison": input_comparison,
              "file_sha256": {str(p): digest(p) for p in files}}
    (output / "verification_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def render(manuscript: Path, output: Path) -> None:
    """Render every delivered PDF page and assemble legible layout overviews."""
    target = output / "rendered"
    target.mkdir(exist_ok=True)
    for stem in ["Hinkston_energy_v13", "Hinkston_SI_v13"]:
        prefix = target / stem
        subprocess.run(["pdftoppm", "-scale-to", "900", "-png", str(manuscript_file(manuscript, f"{stem}.pdf")), str(prefix)], check=True)
        images = sorted(target.glob(f"{stem}-*.png"))
        for group in range(0, len(images), 12):
            sheet = Image.new("RGB", (1200, 430 * ((len(images[group:group+12]) + 3) // 4)), "#dddddd")
            draw = ImageDraw.Draw(sheet)
            for j, path in enumerate(images[group:group+12]):
                im = Image.open(path).convert("RGB")
                im.thumbnail((295, 402))
                x, y = (j % 4) * 300, (j // 4) * 430
                sheet.paste(im, (x, y + 22))
                draw.text((x + 5, y + 4), f"Page {group+j+1}", fill="black")
            sheet.save(target / f"{stem}-contact-{group//12+1}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ledger-dir", type=Path, required=True)
    parser.add_argument("--originals-dir", type=Path)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    result = verify(args.manuscript_dir.resolve(), args.baseline_dir.resolve(), output,
                    args.ledger_dir.resolve(), args.originals_dir)
    if args.render:
        render(args.manuscript_dir.resolve(), output)
    print(json.dumps({k: result[k] for k in ["checks", "equations_changed", "SI_only_references", "build_warnings", "PDF_pages"]}, indent=2))


if __name__ == "__main__":
    main()

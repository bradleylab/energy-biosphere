"""Regenerate audited numerical results and the manuscript's Eq. 15 figure."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from audit_equations import build_ledger, execute_model


def plot_temperature(n: dict, root: Path, output: Path) -> None:
    """Plot the canonical notebook calculation without duplicating its model."""
    temperature = np.linspace(250.0, 320.0, 701)
    result = n["compute_ise_temperature"](temperature)
    ise = result["ISE"]
    # Independent verification of the displayed equation, with identical constants.
    equation15 = result["A_calibrated"] * np.exp(
        -n["Ea_per_molecule"] / (n["k_B"] * temperature)
    ) * n["k_B"] * temperature * np.log(2)
    np.testing.assert_allclose(ise, equation15, rtol=1e-14, atol=0)
    pd.DataFrame({"temperature_K": temperature, "ISE_J_per_bit": ise}).to_csv(
        output / "ise_temperature_curve.csv", index=False
    )
    markers = {}
    for name in ["Earth", "Europa", "Enceladus"]:
        temp = float(n["df_ss"].set_index("name").loc[name, "T_bio_K"])
        point = n["compute_ise_temperature"](temp)
        np.testing.assert_equal(point["ISE"], n["ISE_body_values"][n["names"].index(name)])
        markers[name] = {"temperature_K": temp, "ISE_J_per_bit": float(point["ISE"])}
    provenance = {
        "producer": "scripts/build_v13_artifacts.py",
        "model": "biosphere_size_model.ipynb#bb13cdbabe7a:compute_ise_temperature",
        "calibration_ISE_J_per_bit": n["modern_biosphere_energy"],
        "Ea_J_per_mol": n["Ea_depurination"], "N_A_per_mol": n["N_A"],
        "k_B_J_per_K": n["k_B"], "A_calibrated": float(result["A_calibrated"]),
        "markers": markers, "equation_grid_check": "passed (relative tolerance 1e-14)",
        "interpretation": "Semi-empirical Earth-anchored scaling; not a universal biological requirement.",
    }
    (output / "ise_temperature_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    with plt.rc_context({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                         "font.size": 11, "axes.linewidth": 0.8,
                         "pdf.fonttype": 42, "ps.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(6.6, 4.1), layout="constrained")
        ax.axvspan(250, 273, color="0.94", zorder=0)
        ax.plot(temperature, ise, color="0.15", linewidth=1.6)
        offsets = {"Earth": (10, 0), "Europa": (-10, 0), "Enceladus": (10, 0)}
        symbols = {"Earth": "o", "Europa": "s", "Enceladus": "^"}
        for name, values in markers.items():
            x, y = values["temperature_K"], values["ISE_J_per_bit"]
            ax.plot(x, y, marker=symbols[name], markersize=6, linestyle="none",
                    markerfacecolor="white", markeredgecolor="0.15", zorder=3)
            label = f"{name} ({x:g} K)"
            ax.annotate(label, (x, y), xytext=offsets[name], textcoords="offset points",
                        fontsize=10, ha="right" if name == "Europa" else "left", va="center")
            if name == "Earth":
                ax.annotate("calibration", (x, y), xytext=(10, -13),
                            textcoords="offset points", fontsize=10, ha="left", va="center")
        ax.text(0.018, 0.975, "Low-temperature\nextrapolation", transform=ax.transAxes,
                ha="left", va="top", fontsize=9, color="0.4")
        ax.set(xlim=(250, 320), yscale="log", xlabel="Temperature (K)",
               ylabel=r"ISE (J bit$^{-1}$)")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(which="both", direction="out")
        for ext in ["png", "pdf"]:
            fig.savefig(root / "plots" / f"ise_temperature.{ext}", dpi=300)
        plt.close(fig)


def compare_baseline(baseline: Path, output: Path) -> None:
    """Record every before/after budget and utilization difference."""
    old = pd.read_csv(baseline / "body_budgets.csv").set_index("name")
    new = pd.read_csv(output / "body_budgets.csv").set_index("name")
    assert old.index.equals(new.index), "Body membership changed"
    records = []
    for name in old.index:
        for key in old.columns:
            a, b = float(old.loc[name, key]), float(new.loc[name, key])
            records.append({"body": name, "quantity": key, "before": a, "after": b,
                            "absolute_change": b - a, "relative_change": (b / a - 1) if a else None})
    pd.DataFrame(records).to_csv(output / "before_after_all_bodies.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--manuscript-dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    n = execute_model(root, output)
    ledger = build_ledger(n, root, output)
    plot_temperature(n, root, output)
    if args.baseline_dir:
        compare_baseline(args.baseline_dir.resolve(), output)
    if args.manuscript_dir:
        destination = args.manuscript_dir.resolve()
        main_figures = destination / "main" / "figures"
        supplement_figures = destination / "supplement" / "figures"
        main_data = destination / "main" / "data"
        if not (main_figures.is_dir() and supplement_figures.is_dir() and main_data.is_dir()):
            raise ValueError("Expected the dated release's main, supplement, and shared asset directories")
        for filename in ["ise_temperature.png", "ise_temperature.pdf", "earth_e.png", "earths_ise.png"]:
            shutil.copy2(root / "plots" / filename, main_figures / filename)
        shutil.copy2(root / "plots" / "efficiency_mult_exo.png", supplement_figures / "efficiency_mult_exo.png")
        shutil.copy2(root / "data" / "exoplanet_S1_results.csv", main_data / "Dataset_S1_v13.csv")
    print("Audited model and figure generated:", output)
    print("Earth utilization (%):", ledger["Earth"]["U_total_pct"])
    print("Earth history today:", ledger["figure_history_today"])
    print("Era table:", ledger["era_table"])


if __name__ == "__main__":
    main()

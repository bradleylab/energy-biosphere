"""Execute the notebook and export a reproducible v13 equation-audit ledger.

Run from this repository with the pinned requirements. The notebook remains the
single implementation of the scientific model; independent identities below
are tests, not alternative producers of manuscript results.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def execute_model(root: Path, output: Path) -> dict:
    """Execute canonical code cells in order and retain their shared namespace."""
    notebook = json.loads((root / "biosphere_size_model.ipynb").read_text())
    namespace = {"__name__": "__main__"}
    previous = Path.cwd()
    output.mkdir(parents=True, exist_ok=True)
    try:
        os.chdir(root)  # Compatibility with the released notebook's relative paths.
        with (output / "notebook_stdout.txt").open("w") as log:
            with contextlib.redirect_stdout(log):
                for cell in notebook["cells"]:
                    if cell["cell_type"] != "code":
                        continue
                    source = "".join(cell["source"])
                    exec(compile(source, f"notebook#{cell['id']}", "exec"), namespace)
                    plt.close("all")
    finally:
        os.chdir(previous)
    return namespace


def build_ledger(n: dict, root: Path, output: Path) -> dict:
    """Record component budgets, thresholds, normalization and source inputs."""
    fields = {
        "raw_solar_J": "solar_free_energy_values",
        "raw_radio_J": "radiogenic_energy_values",
        "raw_tidal_J": "tidal_energy_values",
        "raw_accretion_J": "accretional_energy_values",
        "raw_total_J": "total_es",
        "F_total_J": "F_total_values",
        "F_internal_J": "F_internal_values",
        "U_total_pct": "U_req_free",
        "eta_power_pct": "eta_req_power",
        "integration_Gyr": "integration_times",
        "star_age_Gyr": "star_ages",
        "ISE_J_per_bit": "ISE_body_values",
    }
    rows = []
    for i, name in enumerate(n["names"]):
        row = {"name": name, **{k: float(n[v][i]) for k, v in fields.items()}}
        row["U_internal_pct"] = n["E_bio_empirical"] / row["F_internal_J"] * 100
        row["power_relative_to_Earth"] = row["eta_power_pct"] / n["eta_req_power"][n["EARTH_IDX"]]
        rows.append(row)
    pd.DataFrame(rows).to_csv(output / "body_budgets.csv", index=False)
    earth = rows[n["EARTH_IDX"]]
    exo = n["df_exo_f"].copy()
    exo["tau_M_over_L_Gyr"] = n["exo_tau_ms"]
    exo["tau_M_minus3_Gyr"] = 10 * exo["st_mass"] ** -3
    exo["integration_Gyr"] = n["exo_t_int"]
    exo["rate_lookup_age_Gyr"] = [n["age_today"][n["get_heating_index"](x)] for x in exo.st_age]
    capped = exo[exo.st_age > exo.tau_M_over_L_Gyr]
    capped.to_csv(output / "lifetime_capped_planets.csv", index=False)
    exo.to_csv(output / "all_exoplanet_integration_windows.csv", index=False)
    # This reports existing preprocessing, including the explicit tidal NaN fallback.
    missing = {key: int(n["df_exo"][key].isna().sum()) for key in n["subset_cols"]}
    idx = n["get_heating_index"](earth["star_age_Gyr"])
    isotope = {}
    for name, rates in n["heating_rates"].items():
        lam = n["decay_constants"][name]
        rate = rates[idx]
        isotope[name] = {
            "rate_W_per_kg": rate, "lambda_per_Gyr": lam,
            "energy_J": rate / lam * n["k_gyr_to_s"]
            * np.expm1(lam * earth["integration_Gyr"]) * n["masses"][n["EARTH_IDX"]],
        }
    np.testing.assert_allclose(sum(v["energy_J"] for v in isotope.values()), earth["raw_radio_J"], rtol=1e-14)
    for row in rows:
        np.testing.assert_allclose(row["raw_total_J"], sum(row[k] for k in
            ["raw_solar_J", "raw_radio_J", "raw_tidal_J", "raw_accretion_J"]), rtol=1e-14)
    ise_checks = {}
    for temp in [250.0, 270.0, 273.0, 288.0, 320.0]:
        actual = n["compute_ise_temperature"](temp)
        # Same stored constants, independently rearranged anchored Eq. 15.
        anchored = n["modern_biosphere_energy"] * temp / 288 * np.exp(
            n["Ea_per_molecule"] / n["k_B"] * (1 / 288 - 1 / temp))
        np.testing.assert_allclose(actual["ISE"], anchored, rtol=2e-14)
        ise_checks[str(temp)] = {k: float(v) for k, v in actual.items()}
    normalization = []
    q_per_bit = n["modern_biosphere_power_W"] / n["_N_biosphere_bits"]
    for tau in [10 / (365.25 * 24 * 60), 1.0, 100.0]:
        ise_tau = q_per_bit * n["SEC_PER_YR"] * tau
        energy = ise_tau * n["cumulative_bit_years"] / tau
        np.testing.assert_allclose(energy, n["E_bio_empirical"], rtol=1e-14)
        normalization.append({"reference_interval_yr": tau, "ISE_J_per_bit": ise_tau,
                              "E_bio_J": energy, "U_Earth_pct": energy / earth["F_total_J"] * 100})
    archean = n["ave_archean_bits"] * n["ARCHEAN_DURATION_GYR"] * n["GYR_TO_YR"]
    turnover = [{"archean_turnover_yr": tau, "E_bio_J": n["modern_biosphere_energy"] *
                 (n["cumulative_bit_years"] + (tau - 1) * archean)} for tau in [0.1, 1.0, 10.0]]
    # No extrapolation fallback or clipping is introduced by the audit.
    eps = (exo.st_rad * n["R_sun_m"] / (2 * exo.pl_orbsmax * n["CONST"]["AU_TO_M"]["value"])) ** 2
    X = 0.9652 + 0.2777 * np.log(1 / eps) + 0.0511 * eps
    quartic = (X * 288 / exo.st_teff) ** 4 / 3
    era = []
    for name, period, lookback in n["era_table"]:
        bits_years = n["calculate_biosphere_size"](lookback, (n["LIFE_ORIGIN_GYA"] - lookback) * n["GYR_TO_YR"])[2]
        F = n["earth_F_total_at"](n["EARTH_FORMATION_GYR"] - lookback)
        era.append({"era": name, "F_J": F, "U_pct": n["modern_biosphere_energy"] * bits_years / F * 100})
    snapshot = {
        "notebook_sha256": hashlib.sha256((root / "biosphere_size_model.ipynb").read_bytes()).hexdigest(),
        "input_sha256": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((root / "data").glob("*")) if p.is_file()},
        "Earth": earth, "E_bio_empirical_J": n["E_bio_empirical"],
        "E_bio_conditional_J": n["E_bio_thermo"], "q_I_W_per_bit": q_per_bit,
        "ISE_uncertainty_J_per_bit": n["modern_biosphere_energy_err"],
        "cumulative_bit_years": n["cumulative_bit_years"],
        "Archean_fraction": archean / n["cumulative_bit_years"],
        "Earth_radio_isotopes": isotope, "ISE_checks": ise_checks,
        "normalization_checks": normalization, "Archean_turnover_sensitivity": turnover,
        "era_table": era, "fixed_distance_twins": n["hypo_results"],
        "equal_insolation_twins": n["hypo_hz_results"],
        "exo_count": len(exo), "lifetime_capped_planets": len(capped),
        "lifetime_capped_hosts": int(capped.hostname.nunique()),
        "raw_exo_rows": len(n["df_exo"]), "missing_required_field_counts": missing,
        "retained_missing_orbit_period": int(exo.pl_orbper.isna().sum()),
        "retained_nonpositive_distance": int((exo.pl_orbsmax <= 0).sum()),
        "retained_invalid_eccentricity": int(((exo.pl_orbeccen < 0) | (exo.pl_orbeccen >= 1)).sum()),
        "lookup_age_bounds_Gyr": [min(n["age_today"]), max(n["age_today"])],
        "lookup_clamped_count": int(((exo.st_age < min(n["age_today"])) | (exo.st_age > max(n["age_today"]))).sum()),
        "diffuse_exo_epsilon_range": [float(eps.min()), float(eps.max())],
        "proposed_quartic_sensitivity_range": [float(quartic.min()), float(quartic.max())],
        "above_Earth_power_benchmark": [r for r in rows[len(n["df_ss"]):] if r["power_relative_to_Earth"] > 1],
        "above_100pct_power": [r["name"] for r in rows[len(n["df_ss"]):] if r["eta_power_pct"] > 100],
        "figure_history_today": {"solar_J": float(n["solar_t"][-1]), "internal_J": float(n["internal_t"][-1]),
                                 "radiogenic_J": float(n["radiogenic_t"][-1]), "tidal_J": float(n["tidal_t"][-1])},
    }
    (output / "audit_values.json").write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")
    independent_checks(n, output)
    check_model_normalization(n, root, output)
    return snapshot


def check_model_normalization(n: dict, root: Path, output: Path) -> None:
    """Re-execute the actual normalization, history and demand cells in isolation."""
    notebook = json.loads((root / "biosphere_size_model.ipynb").read_text())
    cells = {c["id"]: "".join(c["source"]) for c in notebook["cells"]}
    rows = []
    previous = Path.cwd()
    try:
        os.chdir(root)
        for reference, turnover in [(10 / (365.25 * 24 * 60), 1), (1, 1),
                                    (100, 1), (1, 0.1), (1, 10)]:
            trial = n.copy()
            # Only diagnostic in-memory overrides; no source or input is altered.
            constants = cells["3258ed88"].replace(
                "REFERENCE_INTERVAL_YR = 1.0", f"REFERENCE_INTERVAL_YR = {reference!r}"
            ).replace("ARCHEAN_TURNOVER_YR = 1.0", f"ARCHEAN_TURNOVER_YR = {turnover!r}")
            with contextlib.redirect_stdout(io.StringIO()):
                for source in [
                    constants, cells["24551def"], cells["5ce69298"], cells["59a179b6"]
                ]:
                    exec(source, trial)
            if turnover == 1:
                np.testing.assert_allclose(trial["E_bio_empirical"], n["E_bio_empirical"], rtol=1e-14)
                np.testing.assert_allclose(trial["U_req_free"], n["U_req_free"], rtol=1e-14)
                np.testing.assert_equal(trial["cumulative_bit_years"], n["cumulative_bit_years"])
            rows.append({"reference_interval_yr": reference, "Archean_turnover_yr": turnover,
                         "ISE_J_per_bit": trial["modern_biosphere_energy"],
                         "information_time_bit_years": trial["cumulative_bit_years"],
                         "E_bio_J": trial["E_bio_empirical"],
                         "U_Earth_pct": trial["U_req_free"][trial["EARTH_IDX"]]})
    finally:
        os.chdir(previous)
    (output / "model_normalization_checks.json").write_text(json.dumps(rows, indent=2) + "\n")


def independent_checks(n: dict, output: Path) -> None:
    """Verify identities by quadrature and export non-adopted model diagnostics."""
    checks = {}
    earth = n["EARTH_IDX"]
    t = np.linspace(n["ACCRETION_OFFSET_GYR"], n["star_ages"][earth], 100001)
    luminosity = n["L_sun"] / (1 + 0.4 * (1 - t / (n["t_sun"] / 1e9)))
    absorbed = luminosity / (4 * np.pi * n["distances"][earth] ** 2) * (
        np.pi * n["radii"][earth] ** 2) * (1 - n["albedos"][earth])
    solar_integral = np.trapezoid(absorbed, t) * n["k_gyr_to_s"]
    np.testing.assert_allclose(solar_integral, n["solar_free_energy_values"][earth], rtol=1e-10)
    checks["Eq6_Earth_solar_quadrature_J"] = float(solar_integral)
    checks["Eq3_Earth_Petela"] = n["petela_exergy_fraction"](288, n["T_sun_eff"])
    checks["Eq3_equal_temperature"] = n["petela_exergy_fraction"](288, 288)
    checks["Eq14_R_from_stored_constants"] = n["N_A"] * n["k_B"]
    np.testing.assert_allclose(n["Ea_per_molecule"] / n["k_B"],
                               n["Ea_depurination"] / checks["Eq14_R_from_stored_constants"], rtol=1e-14)
    # Exact angular average over an ellipse, weighted by time in eccentric anomaly.
    eccentricity_checks = []
    anomaly = np.linspace(0, 2 * np.pi, 100001)
    for eccentricity in [0.0, float(n["df_exo_f"].pl_orbeccen.max())]:
        average = np.trapezoid(1 / (1 - eccentricity * np.cos(anomaly)), anomaly) / (2 * np.pi)
        expected = 1 / np.sqrt(1 - eccentricity ** 2)
        np.testing.assert_allclose(average, expected, rtol=1e-12)
        eccentricity_checks.append({"eccentricity": eccentricity, "factor": expected})
    checks["Eq6_eccentricity_checks"] = eccentricity_checks
    # Landsberg-Tonge 1980 Eq. 8.13: entropy integral for diluted Planck occupation.
    y = np.linspace(1e-7, 70, 250001)
    eps_earth = (n["R_sun_m"] / (2 * n["distances"][earth])) ** 2
    exo_eps = (n["df_exo_f"].st_rad * n["R_sun_m"] /
               (2 * n["df_exo_f"].pl_orbsmax * n["CONST"]["AU_TO_M"]["value"])) ** 2
    entropy_checks = []
    for eps in [float(exo_eps.min()), eps_earth, float(exo_eps.max())]:
        occupation = eps / np.expm1(y)
        entropy = (1 + occupation) * np.log1p(occupation) - occupation * np.log(occupation)
        exact_x = 45 / (4 * np.pi ** 4 * eps) * np.trapezoid(y ** 2 * entropy, y)
        fit_x = 0.9652 + 0.2777 * np.log(1 / eps) + 0.0511 * eps
        entropy_checks.append({"epsilon": eps, "X_integral": float(exact_x),
                               "X_fit": float(fit_x), "relative_error": float(fit_x / exact_x - 1)})
    checks["Eq4_entropy_integral_checks"] = entropy_checks
    # The proposed quartic is a diagnostic, NOT an adopted replacement for Eq. 9.1.
    alternative = []
    for i, name in enumerate(n["names"]):
        is_exo = i >= len(n["df_ss"])
        atmospheric = is_exo or name in n["ATMOSPHERIC_BODIES"]
        temp = 288 if is_exo else n["T_bio_values"][i]
        radius_star = n["exo_st_rad_arr"][i - len(n["df_ss"])] if is_exo else n["R_sun_m"]
        temp_star = n["exo_st_teff_arr"][i - len(n["df_ss"])] if is_exo else n["T_sun_eff"]
        eps = (radius_star / (2 * n["distances"][i])) ** 2
        x = 0.9652 + 0.2777 * np.log(1 / eps) + 0.0511 * eps
        delta = (x * temp / temp_star) ** 4 / 3 if atmospheric else 0.0
        f_alt = n["F_total_values"][i] + n["solar_free_energy_values"][i] * delta
        alternative.append({"body": name, "eta_added_diagnostic_only": delta,
                            "F_total_original_J": n["F_total_values"][i], "F_total_diagnostic_J": f_alt,
                            "U_diagnostic_pct": n["E_bio_empirical"] / f_alt * 100})
        np.testing.assert_allclose(n["F_total_values"][i], n["F_solar_values"][i] +
                                   n["F_radiogenic_values"][i] + n["F_tidal_values"][i], rtol=1e-14)
    pd.DataFrame(alternative).to_csv(output / "nonadopted_quartic_diagnostic.csv", index=False)
    checks["Eq4_Earth_diagnostic"] = alternative[earth]
    checks["Eq11_tidal_duration_Gyr"] = sorted(set(n["df_tidal"].age_s / n["k_gyr_to_s"]))
    checks["Eq12_Archean_carbon_tonnes_per_year"] = [
        flux / n["N_A"] * n["EARTH_SURFACE_CM2"] * n["SEC_PER_YR"] * 12 / 1e6
        for flux in [n["ARCHEAN_CARBON_FLUX_MIN"], n["ARCHEAN_CARBON_FLUX_MAX"]]]
    checks["Eq19_standing_bits_from_power"] = n["modern_biosphere_power_W"] / (
        n["modern_biosphere_energy"] / (n["SEC_PER_YR"] * n.get("REFERENCE_INTERVAL_YR", 1.0)))
    np.testing.assert_allclose(checks["Eq19_standing_bits_from_power"], n["_N_biosphere_bits"], rtol=1e-14)
    (output / "independent_checks.json").write_text(json.dumps(checks, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.model_root.resolve(), args.output_dir.resolve()
    n = execute_model(root, output)
    ledger = build_ledger(n, root, output)
    print(json.dumps({key: ledger[key] for key in ["Earth", "E_bio_empirical_J", "exo_count", "lifetime_capped_planets", "lifetime_capped_hosts", "above_100pct_power"]}, indent=2))


if __name__ == "__main__":
    main()

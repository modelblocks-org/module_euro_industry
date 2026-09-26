"""Project aggregated industrial production from a historical reference year.

The projection is intentionally performed at commodity level. Production-route
shares (e.g. BF_BOF/EAF) are not projected here; they belong to a later scenario
transformation stage.

Projection factors are relative to reference-year production:
    future production = reference production * projection factor

A generic projection curve applies to every country/commodity. An optional CSV
can override selected anchor years for selected country/commodity combinations.
Annual factors between anchor years are linearly interpolated.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


REQUIRED_REFERENCE_COLUMNS = {
    "country",
    "commodity",
    "year",
    "production",
    "unit",
}
REQUIRED_OVERRIDE_COLUMNS = {"country", "commodity", "year", "value"}


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _normalise_generic(generic: dict, reference_year: int) -> dict[int, float]:
    if not generic:
        raise ValueError("production_projection.generic must contain at least one future anchor year.")

    anchors = {reference_year: 1.0}
    for year, value in generic.items():
        year = int(year)
        value = float(value)
        if year <= reference_year:
            raise ValueError(
                f"Generic projection year {year} must be later than reference year {reference_year}."
            )
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"Projection factor for {year} must be a finite non-negative number.")
        anchors[year] = value
    return dict(sorted(anchors.items()))


def load_overrides(path: str | Path | None, reference_year: int) -> pd.DataFrame:
    columns = ["country", "commodity", "year", "value"]
    if path in (None, "", "null"):
        return pd.DataFrame(columns=columns)

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Production-projection override CSV not found: {path}")

    df = pd.read_csv(path)
    missing = REQUIRED_OVERRIDE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Projection override CSV is missing required columns: {sorted(missing)}. "
            "Expected country, commodity, year, value."
        )

    df = df[columns].copy()
    df["country"] = df["country"].astype(str).str.strip()
    df["commodity"] = df["commodity"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype(int)
    df["value"] = pd.to_numeric(df["value"], errors="raise").astype(float)

    if (df["year"] <= reference_year).any():
        bad = sorted(df.loc[df["year"] <= reference_year, "year"].unique().tolist())
        raise ValueError(
            f"CSV projection years must be later than reference year {reference_year}; found {bad}."
        )
    if (~np.isfinite(df["value"]) | (df["value"] < 0)).any():
        raise ValueError("CSV projection factors must be finite non-negative numbers.")

    duplicated = df.duplicated(["country", "commodity", "year"], keep=False)
    if duplicated.any():
        duplicates = df.loc[duplicated, ["country", "commodity", "year"]]
        raise ValueError(
            "Projection override CSV contains duplicate country/commodity/year anchors:\n"
            + duplicates.to_string(index=False)
        )

    return df


def _interpolate_curve(
    reference_year: int,
    generic_anchors: dict[int, float],
    override_anchors: pd.DataFrame,
) -> pd.DataFrame:
    """Build one annual curve, with CSV anchors overriding generic anchors."""
    anchors = dict(generic_anchors)
    source_at_anchor = {year: ("historical" if year == reference_year else "generic") for year in anchors}

    for row in override_anchors.itertuples(index=False):
        anchors[int(row.year)] = float(row.value)
        source_at_anchor[int(row.year)] = "csv"

    anchors = dict(sorted(anchors.items()))
    years = np.arange(reference_year, max(anchors) + 1, dtype=int)
    anchor_years = np.array(list(anchors), dtype=int)
    anchor_values = np.array(list(anchors.values()), dtype=float)
    factors = np.interp(years, anchor_years, anchor_values)

    rows = []
    for year, factor in zip(years, factors):
        if year == reference_year:
            source = "historical"
        elif year in source_at_anchor:
            source = source_at_anchor[year]
        else:
            left_i = np.searchsorted(anchor_years, year) - 1
            right_i = left_i + 1
            left_source = source_at_anchor[int(anchor_years[left_i])]
            right_source = source_at_anchor[int(anchor_years[right_i])]
            source = "interpolated_csv" if "csv" in {left_source, right_source} else "interpolated_generic"
        rows.append((int(year), float(factor), source))

    return pd.DataFrame(rows, columns=["year", "projection_factor", "projection_source"])


def project_production(
    reference_path: str | Path,
    config_path: str | Path,
    scenario_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    config = load_config(config_path)
    scenario = load_config(scenario_path)
    historical = config["historical_calibration"]
    projection_cfg = scenario.get("production_projection", {})
    reference_year = int(historical["reference_year"])

    reference = pd.read_csv(reference_path)
    missing = REQUIRED_REFERENCE_COLUMNS - set(reference.columns)
    if missing:
        raise ValueError(
            f"Historical aggregated production is missing required columns: {sorted(missing)}"
        )

    reference = reference.loc[reference["year"].astype(int) == reference_year].copy()
    if reference.empty:
        raise ValueError(
            f"No aggregated historical production rows found for reference year {reference_year}."
        )

    reference["production"] = pd.to_numeric(reference["production"], errors="raise").astype(float)
    generic = _normalise_generic(projection_cfg.get("generic", {}), reference_year)
    overrides = load_overrides(projection_cfg.get("file"), reference_year)

    known_pairs = set(zip(reference["country"], reference["commodity"]))
    if not overrides.empty:
        override_pairs = set(zip(overrides["country"], overrides["commodity"]))
        unknown = sorted(override_pairs - known_pairs)
        if unknown:
            formatted = ", ".join(f"{c}/{p}" for c, p in unknown)
            raise ValueError(
                "Projection override CSV contains country/commodity combinations not present "
                f"in historical aggregated production: {formatted}"
            )

    frames = []
    metadata_cols = [c for c in reference.columns if c not in {"year", "production"}]

    for row in reference.itertuples(index=False):
        country = str(row.country)
        commodity = str(row.commodity)
        group_overrides = overrides.loc[
            (overrides["country"] == country) & (overrides["commodity"] == commodity)
        ]
        curve = _interpolate_curve(reference_year, generic, group_overrides)

        base_production = float(row.production)
        curve["production"] = base_production * curve["projection_factor"]
        curve["reference_production"] = base_production
        curve["reference_year"] = reference_year

        row_dict = row._asdict()
        for col in metadata_cols:
            curve[col] = row_dict[col]

        frames.append(curve)

    projected = pd.concat(frames, ignore_index=True)
    preferred = [
        "country",
        "sector",
        "sector_name",
        "commodity",
        "year",
        "production",
        "unit",
        "projection_factor",
        "projection_source",
        "reference_year",
        "reference_production",
    ]
    columns = [c for c in preferred if c in projected.columns]
    columns += [c for c in projected.columns if c not in columns]
    projected = projected[columns]
    projected.sort_values(["country", "commodity", "year"], inplace=True)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    projected.to_csv(output_path, index=False, float_format="%.6f")
    return projected


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-production", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_production(args.reference_production, args.config, args.scenario, args.output)

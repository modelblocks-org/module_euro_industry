"""Prepare route-preserving historical industrial production.

The output stays close to JRC-IDEES: each JRC sector/activity is retained as a
record, while production routes are only distinguished where JRC itself gives
separate historical activity (steel and aluminium). Basic chemicals are
replaced by the calibrated AMMONIA/HVC/CHLORINE/METHANOL activities used by the
legacy workflow.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import country_converter as coco
import numpy as np
import pandas as pd
import yaml

from _industry_schema import (
    CHEMICAL_SCHEMA,
    JRC_INDUSTRY_SHEETS,
    JRC_NAMES,
    PRODUCTION_DEFINITIONS,
    SECTOR_NAMES,
)

TJ_TO_KTOE = 0.0238845

# Eurostat sector names used only to scale JRC-EU27 activity for countries
# without a national JRC-IDEES workbook.
EB_SECTORS = {
    "Iron & steel": "ISI",
    "Chemical & petrochemical": "CHI",
    "Non-ferrous metals": "NFM",
    "Paper, pulp & printing": "PPA",
    "Food, beverages & tobacco": "FBT",
    "Non-metallic minerals": "NMM",
    "Transport equipment": "TRE",
    "Machinery": "MAE",
    "Textile & leather": "TEL",
    "Wood & wood products": "WWP",
    "Not elsewhere specified (industry)": "OIS",
}

CH_MAPPING = {
    "Nahrung": "FBT",
    "Textil / Leder": "TEL",
    "Papier / Druck": "PPA",
    "Chemie / Pharma": "CHI",
    "Zement / Beton": "NMM",
    "Andere NE-Mineralien": "NMM",
    "Metall / Eisen": "ISI",
    "NE-Metall": "NFM",
    "Metall / Geräte": "TRE",
    "Maschinen": "MAE",
    "Andere Industrien": "OIS",
}


def find_physical_output(df: pd.DataFrame) -> slice:
    labels = df.index.to_series().astype("string")
    starts = np.flatnonzero(labels.str.contains("Physical output", na=False).to_numpy())
    if not len(starts):
        raise ValueError("Could not locate the 'Physical output' block in JRC-IDEES sheet.")
    start = int(starts[0])
    empty_rows = np.flatnonzero(df.index.isna())
    following = empty_rows[empty_rows > start]
    end = int(following[0]) if len(following) else len(df)
    return slice(start, end)


def get_energy_ratio(country: str, eurostat_dir: Path, jrc_dir: Path, year: int, ch_path: Path) -> pd.Series:
    """National/EU27 sector energy ratio used by the legacy non-EU proxy."""
    if country == "CH":
        energy = pd.read_csv(ch_path, index_col=0).dropna()
        energy = energy.rename(index=CH_MAPPING).groupby(level=0).sum()
        energy = energy[str(min(2019, year))] * TJ_TO_KTOE
    else:
        eurostat_country = country.replace("GB", "UK")
        filename = eurostat_dir / f"{eurostat_country}-Energy-balance-sheets-April-2023-edition.xlsb"
        df = pd.read_excel(filename, sheet_name=str(min(2019, year)), index_col=2, header=0, skiprows=4)
        energy = df.loc[list(EB_SECTORS), "Total"].rename(index=EB_SECTORS)

    filename = jrc_dir / "EU27" / "JRC-IDEES-2021_Industry_EU27.xlsx"
    df = pd.read_excel(filename, sheet_name="Ind_Summary", index_col=0, header=0)
    year_i = df.columns.get_loc(year)
    eu27_energy = df.iloc[50:77, year_i]
    eu27_energy.index = eu27_energy.index.astype(str).str.lstrip()
    sector_names = {
        "Iron and steel": "ISI",
        "Chemical industry": "CHI",
        "Non-metallic mineral products": "NMM",
        "Pulp, paper and printing": "PPA",
        "Food, beverages and tobacco": "FBT",
        "Non Ferrous Metals": "NFM",
        "Transport equipment": "TRE",
        "Machinery equipment": "MAE",
        "Textiles and leather": "TEL",
        "Wood and wood products": "WWP",
        "Other industrial sectors": "OIS",
    }
    eu27_energy = eu27_energy.rename(index=sector_names)
    return energy / eu27_energy


def read_sector(country: str, sector: str, year: int, jrc_dir: Path) -> list[dict]:
    jrc_country = JRC_NAMES.get(country, country)
    filename = jrc_dir / jrc_country / f"JRC-IDEES-2021_Industry_{jrc_country}.xlsx"
    df = pd.read_excel(filename, sheet_name=JRC_INDUSTRY_SHEETS[sector], index_col=0, header=0)
    year_i = df.columns.get_loc(year)
    physical_output = df.iloc[find_physical_output(df), year_i]

    records = []
    for definition in PRODUCTION_DEFINITIONS[sector]:
        field = definition["source_field"]
        if field not in physical_output.index:
            raise ValueError(f"Could not find JRC production field '{field}' in {sector}/{country}.")
        records.append(
            {
                "sector": sector,
                "sector_name": SECTOR_NAMES[sector],
                "activity": definition["activity"],
                "commodity": definition["commodity"],
                "production_route": definition["production_route"],
                "production": pd.to_numeric(physical_output.loc[field], errors="coerce"),
                "unit": definition["unit"],
                "source": "JRC-IDEES-2021",
                "source_field": field,
            }
        )
    return records


def production_per_country(country: str, year: int, eurostat_dir: Path, jrc_dir: Path, ch_path: Path, eu27: set[str]) -> pd.DataFrame:
    source_country = country if country in eu27 else "EU27"
    records = []
    for sector in PRODUCTION_DEFINITIONS:
        records.extend(read_sector(source_country, sector, year, jrc_dir))
    production = pd.DataFrame(records)

    if country not in eu27:
        ratios = get_energy_ratio(country, eurostat_dir, jrc_dir, year, ch_path)
        production["production"] = production["production"] * production["sector"].map(ratios)
        production["source"] = "JRC-IDEES-2021 EU27 scaled by national sector energy"

    production.insert(0, "country", country)
    production["year"] = year
    return production


def split_basic_chemicals(production: pd.DataFrame, ammonia_path: Path, year: int, calibration: dict) -> pd.DataFrame:
    """Apply the legacy historical chemical calibration in normalized records."""
    mask = (production["sector"] == "CHI") & (production["commodity"] == "BASIC_CHEMICALS")
    basic = production.loc[mask].copy().set_index("country")
    other = production.loc[~mask].copy()

    ammonia = pd.read_csv(ammonia_path, index_col=0)
    year_to_use = min(max(year, 2018), 2022)
    ammonia_series = pd.Series(0.0, index=basic.index)
    available = ammonia.index.intersection(basic.index)
    ammonia_series.loc[available] = pd.to_numeric(ammonia.loc[available, str(year_to_use)], errors="coerce").fillna(0.0)

    # This intentionally preserves the legacy numerical calibration. JRC basic
    # chemicals are reported as kt ethylene-equivalent while USGS ammonia is kt
    # NH3; the subtraction/distribution is therefore a calibration convention,
    # not a physical mass balance.
    residual = (basic["production"] - ammonia_series).clip(lower=0.0)
    distribution_key = residual / calibration["basic_chemicals_without_NH3_production_today"] / 1e3

    calibrated = {
        "Ammonia": ammonia_series,
        "HVC": calibration["HVC_production_today"] * 1e3 * distribution_key,
        "Chlorine": calibration["chlorine_production_today"] * 1e3 * distribution_key,
        "Methanol": calibration["methanol_production_today"] * 1e3 * distribution_key,
    }

    records = []
    for activity, values in calibrated.items():
        schema = CHEMICAL_SCHEMA[activity]
        for country, value in values.items():
            records.append(
                {
                    "country": country,
                    "sector": schema["sector"],
                    "sector_name": schema["sector_name"],
                    "activity": activity,
                    "commodity": schema["commodity"],
                    "production_route": schema["production_route"],
                    "production": value,
                    "unit": schema["unit"],
                    "source": "USGS" if activity == "Ammonia" else "historical_calibration",
                    "source_field": "USGS T12" if activity == "Ammonia" else "JRC basic chemicals residual",
                    "year": year,
                }
            )
    return pd.concat([other, pd.DataFrame(records)], ignore_index=True)


def aggregate_commodities(production: pd.DataFrame) -> pd.DataFrame:
    """Optional convenience table; route-specific production remains primary."""
    group_cols = ["country", "sector", "sector_name", "commodity", "year", "unit"]
    return production.groupby(group_cols, as_index=False, dropna=False)["production"].sum()


def prepare_current_production(countries, calibration, jrc_dir, eurostat_dir, ch_path, ammonia_path, output_path, aggregate_path):
    year = int(calibration["reference_year"])
    eu27 = set(coco.CountryConverter().EU27as("ISO2").ISO2.values)
    frames = [production_per_country(c, year, Path(eurostat_dir), Path(jrc_dir), Path(ch_path), eu27) for c in countries]
    production = pd.concat(frames, ignore_index=True)
    production = split_basic_chemicals(production, Path(ammonia_path), year, calibration)
    production["production"] = pd.to_numeric(production["production"], errors="coerce").fillna(0.0)
    production.sort_values(["country", "sector", "activity", "production_route"], inplace=True)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    production.to_csv(output_path, index=False, float_format="%.6f")

    aggregated = aggregate_commodities(production)
    aggregate_path = Path(aggregate_path)
    aggregate_path.parent.mkdir(parents=True, exist_ok=True)
    aggregated.to_csv(aggregate_path, index=False, float_format="%.6f")


def load_config(path):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--jrc-dir", required=True)
    parser.add_argument("--eurostat-dir", required=True)
    parser.add_argument("--ch-industrial-production", required=True)
    parser.add_argument("--ammonia-production", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--aggregated-output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    prepare_current_production(
        config["countries"], config["historical_calibration"], args.jrc_dir,
        args.eurostat_dir, args.ch_industrial_production, args.ammonia_production,
        args.output, args.aggregated_output,
    )

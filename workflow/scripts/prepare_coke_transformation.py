"""Prepare Eurostat coke-oven transformation output used in historical calibration."""

from __future__ import annotations

import argparse
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

IDX = pd.IndexSlice
IDEES_RENAME = {"GR": "EL", "GB": "UK"}


def eurostat_per_country(input_eurostat: str | Path, country: str) -> pd.DataFrame:
    filename = Path(input_eurostat) / f"{country}-Energy-balance-sheets-April-2023-edition.xlsb"
    sheets = pd.read_excel(
        filename,
        engine="pyxlsb",
        sheet_name=None,
        skiprows=4,
        index_col=list(range(4)),
        na_values=":",
    )
    sheets.pop("Cover", None)
    return pd.concat(sheets)


def build_eurostat(input_eurostat: str | Path, countries: list[str]) -> pd.DataFrame:
    countries_no_che = {IDEES_RENAME.get(country, country) for country in countries} - {"CH"}
    func = partial(eurostat_per_country, input_eurostat)
    dfs = [func(country) for country in countries_no_che]

    index_names = ["country", "year", "lvl1", "lvl2", "lvl3", "lvl4"]
    df = pd.concat(dfs, keys=countries_no_che, names=index_names)
    df.index = df.index.set_levels(df.index.levels[1].astype(int), level=1)

    unnamed_cols = df.columns[df.columns.astype(str).str.startswith("Unnamed")]
    df.drop(unnamed_cols, axis=1, inplace=True)
    df.drop(list(range(1990, 2022)), axis=1, inplace=True, errors="ignore")
    df.replace("Z", 0, inplace=True)
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.select_dtypes(include=[np.number])

    int_avia = df.index.get_level_values(3) == "International aviation"
    temp = df.loc[int_avia]
    temp.index = pd.MultiIndex.from_frame(temp.index.to_frame().fillna("International aviation"))
    df = pd.concat([temp, df.loc[~int_avia]]).sort_index()

    for country in countries_no_che:
        slicer = IDX[country, :, :, :, "Domestic aviation"]
        for col in ["Total", "Fossil energy"]:
            if col in df.columns:
                df.loc[slicer, col] = df.loc[slicer, col].replace(0.0, np.nan).ffill().bfill()

    df.rename(
        index={
            "Households": "Residential",
            "Commercial & public services": "Services",
            "Domestic navigation": "Domestic Navigation",
            "International maritime bunkers": "Bunkers",
            "UK": "GB",
            "EL": "GR",
        },
        columns={"Total": "Total all products"},
        inplace=True,
    )
    df.sort_index(inplace=True)

    # ktoe/a -> TWh/a
    df *= 11.63 / 1e3
    return df


def prepare_coke_transformation(
    eurostat_dir: str | Path,
    countries: list[str],
    output_path: str | Path,
) -> None:
    eurostat = build_eurostat(eurostat_dir, countries)
    slicer = pd.IndexSlice[:, :, :, "Coke ovens", "Other sources", :]
    coke = eurostat.loc[slicer, :].droplevel(level=[2, 3, 4, 5])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    coke.to_csv(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eurostat-dir", required=True)
    parser.add_argument("--countries", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare_coke_transformation(args.eurostat_dir, args.countries, args.output)

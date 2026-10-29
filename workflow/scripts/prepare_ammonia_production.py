"""Prepare historical annual ammonia production from the USGS workbook."""

import sys
from pathlib import Path

import country_converter as coco
import pandas as pd


def prepare_ammonia_production(input_path: str | Path, output_path: str | Path) -> None:
    """Extract annual ammonia production and convert kton N to kton NH3."""
    ammonia = pd.read_excel(
        input_path,
        sheet_name="T12",
        skiprows=5,
        header=0,
        index_col=0,
        skipfooter=7,
        na_values=["--"],
    )

    cc = coco.CountryConverter()
    ammonia.index = cc.convert(ammonia.index, to="iso2")

    years = [str(year) for year in range(2018, 2023)]
    ammonia = ammonia.rename(columns=lambda x: str(x))[years]

    # USGS reports nitrogen content; convert kton N to kton NH3.
    ammonia *= 17 / 14
    ammonia.index.name = "ktonNH3/a"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ammonia.to_parquet(output_path)


def main() -> None:
    prepare_ammonia_production(snakemake.input.usgs, snakemake.output[0])


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main()

"""Prepare land shapes and country lists using ISO2 country codes."""

import sys
from pathlib import Path

import country_converter as coco
import geopandas as gpd


def read_regions(path: str) -> gpd.GeoDataFrame:
    """Validate and normalize user regions once for all downstream steps."""
    regions = gpd.read_parquet(path)
    if "shape_class" in regions.columns:
        regions = regions.loc[regions["shape_class"].eq("land")].copy()
    if regions.empty:
        raise ValueError("The supplied shapes contain no land regions.")
    if "shape_id" not in regions.columns:
        raise ValueError(f"Region id column 'shape_id' not found in {path}.")
    if "country_id" not in regions.columns:
        raise ValueError(f"Country column 'country_id' not found in {path}.")

    regions = regions.rename(columns={"shape_id": "region"}).copy()
    regions["region"] = regions["region"].astype(str)

    countries = regions["country_id"].astype(str).str.upper()
    unique_countries = countries.unique().tolist()
    converter = coco.CountryConverter()
    country_codes = {
        country: converter.convert(country, to="ISO2") for country in unique_countries
    }
    regions["country"] = countries.map(country_codes)

    if regions["region"].duplicated().any():
        dup = regions.loc[regions["region"].duplicated(), "region"].tolist()
        raise ValueError(f"Duplicate region identifiers in GeoParquet: {dup[:10]}")

    if regions.crs is None:
        raise ValueError("The user GeoParquet has no CRS. Please provide a valid CRS.")

    return regions[["region", "country", "geometry"]].to_crs("EPSG:4326")


def country_scope(country_ids, supported_countries, eu_countries):
    """Add the fixed EU reference only when non-EU inference is needed."""
    country_ids = sorted(set(country_ids))
    if not country_ids:
        raise ValueError("The supplied shapes contain no land countries.")
    unsupported = set(country_ids) - set(supported_countries)
    if unsupported:
        raise ValueError(
            "No supported industrial calibration source for countries: "
            f"{', '.join(sorted(unsupported))}. "
            "Supply shapes restricted to supported countries, or add a verified "
            "industrial data source before including these countries."
        )
    reference = sorted(set(supported_countries) & set(eu_countries))
    source_country_ids = set(country_ids)
    if source_country_ids - set(eu_countries):
        source_country_ids.update(reference)
    return country_ids, sorted(source_country_ids)


def main():
    """Prepare land shapes and target/reference country lists."""
    shapes = read_regions(snakemake.input.shapes)
    country_ids, source_country_ids = country_scope(
        shapes["country"].unique(),
        snakemake.params.supported_countries,
        coco.CountryConverter().EU27as("ISO2").ISO2.tolist(),
    )
    shapes.to_parquet(snakemake.output.shapes, index=False)
    Path(snakemake.output.country_ids).write_text("\n".join(country_ids) + "\n")
    Path(snakemake.output.source_country_ids).write_text(
        "\n".join(source_country_ids) + "\n"
    )


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main()

"""Prepare land shapes using required input columns and ISO2 country codes."""

import sys

import country_converter as coco
import geopandas as gpd
from _country_scope import country_scope


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


def main():
    """Prepare the shape-specific workflow input."""
    shapes = read_regions(snakemake.input.shapes)
    country_scope(
        shapes["country"].unique(),
        snakemake.params.supported_countries,
        coco.CountryConverter().EU27as("ISO2").ISO2.tolist(),
    )
    shapes.to_parquet(snakemake.output.shapes, index=False)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main()

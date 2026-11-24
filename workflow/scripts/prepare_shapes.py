"""Prepare land shapes and country lists using ISO2 country codes."""

import sys
from pathlib import Path

import country_converter as coco
import geopandas as gpd
from _schemas import ShapesSchema


def read_regions(path: str, reference_year: int) -> gpd.GeoDataFrame:
    """Validate and normalize user regions once for all downstream steps."""
    regions = gpd.read_parquet(path)
    regions = ShapesSchema.validate_for_year(regions, reference_year)
    regions = regions.loc[regions["shape_class"].eq("land")].copy()

    regions = regions.rename(columns={"shape_id": "region"}).copy()
    regions["region"] = regions["region"].astype(str)

    countries = regions["country_id"].astype(str).str.upper()
    unique_countries = countries.unique().tolist()
    converter = coco.CountryConverter()
    country_codes = {
        country: converter.convert(country, to="ISO2") for country in unique_countries
    }
    regions["country"] = countries.map(country_codes)

    return regions[["region", "country", "geometry"]].to_crs("EPSG:4326")


def country_scope(country_ids, supported_countries, eu_countries):
    """Add the fixed EU reference only when non-EU inference is needed."""
    country_ids = sorted(set(country_ids))
    unsupported = set(country_ids) - set(supported_countries)
    if unsupported:
        raise ValueError(
            "No supported industrial calibration source for countries: "
            f"{', '.join(sorted(unsupported))}. "
            "Supply shapes restricted to supported countries."
        )
    reference = sorted(set(supported_countries) & set(eu_countries))
    source_country_ids = set(country_ids)
    if source_country_ids - set(eu_countries):
        source_country_ids.update(reference)
    return country_ids, sorted(source_country_ids)


def main():
    """Prepare land shapes and target/reference country lists."""
    shapes = read_regions(snakemake.input.shapes, snakemake.params.reference_year)
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

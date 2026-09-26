from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml


HOTMAPS_CATEGORY_BY_SECTOR = {
    "ISI": "Iron and steel",
    "CHI": "Chemical industry",
    "PPA": "Paper and printing",
    "NFM": "Non-ferrous metals",
    "FBT": "Other non-classified",
    "TRE": "Other non-classified",
    "MAE": "Other non-classified",
    "TEL": "Other non-classified",
    "WWP": "Other non-classified",
    "OIS": "Other non-classified",
}

SUPPORTED_FALLBACKS = {"generic_industry", "population", "user_key", "uniform"}


def spatial_category(sector: str, commodity: str) -> str:
    """Map model sector/commodity to the Hotmaps industrial subsector taxonomy."""
    if sector == "NMM":
        if commodity in {"CEM", "CEMENT"}:
            return "Cement"
        if commodity == "GLASS":
            return "Glass"
        return "Non-metallic mineral products"
    return HOTMAPS_CATEGORY_BY_SECTOR.get(sector, "Other non-classified")


def read_regions(path: str, region_id_column: str, country_column: str | None) -> gpd.GeoDataFrame:
    regions = gpd.read_file(path)
    if region_id_column not in regions.columns:
        raise ValueError(f"Region id column '{region_id_column}' not found in {path}.")

    regions = regions.rename(columns={region_id_column: "region"}).copy()
    regions["region"] = regions["region"].astype(str)

    if country_column:
        if country_column not in regions.columns:
            raise ValueError(f"Country column '{country_column}' not found in {path}.")
        regions["country"] = regions[country_column].astype(str).str.upper()
    else:
        regions["country"] = regions["region"].str[:2].str.upper()

    if regions["region"].duplicated().any():
        dup = regions.loc[regions["region"].duplicated(), "region"].tolist()
        raise ValueError(f"Duplicate region identifiers in GeoJSON: {dup[:10]}")

    if regions.crs is None:
        raise ValueError("The user GeoJSON has no CRS. Please provide a valid CRS.")

    return regions[["region", "country", "geometry"]].to_crs("EPSG:4326")


def read_hotmaps(path: str) -> gpd.GeoDataFrame:
    df = pd.read_csv(path, sep=";", index_col=0, low_memory=False)
    required = {"geom", "Subsector"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Hotmaps file is missing required columns: {sorted(missing)}")

    coords = df["geom"].astype("string").str.split(";", n=1, expand=True)
    if coords.shape[1] < 2:
        raise ValueError("Could not parse Hotmaps 'geom' column as '<SRID>;<WKT>'.")
    df["coordinates"] = coords[1]
    df = df[df["coordinates"].notna()].copy()

    geometry = gpd.GeoSeries.from_wkt(df["coordinates"], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    ets = pd.to_numeric(gdf.get("Emissions_ETS_2014"), errors="coerce")
    eprtr = pd.to_numeric(gdf.get("Emissions_EPRTR_2014"), errors="coerce")
    gdf["site_weight"] = ets.combine_first(eprtr)
    return gdf


def assign_sites_to_regions(hotmaps: gpd.GeoDataFrame, regions: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    joined = gpd.sjoin(
        hotmaps,
        regions[["region", "country", "geometry"]],
        how="inner",
        predicate="within",
    )
    if joined.index.duplicated().any():
        joined = joined[~joined.index.duplicated(keep="first")].copy()
    return joined


def normalized_region_key(facilities: pd.DataFrame, region_index: pd.Index) -> pd.Series:
    """Return region shares summing to one using Hotmaps site emissions as weights."""
    if facilities.empty:
        return pd.Series(0.0, index=region_index, dtype=float)

    weights = pd.to_numeric(facilities["site_weight"], errors="coerce").copy()
    positive = weights[weights > 0]
    if positive.empty:
        weights = pd.Series(1.0, index=facilities.index)
    else:
        fill = float(positive.quantile(0.20))
        weights = weights.fillna(fill).clip(lower=0.0)
        if weights.sum() <= 0:
            weights = pd.Series(1.0, index=facilities.index)

    shares = weights / weights.sum()
    by_region = shares.groupby(facilities["region"]).sum()
    return by_region.reindex(region_index, fill_value=0.0)


def read_generic_key(path: str, cfg: dict, default_source_name: str) -> pd.DataFrame:
    """Read a user-provided regional weighting table.

    Expected columns are configured through region_column, country_column and
    weight_column. The weights do not have to be normalized; normalization is
    performed after restricting to regions in the supplied GeoJSON.
    """
    df = pd.read_csv(path, low_memory=False)
    region_col = cfg.get("region_column", "name")
    country_col = cfg.get("country_column", "ct")
    weight_col = cfg.get("weight_column", "fraction")

    missing = [c for c in (region_col, country_col, weight_col) if c not in df.columns]
    if missing:
        raise ValueError(
            f"Generic spatial key file {path} is missing configured columns: {missing}"
        )

    out = df[[region_col, country_col, weight_col]].copy()
    out.columns = ["region", "country", "weight"]
    out["region"] = out["region"].astype(str)
    out["country"] = out["country"].astype(str).str.upper()
    out["weight"] = pd.to_numeric(out["weight"], errors="coerce")
    out["source_name"] = cfg.get("source_name", default_source_name)
    return out


def generic_key_for_country(
    table: pd.DataFrame | None,
    country: str,
    region_index: pd.Index,
) -> pd.Series | None:
    if table is None:
        return None

    subset = table[(table["country"] == country) & (table["region"].isin(region_index))].copy()
    if subset.empty:
        return None

    weights = subset.groupby("region", observed=True)["weight"].sum().reindex(region_index, fill_value=0.0)
    weights = pd.to_numeric(weights, errors="coerce").fillna(0.0).clip(lower=0.0)
    if weights.sum() <= 0:
        return None
    return weights / weights.sum()


def choose_fallback(
    fallback_options: list[str],
    country: str,
    region_index: pd.Index,
    country_sites: pd.DataFrame,
    population: pd.DataFrame | None,
    user_key: pd.DataFrame | None,
) -> tuple[pd.Series, str, int]:
    """Evaluate configured fallback options in order and return the first available key."""
    for option in fallback_options:
        if option == "generic_industry":
            key = normalized_region_key(country_sites, region_index)
            if float(key.sum()) > 0:
                return key / key.sum(), "generic_industry", int(len(country_sites))

        elif option == "population":
            key = generic_key_for_country(population, country, region_index)
            if key is not None:
                return key, "population", 0

        elif option == "user_key":
            key = generic_key_for_country(user_key, country, region_index)
            if key is not None:
                source = "user_key"
                if user_key is not None and "source_name" in user_key.columns:
                    vals = user_key.loc[user_key["country"] == country, "source_name"].dropna().unique()
                    if len(vals):
                        source = str(vals[0])
                return key, source, 0

        elif option == "uniform":
            return (
                pd.Series(1.0 / len(region_index), index=region_index),
                "uniform",
                0,
            )

        else:
            raise ValueError(
                f"Unknown spatial fallback option '{option}'. "
                f"Supported values are: {sorted(SUPPORTED_FALLBACKS)}"
            )

    raise ValueError(
        f"No spatial fallback could be constructed for country {country}. "
        "Add 'uniform' as the final fallback if an unconditional fallback is desired."
    )


def build_keys(
    regions: gpd.GeoDataFrame,
    hotmaps: gpd.GeoDataFrame,
    categories: list[str],
    fallback_options: list[str],
    population: pd.DataFrame | None = None,
    user_key: pd.DataFrame | None = None,
) -> pd.DataFrame:
    records: list[dict] = []

    unknown = set(fallback_options) - SUPPORTED_FALLBACKS
    if unknown:
        raise ValueError(
            f"Unsupported fallback options: {sorted(unknown)}. "
            f"Supported values are: {sorted(SUPPORTED_FALLBACKS)}"
        )

    for country in sorted(regions["country"].unique()):
        country_regions = regions.loc[regions["country"] == country, "region"]
        region_index = pd.Index(country_regions.tolist(), name="region")
        country_sites = hotmaps[hotmaps["country"] == country]

        for category in categories:
            facilities = country_sites[country_sites["Subsector"] == category]
            exact_key = normalized_region_key(facilities, region_index)

            if float(exact_key.sum()) > 0:
                key = exact_key / exact_key.sum()
                source = "hotmaps_subsector"
                n_sites = int(len(facilities))
            else:
                key, source, n_sites = choose_fallback(
                    fallback_options=fallback_options,
                    country=country,
                    region_index=region_index,
                    country_sites=country_sites,
                    population=population,
                    user_key=user_key,
                )

            for region, value in key.items():
                records.append(
                    {
                        "country": country,
                        "region": region,
                        "spatial_category": category,
                        "key": float(value),
                        "source": source,
                        "n_sites": n_sites,
                    }
                )

    out = pd.DataFrame(records)
    sums = out.groupby(["country", "spatial_category"], observed=True)["key"].sum()
    if not np.allclose(sums.values, 1.0, atol=1e-9):
        bad = sums[~np.isclose(sums, 1.0, atol=1e-9)]
        raise ValueError("Spatial keys do not sum to one:\n" + bad.to_string())
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--regions", required=True)
    parser.add_argument("--hotmaps", required=True)
    parser.add_argument("--population")
    parser.add_argument("--user-key")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    cfg = config.get("spatial_disaggregation", {})

    region_id_column = cfg.get("region_id_column", "name")
    country_column = cfg.get("country_column")
    fallback_options = cfg.get(
        "fallback_options",
        ["generic_industry", "population", "uniform"],
    )
    if not isinstance(fallback_options, list) or not fallback_options:
        raise ValueError("spatial_disaggregation.fallback_options must be a non-empty list.")

    regions = read_regions(args.regions, region_id_column, country_column)
    hotmaps = read_hotmaps(args.hotmaps)
    hotmaps = assign_sites_to_regions(hotmaps, regions)

    population = None
    if args.population:
        population = read_generic_key(
            args.population,
            cfg.get("population", {}),
            default_source_name="population",
        )

    user_key = None
    if args.user_key:
        user_key = read_generic_key(
            args.user_key,
            cfg.get("user_key", {}),
            default_source_name="user_key",
        )

    categories = sorted(
        {
            "Iron and steel",
            "Cement",
            "Chemical industry",
            "Glass",
            "Paper and printing",
            "Non-ferrous metals",
            "Non-metallic mineral products",
            "Other non-classified",
        }
    )

    keys = build_keys(
        regions=regions,
        hotmaps=hotmaps,
        categories=categories,
        fallback_options=fallback_options,
        population=population,
        user_key=user_key,
    )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    keys.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()

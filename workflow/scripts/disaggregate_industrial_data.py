from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml

from build_spatial_distribution_keys import spatial_category


def attach_category(df: pd.DataFrame) -> pd.DataFrame:
    if "commodity" not in df.columns:
        raise ValueError("Input must contain a 'commodity' column.")

    df = df.copy()

    # route_production.csv may not carry the historical JRC sector code.
    # Use commodity-first mappings where they are unambiguous, otherwise
    # fall back to the sector code when it is available.
    commodity_map = {
        "STEEL": "Iron and steel",
        "HVC": "Chemical industry",
        "AMMONIA": "Chemical industry",
        "CHLORINE": "Chemical industry",
        "METHANOL": "Chemical industry",
        "OTHER_CHEMICALS": "Chemical industry",
        "PHARMACEUTICALS": "Chemical industry",
        "PHARM": "Chemical industry",
        "CEM": "Cement",
        "CEMENT": "Cement",
        "GLASS": "Glass",
        "PULP": "Paper and printing",
        "PAPER": "Paper and printing",
        "PRINT": "Paper and printing",
        "ALUMINA": "Non-ferrous metals",
        "ALUMINIUM": "Non-ferrous metals",
        "OTHER_NFM": "Non-ferrous metals",
    }

    categories = []
    has_sector = "sector" in df.columns
    for row in df.itertuples(index=False):
        commodity = str(getattr(row, "commodity"))
        if commodity in commodity_map:
            categories.append(commodity_map[commodity])
        elif has_sector:
            categories.append(
                spatial_category(str(getattr(row, "sector")), commodity)
            )
        else:
            categories.append("Other non-classified")

    df["spatial_category"] = categories
    return df


def _restrict_to_spatial_scope(
    df: pd.DataFrame,
    distribution_keys: pd.DataFrame,
) -> pd.DataFrame:
    """Keep only countries represented in the user's regional GeoJSON.

    The distribution-key table is built exclusively from regions in the
    user-provided GeoJSON. A national model may contain additional countries.
    Those countries are outside the spatial scope and are therefore omitted
    rather than assigned invented regions.
    """
    if "country" not in df.columns:
        raise ValueError("Input data must contain a 'country' column.")
    if "country" not in distribution_keys.columns:
        raise ValueError("Spatial distribution keys must contain a 'country' column.")

    spatial_countries = set(
        distribution_keys["country"].dropna().astype(str).str.upper().unique()
    )

    out = df.copy()
    out["country"] = out["country"].astype(str).str.upper()

    present_countries = set(out["country"].dropna().unique())
    omitted_countries = sorted(present_countries - spatial_countries)

    if omitted_countries:
        omitted_mask = ~out["country"].isin(spatial_countries)
        n_omitted = int(omitted_mask.sum())
        print(
            "Spatial disaggregation: skipping "
            f"{n_omitted} rows for countries not represented in the "
            "user GeoJSON: "
            + ", ".join(omitted_countries)
        )
        out = out.loc[~omitted_mask].copy()

    return out


def _filter_years(df: pd.DataFrame, years: list[int] | None) -> pd.DataFrame:
    """Restrict the spatial output to selected years before regional expansion."""
    if not years:
        return df
    if "year" not in df.columns:
        raise ValueError("A year filter was requested, but input has no 'year' column.")

    out = df.copy()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    available = set(out["year"].dropna().astype(int).unique())
    requested = {int(y) for y in years}
    missing = sorted(requested - available)
    if missing:
        print("Spatial disaggregation: requested years not available in input: " + ", ".join(map(str, missing)))

    out = out.loc[out["year"].isin(sorted(requested))].copy()
    return out


def disaggregate(
    df: pd.DataFrame,
    distribution_keys: pd.DataFrame,
    value_column: str,
    years: list[int] | None = None,
) -> pd.DataFrame:
    df = _filter_years(df, years)
    df = _restrict_to_spatial_scope(df, distribution_keys)
    df = attach_category(df)

    merged = df.merge(
        distribution_keys[
            ["country", "region", "spatial_category", "key", "source"]
        ],
        on=["country", "spatial_category"],
        how="left",
        validate="many_to_many",
    )

    # At this point every remaining country is represented in the GeoJSON.
    # Missing keys therefore indicate an actual category/key construction issue
    # and should remain a hard error.
    missing = merged.loc[
        merged["key"].isna(), ["country", "spatial_category"]
    ].drop_duplicates()
    if not missing.empty:
        raise ValueError(
            "Missing spatial keys for countries that are present in the GeoJSON:\n"
            + missing.to_string(index=False)
        )

    merged[value_column] = (
        pd.to_numeric(merged[value_column], errors="coerce") * merged["key"]
    )
    merged = merged.rename(
        columns={"key": "spatial_share", "source": "spatial_key_source"}
    )
    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--keys", required=True)
    parser.add_argument("--value-column", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    spatial_cfg = cfg.get("spatial_disaggregation", {})
    years = spatial_cfg.get("years")
    if years is not None:
        years = [int(y) for y in years]
        print("Spatial disaggregation: filtering to years: " + ", ".join(map(str, years)))
    else:
        print("Spatial disaggregation: no year filter configured; keeping all years.")

    # The detailed historical/future demand table deliberately contains mixed
    # metadata types in fields such as source_unit and Code. low_memory=False
    # prevents pandas' chunk-wise dtype inference warning while preserving them.
    df = pd.read_csv(args.input, low_memory=False)
    distribution_keys = pd.read_csv(args.keys, low_memory=False)

    if args.value_column not in df.columns:
        raise ValueError(
            f"Value column '{args.value_column}' not found in {args.input}."
        )

    out = disaggregate(df, distribution_keys, args.value_column, years=years)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()

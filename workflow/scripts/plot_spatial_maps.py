"""Map regional production and energy demand."""

import colorsys
import html
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pydeck as pdk

USE_TYPES = ["final_energy"]
MAX_PIE_SLICES = 10
PIE_RADIUS_DEGREES = 1.0


def _view_state(regions: gpd.GeoDataFrame) -> pdk.ViewState:
    minx, miny, maxx, maxy = regions.total_bounds
    lon = (minx + maxx) / 2
    lat = (miny + maxy) / 2
    span = max(maxx - minx, maxy - miny)
    zoom = 4.0 if span > 20 else 5.0 if span > 10 else 6.0
    return pdk.ViewState(longitude=lon, latitude=lat, zoom=zoom, pitch=0)


def _deck(layers, regions) -> pdk.Deck:
    return pdk.Deck(
        layers=layers,
        initial_view_state=_view_state(regions),
        map_provider="carto",
        map_style="light",
        tooltip={
            "html": "{tooltip}",
            "style": {"backgroundColor": "white", "color": "black"},
        },
    )


def _write_html(deck: pdk.Deck, path: Path, title: str, legend_html: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    deck.to_html(path, open_browser=False)
    text = path.read_text(encoding="utf-8")
    title_block = (
        '<div style="position:absolute;left:15px;top:15px;z-index:9999;'
        "background:white;padding:8px 11px;border-radius:4px;"
        'box-shadow:0 1px 5px rgba(0,0,0,.25);font-family:Arial;font-weight:600;">'
        + html.escape(title)
        + "</div>"
    )
    text = text.replace("<body>", "<body>" + title_block + legend_html, 1)
    path.write_text(text, encoding="utf-8")


def _palette(categories: list[str]) -> dict[str, list[int]]:
    colors = {}
    n = max(len(categories), 1)
    for i, category in enumerate(sorted(categories)):
        r, g, b = colorsys.hsv_to_rgb(i / n, 0.62, 0.82)
        colors[category] = [int(255 * r), int(255 * g), int(255 * b), 220]
    return colors


def _legend(colors: dict[str, list[int]], title: str) -> str:
    rows = []
    for category, color in colors.items():
        rows.append(
            '<div style="display:flex;align-items:center;margin:2px 0;">'
            f'<span style="width:11px;height:11px;background:rgb({color[0]},{color[1]},{color[2]});'
            'display:inline-block;margin-right:6px;border:1px solid #888;"></span>'
            f"<span>{html.escape(category)}</span></div>"
        )
    return (
        '<div style="position:absolute;right:15px;top:15px;z-index:9999;background:white;'
        "padding:8px 10px;border-radius:4px;box-shadow:0 1px 5px rgba(0,0,0,.25);"
        'font-family:Arial;font-size:11px;max-height:70vh;overflow:auto;">'
        f'<div style="font-weight:600;margin-bottom:5px;">{html.escape(title)}</div>'
        + "".join(rows)
        + "</div>"
    )


def _region_centres(regions: gpd.GeoDataFrame) -> pd.DataFrame:
    # representative_point stays inside polygons, which is useful for pies.
    projected = regions.to_crs("EPSG:3035")
    pts = gpd.GeoSeries(
        projected.geometry.representative_point(), crs=projected.crs
    ).to_crs("EPSG:4326")
    return pd.DataFrame(
        {"region": regions["region"].values, "lon": pts.x.values, "lat": pts.y.values}
    )


def _compress_categories(df: pd.DataFrame, category: str) -> pd.DataFrame:
    grouped = df.groupby(["region", category], as_index=False)["demand"].sum()
    totals = grouped.groupby(category)["demand"].sum().sort_values(ascending=False)
    keep = set(totals.head(MAX_PIE_SLICES - 1).index)
    grouped[category] = grouped[category].where(grouped[category].isin(keep), "OTHER")
    return grouped.groupby(["region", category], as_index=False)["demand"].sum()


def _wedge_polygon(
    lon: float, lat: float, radius_deg: float, start: float, end: float
) -> list[list[float]]:
    # Simple map-coordinate pie geometry. This mirrors the logic of matplotlib
    # Wedge: radius is a map distance, and angle is the category share.
    n = max(5, int(math.ceil(24 * (end - start) / (2 * math.pi))))
    angles = np.linspace(start, end, n + 1)
    # Correct longitude a little so the symbol stays approximately circular.
    cos_lat = max(math.cos(math.radians(lat)), 0.25)
    points = [[lon, lat]]
    for a in angles:
        points.append(
            [lon + radius_deg * math.cos(a) / cos_lat, lat + radius_deg * math.sin(a)]
        )
    points.append([lon, lat])
    return points


def _pie_records(
    grouped: pd.DataFrame,
    category_col: str,
    centres: pd.DataFrame,
    colors: dict[str, list[int]],
) -> list[dict]:
    totals = grouped.groupby("region")["demand"].sum()
    max_total = float(totals.max()) if len(totals) else 0.0
    if max_total <= 0:
        return []

    centre_lookup = centres.set_index("region")
    records = []

    for region, rg in grouped.groupby("region"):
        if region not in centre_lookup.index:
            continue
        total = float(rg["demand"].sum())
        if total <= 0:
            continue

        # Scale pie area with demand, independently of the demand units.
        radius = math.sqrt(total / max_total) * PIE_RADIUS_DEGREES
        lon = float(centre_lookup.at[region, "lon"])
        lat = float(centre_lookup.at[region, "lat"])

        angle = -math.pi / 2
        for row in rg.itertuples():
            value = float(getattr(row, "demand"))
            if value <= 0:
                continue
            category = str(getattr(row, category_col))
            share = value / total
            next_angle = angle + 2 * math.pi * share
            records.append(
                {
                    "region": str(region),
                    "category": category,
                    "value": value,
                    "total": total,
                    "share": 100 * share,
                    "polygon": _wedge_polygon(lon, lat, radius, angle, next_angle),
                    "color": colors[category],
                    "tooltip": (
                        f"<b>{html.escape(str(region))}</b><br/>"
                        f"{html.escape(category)}: {value:,.2f}<br/>"
                        f"Share: {100 * share:.1f}%<br/>"
                        f"Total: {total:,.2f}"
                    ),
                }
            )
            angle = next_angle

    return records


def _base_region_layer(regions: gpd.GeoDataFrame):
    base = regions.copy()
    base["tooltip"] = "<b>" + base["region"].astype(str) + "</b>"
    return pdk.Layer(
        "GeoJsonLayer",
        base.__geo_interface__,
        pickable=True,
        filled=True,
        stroked=True,
        get_fill_color=[235, 235, 235, 70],
        get_line_color=[90, 90, 90, 160],
        line_width_min_pixels=0.5,
    )


def make_energy_pie_maps(
    energy: pd.DataFrame,
    regions: gpd.GeoDataFrame,
    outdir: Path,
    energy_layer: str,
    include_plots: set[str],
) -> None:
    """Render selected energy pies for every regionalised year."""
    data = energy.loc[
        energy["energy_layer"].eq(energy_layer) & energy["use_type"].isin(USE_TYPES)
    ].copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data["demand"] = pd.to_numeric(data["demand"], errors="coerce").fillna(0.0)
    years = sorted(data["year"].dropna().astype(int).unique())
    centres = _region_centres(regions)

    sector_col = "sector_name" if "sector_name" in data.columns else "sector"
    specs = [
        (column, label)
        for column, label in [
            (sector_col, "sector"),
            ("commodity", "commodity"),
            ("carrier", "carrier"),
        ]
        if f"energy_by_{label}_map" in include_plots
    ]

    for year in years:
        year_data = data[data["year"] == year]
        for category_col, label in specs:
            if category_col not in year_data.columns:
                print(
                    f"Spatial maps: skipping {label}; column '{category_col}' missing."
                )
                continue
            grouped = _compress_categories(year_data, category_col)
            if grouped.empty or grouped["demand"].sum() <= 0:
                continue
            categories = sorted(grouped[category_col].astype(str).unique())
            colors = _palette(categories)
            records = _pie_records(grouped, category_col, centres, colors)
            if not records:
                continue

            print(
                f"Spatial maps: {label} pies for {year}; "
                f"largest pie radius = {PIE_RADIUS_DEGREES:g} map degrees."
            )

            pie_layer = pdk.Layer(
                "PolygonLayer",
                records,
                pickable=True,
                filled=True,
                stroked=True,
                get_polygon="polygon",
                get_fill_color="color",
                get_line_color=[255, 255, 255, 230],
                line_width_min_pixels=0.4,
            )
            deck = _deck([_base_region_layer(regions), pie_layer], regions)
            path = outdir / f"energy_demand_by_{label}_{year}.html"
            _write_html(
                deck,
                path,
                f"Energy demand by {label} — {year}",
                _legend(colors, label.capitalize()),
            )


def _choropleth_color(values: pd.Series) -> list[list[int]]:
    vals = pd.to_numeric(values, errors="coerce").fillna(0.0)
    vmax = float(vals.max()) if len(vals) else 0.0
    if vmax <= 0:
        return [[230, 230, 230, 100] for _ in vals]
    x = np.sqrt(np.clip(vals / vmax, 0, 1))
    return [[int(245 - 120 * v), int(240 - 90 * v), int(230 - 150 * v), 190] for v in x]


def make_production_maps(
    route_prod: pd.DataFrame, regions: gpd.GeoDataFrame, outdir: Path
) -> None:
    """Map production and route breakdowns for each commodity and year."""
    data = route_prod.copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    data["route_production"] = pd.to_numeric(
        data["route_production"], errors="coerce"
    ).fillna(0.0)
    years = sorted(data["year"].dropna().astype(int).unique())

    for year in years:
        year_data = data[data["year"] == year]
        for commodity, group in year_data.groupby("commodity"):
            if group["route_production"].sum() <= 0:
                continue
            total = group.groupby("region", as_index=False)["route_production"].sum()
            breakdown = group.groupby(["region", "production_route"], as_index=False)[
                "route_production"
            ].sum()
            breakdown = breakdown.sort_values(
                ["region", "route_production"], ascending=[True, False]
            )
            breakdown_text = (
                breakdown.groupby("region")
                .apply(
                    lambda x: "<br/>".join(
                        f"{r.production_route}: {r.route_production:,.2f}"
                        for r in x.itertuples()
                    ),
                    include_groups=False,
                )
                .rename("route_breakdown")
                .reset_index()
            )
            total = total.merge(breakdown_text, on="region", how="left")
            gdf = regions.merge(total, on="region", how="left")
            gdf["route_production"] = gdf["route_production"].fillna(0.0)
            gdf["route_breakdown"] = gdf["route_breakdown"].fillna("No production")
            gdf["fill_color"] = _choropleth_color(gdf["route_production"])
            gdf["tooltip"] = (
                "<b>"
                + gdf["region"].astype(str)
                + "</b><br/>"
                + f"{commodity}: "
                + gdf["route_production"].map(lambda x: f"{x:,.2f}")
                + "<br/>"
                + gdf["route_breakdown"]
            )
            layer = pdk.Layer(
                "GeoJsonLayer",
                gdf.__geo_interface__,
                pickable=True,
                filled=True,
                stroked=True,
                get_fill_color="properties.fill_color",
                get_line_color=[80, 80, 80, 180],
                line_width_min_pixels=0.5,
            )
            deck = _deck([layer], regions)
            _write_html(
                deck,
                outdir / f"production_{commodity}_{year}.html",
                f"{commodity} production — {year}",
            )


def _read_regional_data(path) -> pd.DataFrame:
    data = pd.read_parquet(path)
    # The spatial merge suffixes the regional key when a national region exists.
    if "region_y" in data.columns:
        data["region"] = data["region_y"]
    data["region"] = data["region"].astype(str)
    return data


def main() -> None:
    """Render selected spatial maps."""
    outdir = Path(snakemake.output[0]).parent
    outdir.mkdir(parents=True, exist_ok=True)
    for path in outdir.glob("*.html"):
        path.unlink()

    selected = set(snakemake.params.include_plots)
    if not any(name.endswith("_map") for name in selected):
        return
    regions = gpd.read_parquet(snakemake.input.regions).to_crs("EPSG:4326")
    if "production_map" in selected:
        make_production_maps(
            _read_regional_data(snakemake.input.route_production), regions, outdir
        )
    if any(
        name.startswith("energy_by_") and name.endswith("_map") for name in selected
    ):
        make_energy_pie_maps(
            _read_regional_data(snakemake.input.energy_demand),
            regions,
            outdir,
            snakemake.params.energy_layer,
            selected,
        )


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main()

"""Plot national production and energy demand."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px


def _write_html(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(path, include_plotlyjs="cdn", full_html=True)


def plot_production_overview(projected: pd.DataFrame, output_dir: Path) -> None:
    """Plot commodity production relative to its reference year."""
    if projected.empty:
        return

    grouped = (
        projected.groupby(["commodity", "year"], as_index=False)["production"]
        .sum()
        .sort_values(["commodity", "year"])
    )

    ref = (
        grouped.sort_values("year")
        .groupby("commodity", as_index=False)
        .first()[["commodity", "production"]]
        .rename(columns={"production": "reference_production"})
    )
    grouped = grouped.merge(ref, on="commodity", how="left")
    grouped = grouped[grouped["reference_production"] > 0].copy()
    grouped["production_index"] = (
        100.0 * grouped["production"] / grouped["reference_production"]
    )

    fig = px.line(
        grouped,
        x="year",
        y="production_index",
        color="commodity",
        markers=False,
        labels={
            "year": "Year",
            "production_index": "Production index (reference year = 100)",
            "commodity": "Commodity",
        },
        title="Industrial production projections",
    )
    fig.add_hline(y=100, line_dash="dot")
    fig.update_layout(hovermode="x unified")
    _write_html(fig, output_dir / "production_overview.html")


def plot_route_production(routes: pd.DataFrame, output_dir: Path) -> None:
    """Plot commodities with multiple active production routes."""
    if routes.empty:
        return

    route_counts = (
        routes[routes["route_share"] > 0]
        .groupby("commodity")["production_route"]
        .nunique()
    )
    commodities = route_counts[route_counts > 1].index

    for commodity in commodities:
        data = routes[routes["commodity"] == commodity].copy()
        data = (
            data.groupby(["year", "production_route"], as_index=False)[
                "route_production"
            ]
            .sum()
            .sort_values("year")
        )

        fig = px.area(
            data,
            x="year",
            y="route_production",
            color="production_route",
            labels={
                "year": "Year",
                "route_production": "Production",
                "production_route": "Production route",
            },
            title=f"{commodity} production by route",
        )
        fig.update_layout(hovermode="x unified")
        _write_html(fig, output_dir / f"production_routes_{commodity}.html")


def _filter_energy(demand: pd.DataFrame, energy_layer: str) -> pd.DataFrame:
    return demand.loc[
        demand["energy_layer"].eq(energy_layer) & demand["use_type"].eq("final_energy")
    ].copy()


def plot_energy_by_carrier(
    demand: pd.DataFrame, output_dir: Path, energy_layer: str
) -> None:
    """Plot final energy demand for the selected energy layer."""
    data = _filter_energy(demand, energy_layer)
    if data.empty:
        return

    data = (
        data.groupby(["year", "carrier"], as_index=False)["demand"]
        .sum()
        .sort_values("year")
    )

    fig = px.area(
        data,
        x="year",
        y="demand",
        color="carrier",
        labels={"year": "Year", "demand": "Energy demand", "carrier": "Carrier"},
        title=f"Industrial energy demand by carrier ({energy_layer})",
    )
    fig.update_layout(hovermode="x unified")
    _write_html(fig, output_dir / "energy_demand_by_carrier.html")


def plot_energy_by_commodity(
    demand: pd.DataFrame, output_dir: Path, energy_layer: str
) -> None:
    """Plot final energy demand for the selected energy layer."""
    data = _filter_energy(demand, energy_layer)
    if data.empty:
        return

    data = (
        data.groupby(["year", "commodity"], as_index=False)["demand"]
        .sum()
        .sort_values("year")
    )

    fig = px.line(
        data,
        x="year",
        y="demand",
        color="commodity",
        labels={"year": "Year", "demand": "Energy demand", "commodity": "Commodity"},
        title=f"Industrial energy demand by commodity ({energy_layer})",
    )
    fig.update_layout(hovermode="x unified")
    _write_html(fig, output_dir / "energy_demand_by_commodity.html")


def _clean_standard_outputs(output_dir: Path) -> None:
    """Remove generated plots before rendering."""
    fixed = [
        output_dir / "production_overview.html",
        output_dir / "energy_demand_by_carrier.html",
        output_dir / "energy_demand_by_commodity.html",
    ]
    for path in fixed:
        if path.exists():
            path.unlink()
    for path in output_dir.glob("production_routes_*.html"):
        path.unlink()


def main() -> None:
    """Render selected plots for all modelled countries and commodities."""
    output_dir = Path(snakemake.output[0]).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    _clean_standard_outputs(output_dir)

    selected = set(snakemake.params.include_plots)
    if "production_overview" in selected:
        plot_production_overview(
            pd.read_parquet(snakemake.input.projected_production), output_dir
        )
    if "production_route" in selected:
        plot_route_production(
            pd.read_parquet(snakemake.input.route_production), output_dir
        )
    energy_plots = {
        "energy_by_carrier": plot_energy_by_carrier,
        "energy_by_commodity": plot_energy_by_commodity,
    }
    if selected & energy_plots.keys():
        demand = pd.read_parquet(snakemake.input.energy_demand)
        for name, plot in energy_plots.items():
            if name in selected:
                plot(demand, output_dir, snakemake.params.energy_layer)


if __name__ == "__main__":
    sys.stderr = open(snakemake.log[0], "w", buffering=1)
    main()

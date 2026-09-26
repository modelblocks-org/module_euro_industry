"""Transform projected industrial production into future process-level demand.

The engine combines four layers:

1. Projected commodity production.
2. Historical route/process FEC and UED intensities.
3. Process transformations for existing routes.
4. New production routes composed of intensity-based processes.

Historical process transformations are applied in UED space. New production
routes are intensity based because they have no historical UED baseline.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml


HISTORICAL_TECH = "HISTORICAL"


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _interp(year: int, reference_year: int, reference_value: float, anchors: dict) -> float:
    points = {int(reference_year): float(reference_value)}
    points.update({int(y): float(v) for y, v in (anchors or {}).items()})
    xs = np.array(sorted(points), dtype=int)
    ys = np.array([points[x] for x in xs], dtype=float)
    if len(xs) == 1:
        return float(ys[0])
    if year < xs.min() or year > xs.max():
        raise ValueError(f"Year {year} outside interpolation range {xs.min()}-{xs.max()}.")
    return float(np.interp(year, xs, ys))


def _validate_shares(shares: dict[str, float], label: str, tol: float = 1e-6) -> None:
    if any(v < -tol for v in shares.values()):
        raise ValueError(f"Negative share in {label}: {shares}")
    total = sum(shares.values())
    if not np.isclose(total, 1.0, atol=tol):
        raise ValueError(f"Shares in {label} sum to {total:.8f}, expected 1.0: {shares}")


def historical_route_shares(
    historical_production: pd.DataFrame,
    reference_year: int,
) -> dict[tuple[str, str], dict[str, float]]:
    data = historical_production.loc[
        historical_production["year"].astype(int).eq(reference_year)
    ].copy()
    data["production"] = pd.to_numeric(data["production"], errors="raise")
    grouped = data.groupby(["country", "commodity", "production_route"], as_index=False)[
        "production"
    ].sum()
    result: dict[tuple[str, str], dict[str, float]] = {}
    for (country, commodity), group in grouped.groupby(["country", "commodity"]):
        total = group["production"].sum()
        if total <= 0:
            continue
        result[(country, commodity)] = {
            str(r.production_route): float(r.production / total)
            for r in group.itertuples(index=False)
        }
    return result


def route_share_curve(
    country: str,
    commodity: str,
    years: Iterable[int],
    reference_year: int,
    historical_shares: dict[str, float],
    scenario_route_shares: dict,
) -> pd.DataFrame:
    """Build annual production-route shares for one country/commodity.

    If the commodity has no entry in ``scenario_route_shares``, its historical
    route mix is preserved unchanged for every projected year. Only commodities
    explicitly listed in the scenario are transformed.
    """
    scenario = scenario_route_shares.get(commodity)

    # No route transformation requested: preserve the historical route mix.
    if not scenario:
        if not historical_shares:
            raise ValueError(
                f"Cannot preserve route mix for {country}/{commodity}: "
                "no historical route shares are available."
            )
        rows = []
        _validate_shares(
            historical_shares,
            f"historical route shares {country}/{commodity}",
            tol=1e-5,
        )
        for year in years:
            for route, share in historical_shares.items():
                rows.append(
                    {
                        "country": country,
                        "commodity": commodity,
                        "year": int(year),
                        "production_route": route,
                        "route_share": float(share),
                        "route_share_source": "historical",
                    }
                )
        return pd.DataFrame(rows)

    # Route transformation requested: interpolate from the historical route mix
    # at the reference year to the user-supplied scenario anchors.
    all_routes = sorted(set(historical_shares) | set(scenario))
    if not all_routes:
        raise ValueError(f"No production routes available for {country}/{commodity}.")

    anchor_years = sorted({int(y) for route in scenario.values() for y in (route or {})})
    for anchor in anchor_years:
        anchor_shares = {}
        for route in all_routes:
            anchors = scenario.get(route, {}) or {}
            if str(anchor) in anchors:
                anchor_shares[route] = float(anchors[str(anchor)])
            elif anchor in anchors:
                anchor_shares[route] = float(anchors[anchor])
            else:
                raise ValueError(
                    f"Route '{route}' has no share for anchor year {anchor} in commodity {commodity}. "
                    "All routes must be specified at every route-share anchor year."
                )
        _validate_shares(anchor_shares, f"{commodity}/{anchor}")

    rows = []
    for year in years:
        shares = {}
        for route in all_routes:
            ref = historical_shares.get(route, 0.0)
            shares[route] = _interp(
                int(year), reference_year, ref, scenario.get(route, {}) or {}
            )
        _validate_shares(shares, f"{country}/{commodity}/{year}", tol=1e-5)
        for route, share in shares.items():
            rows.append(
                {
                    "country": country,
                    "commodity": commodity,
                    "year": int(year),
                    "production_route": route,
                    "route_share": share,
                    "route_share_source": "scenario",
                }
            )
    return pd.DataFrame(rows)


def build_route_production(
    projected_production: pd.DataFrame,
    historical_production: pd.DataFrame,
    reference_year: int,
    scenario_route_shares: dict,
) -> pd.DataFrame:
    """Allocate projected commodity production across production routes.

    Rules:
    - Commodity in ``scenario_route_shares``: use the scenario trajectory,
      interpolated from the historical reference-year mix.
    - Commodity not in ``scenario_route_shares``: preserve the historical mix.
    - If no historical route information exists and no route transformation is
      requested, fall back to ``BASE_ROUTE = 1``. This covers proxy/aggregated
      historical commodities for which route detail is unavailable.
    - If a route transformation is requested but historical route information
      is missing, fail explicitly because the reference-year route mix is
      required for interpolation.
    """
    hist_shares = historical_route_shares(historical_production, reference_year)
    frames = []

    for (country, commodity), group in projected_production.groupby(
        ["country", "commodity"]
    ):
        years = sorted(group["year"].astype(int).unique())
        shares = hist_shares.get((country, commodity), {})
        has_route_scenario = bool(scenario_route_shares.get(commodity))

        # A country/commodity with zero projected production does not need a
        # production-route allocation. This is common for commodities such as
        # steel in countries with no reference-year production. Since the
        # production projection is relative to the historical baseline, a zero
        # reference value remains zero in all projected years unless the
        # projection framework is explicitly extended to allow absolute entries.
        production_values = pd.to_numeric(group["production"], errors="coerce").fillna(0.0)
        if production_values.abs().max() <= 1e-12:
            continue

        if not shares:
            if has_route_scenario:
                commodity_scenario = scenario_route_shares.get(commodity, {}) or {}

                # Calibrated/aggregated commodities such as HVC may exist in the
                # historical commodity table without an explicit route record.
                # If the scenario explicitly contains BASE_ROUTE, it provides an
                # unambiguous incumbent route: assume 100% BASE_ROUTE in the
                # reference year and let the scenario phase in the new routes.
                #
                # We intentionally do NOT apply this fallback to commodities
                # such as STEEL, where multiple historical routes (e.g. BF_BOF
                # and EAF) may exist and inventing a reference mix would be wrong.
                if "BASE_ROUTE" in commodity_scenario:
                    shares = {"BASE_ROUTE": 1.0}
                else:
                    raise ValueError(
                        f"No historical route shares found for {country}/{commodity}, "
                        "but a route transformation is defined for this commodity. "
                        "A reference-year route mix is required unless the scenario "
                        "contains an explicit BASE_ROUTE incumbent."
                    )
            else:
                # No transformation is requested and the historical source has no
                # route detail. Treat the commodity as a single incumbent route.
                shares = {"BASE_ROUTE": 1.0}

        curve = route_share_curve(
            country=country,
            commodity=commodity,
            years=years,
            reference_year=reference_year,
            historical_shares=shares,
            scenario_route_shares=scenario_route_shares,
        )

        # Make fallbacks explicit in the output for traceability.
        if (country, commodity) not in hist_shares:
            if has_route_scenario and "BASE_ROUTE" in (scenario_route_shares.get(commodity, {}) or {}):
                curve["route_share_source"] = "scenario_from_base_route_fallback"
            elif not has_route_scenario:
                curve["route_share_source"] = "fallback_base_route"

        base = group[["country", "commodity", "year", "production", "unit"]].copy()
        merged = curve.merge(base, on=["country", "commodity", "year"], how="left")
        merged["route_production"] = merged["production"] * merged["route_share"]
        frames.append(merged)

    if not frames:
        return pd.DataFrame(
            columns=[
                "country", "commodity", "year", "production_route",
                "route_share", "route_share_source", "production",
                "unit", "route_production",
            ]
        )

    return pd.concat(frames, ignore_index=True)

def historical_route_intensities(
    historical_energy: pd.DataFrame,
    historical_production: pd.DataFrame,
    reference_year: int,
) -> pd.DataFrame:
    """Build historical route/process energy intensities.

    Only country/commodity/route combinations with *positive* historical
    production are modelled. JRC-IDEES can contain energy-only or aggregate
    rows (for example TOTAL or activities for which this model has no physical
    production basis). Those rows cannot be converted to an energy intensity
    and are therefore ignored rather than treated as an error.

    This also handles the case where a sector/commodity is absent in a country:
    no production means no route intensity and consequently no future demand is
    generated for that country/commodity unless a separately defined new route
    is supplied with positive projected production.
    """
    keys = ["country", "commodity", "production_route"]

    energy = historical_energy.loc[
        historical_energy["year"].astype(int).eq(reference_year)
    ].copy()
    production = historical_production.loc[
        historical_production["year"].astype(int).eq(reference_year)
    ].copy()

    production["production"] = pd.to_numeric(production["production"], errors="coerce")
    route_prod = (
        production.groupby(keys, as_index=False, dropna=False)["production"]
        .sum()
        .rename(columns={"production": "reference_route_production"})
    )

    # A route with no positive production cannot provide a meaningful
    # demand-per-production intensity. Keep only modelled incumbent routes.
    route_prod = route_prod.loc[
        route_prod["reference_route_production"].notna()
        & route_prod["reference_route_production"].gt(0)
    ].copy()

    modelled_keys = route_prod[keys].drop_duplicates()
    unmatched = energy.merge(
        modelled_keys.assign(_modelled=True),
        on=keys,
        how="left",
    )
    unmatched = unmatched.loc[unmatched["_modelled"].isna(), keys].drop_duplicates()
    if not unmatched.empty:
        print(
            "Ignoring historical energy rows without positive matching "
            "route production (these cannot form production-based intensities):\n"
            + unmatched.to_string(index=False)
        )

    # Inner join is deliberate: only energy demand associated with an actually
    # modelled historical production route is carried into future intensities.
    energy = energy.merge(
        route_prod,
        on=keys,
        how="inner",
        validate="many_to_one",
    )

    energy["demand"] = pd.to_numeric(energy["demand"], errors="raise")
    energy["intensity_per_production_unit"] = (
        energy["demand"] / energy["reference_route_production"]
    )
    return energy


def _transformation_curve(
    transformation: dict,
    years: Iterable[int],
    reference_year: int,
) -> dict[int, dict[str, float]]:
    techs = transformation["technologies"]
    all_techs = list(techs)
    if HISTORICAL_TECH not in all_techs:
        all_techs = [HISTORICAL_TECH] + all_techs

    # Validate explicit anchors.
    anchors = sorted({int(y) for values in techs.values() for y in (values or {})})
    for anchor in anchors:
        values = {}
        for tech in all_techs:
            mapping = techs.get(tech, {}) or {}
            if str(anchor) in mapping:
                values[tech] = float(mapping[str(anchor)])
            elif anchor in mapping:
                values[tech] = float(mapping[anchor])
            else:
                proc_label = transformation.get('process') or transformation.get('processes')
                raise ValueError(
                    f"Technology '{tech}' missing share for {transformation['commodity']}/"
                    f"{transformation['production_route']}/{proc_label} anchor {anchor}."
                )
        _validate_shares(values, f"process transformation {anchor}")

    curves = {}
    for year in years:
        values = {}
        for tech in all_techs:
            ref = 1.0 if tech == HISTORICAL_TECH else 0.0
            values[tech] = _interp(int(year), reference_year, ref, techs.get(tech, {}) or {})
        _validate_shares(values, f"process transformation {year}", tol=1e-5)
        curves[int(year)] = values
    return curves


def _selected_processes(tr: dict) -> list[str]:
    """Return process selector as a normalized list.

    A transformation may use either:
      process: LOW_ENTHALPY_HEAT
    or:
      processes:
        - LOW_ENTHALPY_HEAT
        - PAPER_MACHINE
    """
    if tr.get("processes") is not None:
        processes = tr["processes"]
        if isinstance(processes, str):
            processes = [processes]
        processes = [str(p) for p in processes]
    elif tr.get("process") is not None:
        processes = [str(tr["process"])]
    else:
        raise ValueError(
            f"Process transformation for {tr.get('commodity')}/"
            f"{tr.get('production_route')} must define 'process' or 'processes'."
        )

    if not processes:
        raise ValueError("Process transformation contains an empty process selector.")
    return processes


def _value_selector(series: pd.Series, selector) -> pd.Series:
    """Match an exact value, a list of values, or the wildcard ``*``."""
    if selector is None or selector == "*":
        return pd.Series(True, index=series.index)
    if isinstance(selector, (list, tuple, set)):
        values = [str(v) for v in selector]
        if "*" in values:
            return pd.Series(True, index=series.index)
        return series.astype(str).isin(values)
    return series.astype(str).eq(str(selector))


def _selector_mask(df: pd.DataFrame, tr: dict) -> pd.Series:
    processes = _selected_processes(tr)
    process_mask = pd.Series(True, index=df.index) if "*" in processes else df["process"].astype(str).isin(processes)
    mask = (
        _value_selector(df["commodity"], tr.get("commodity", "*"))
        & _value_selector(df["production_route"], tr.get("production_route", "*"))
        & process_mask
    )
    if tr.get("use_type"):
        mask &= _value_selector(df["use_type"], tr["use_type"])
    if tr.get("countries"):
        mask &= _value_selector(df["country"], tr["countries"])
    return mask


def apply_process_transformations(
    existing_demand: pd.DataFrame,
    transformations: list[dict],
    processes: dict,
    reference_year: int,
) -> pd.DataFrame:
    out = existing_demand.copy()

    for tr in transformations:
        mask = _selector_mask(out, tr)
        selected = out.loc[mask].copy()
        if selected.empty:
            processes_selected = _selected_processes(tr)
            print(
                "WARNING: process transformation matched no historical rows; skipping: "
                f"{tr['commodity']}/{tr['production_route']}/{processes_selected}"
            )
            continue

        years = sorted(selected["year"].astype(int).unique())
        curves = _transformation_curve(tr, years, reference_year)
        generated = []

        # Remove all selected rows; rebuild historical remainder and replacements.
        out = out.loc[~mask].copy()
        group_cols = ["country", "commodity", "production_route", "process", "year"]
        for group_key, group in selected.groupby(group_cols, dropna=False):
            country, commodity, production_route, process_name, year = group_key
            shares = curves[int(year)]
            hist_share = shares.get(HISTORICAL_TECH, 0.0)

            ued = group.loc[group["energy_layer"].eq("UED"), "demand"].sum()
            has_replacement = any(
                shares.get(t, 0) > 0 for t in shares if t != HISTORICAL_TECH
            )

            # A wildcard transformation can legitimately select a process that is
            # present in the source structure but has zero useful-energy demand for
            # a particular country/year. There is nothing to transform in that case.
            # Preserve the original rows unchanged instead of failing or scaling them
            # by the scenario technology shares.
            if ued <= 0 and has_replacement:
                skipped = group.copy()
                skipped["technology_scenario"] = HISTORICAL_TECH
                skipped["technology_share"] = 1.0
                skipped["transformation_source"] = "process_transformation_skipped_zero_ued"
                generated.append(skipped)
                print(
                    "WARNING: skipping process transformation with no positive UED: "
                    f"{country}/{commodity}/{production_route}/{process_name}/{year}"
                )
                continue

            # Historical remainder keeps the full original FEC/UED/carrier structure.
            if hist_share > 0:
                hist = group.copy()
                hist["demand"] *= hist_share
                hist["technology_scenario"] = HISTORICAL_TECH
                hist["technology_share"] = hist_share
                hist["transformation_source"] = "process_transformation"
                generated.append(hist)

            template = group.iloc[0].to_dict()
            for tech, share in shares.items():
                if tech == HISTORICAL_TECH or share <= 0:
                    continue
                definition = processes.get(tech)
                if not definition:
                    raise ValueError(f"Undefined process technology '{tech}'.")
                if "efficiency" not in definition or "carriers" not in definition:
                    raise ValueError(
                        f"Replacement process '{tech}' must define efficiency and carriers."
                    )
                eff = float(definition["efficiency"])
                # ``efficiency`` is a generic useful-energy/FEC conversion factor.
                # For heat pumps it is a COP and can therefore exceed 1.
                if not 0 < eff <= 10:
                    raise ValueError(f"Invalid efficiency/COP for {tech}: {eff}")
                carrier_defs = definition["carriers"]
                carrier_shares = {c: float(v["share"] if isinstance(v, dict) else v) for c, v in carrier_defs.items()}
                _validate_shares(carrier_shares, f"carrier shares of {tech}")

                tech_ued = ued * share
                # One synthetic UED bookkeeping row.
                ued_row = dict(template)
                ued_row.update(
                    {
                        "technology": tech,
                        "technology_scenario": tech,
                        "technology_share": share,
                        "carrier": "USEFUL_ENERGY",
                        "energy_layer": "UED",
                        "demand": tech_ued,
                        "source": "scenario_process",
                        "source_note": f"UED allocated to replacement technology {tech}.",
                        "transformation_source": "process_transformation",
                    }
                )
                generated.append(pd.DataFrame([ued_row]))

                fec_total = tech_ued / eff
                for carrier, cshare in carrier_shares.items():
                    fec_row = dict(template)
                    fec_row.update(
                        {
                            "technology": tech,
                            "technology_scenario": tech,
                            "technology_share": share,
                            "carrier": carrier,
                            "energy_layer": "FEC",
                            "demand": fec_total * cshare,
                            "source": "scenario_process",
                            "source_note": f"Replacement technology {tech}, efficiency={eff}.",
                            "transformation_source": "process_transformation",
                        }
                    )
                    generated.append(pd.DataFrame([fec_row]))

        if generated:
            out = pd.concat([out] + generated, ignore_index=True, sort=False)

    return out


def build_existing_route_demand(
    route_production: pd.DataFrame,
    historical_intensity: pd.DataFrame,
) -> pd.DataFrame:
    new_route_pairs = set()
    # Existing routes are simply those present in historical intensity.
    existing_keys = historical_intensity[["country", "commodity", "production_route"]].drop_duplicates()
    rp = route_production.merge(
        existing_keys.assign(_existing=True),
        on=["country", "commodity", "production_route"],
        how="left",
    )
    rp = rp.loc[rp["_existing"].eq(True)].drop(columns="_existing")

    merged = rp.merge(
        historical_intensity,
        on=["country", "commodity", "production_route"],
        how="left",
        suffixes=("", "_hist"),
    )
    merged["demand"] = merged["route_production"] * merged["intensity_per_production_unit"]
    if "unit_hist" in merged.columns:
        merged["unit"] = merged["unit_hist"]
    merged["technology_scenario"] = HISTORICAL_TECH
    merged["technology_share"] = 1.0
    merged["transformation_source"] = "historical_intensity"
    # The target year comes from route production, not the historical record.
    if "year_hist" in merged.columns:
        merged.drop(columns=["year_hist"], inplace=True)
    return merged


def _intensity_entries(definition: dict) -> list[tuple[str, float, str]]:
    result = []
    for carrier, raw in definition.get("intensities", {}).items():
        if isinstance(raw, dict):
            value = float(raw["value"])
            use_type = raw.get("use_type", "final_energy")
        else:
            value = float(raw)
            use_type = "final_energy"
        result.append((str(carrier), value, str(use_type)))
    return result


def build_new_route_demand(
    route_production: pd.DataFrame,
    route_definitions: dict,
    processes: dict,
    historical_intensity: pd.DataFrame,
) -> pd.DataFrame:
    frames = []
    for route_name, route_def in route_definitions.items():
        commodity = route_def["commodity"]
        rp = route_production.loc[
            route_production["commodity"].eq(commodity)
            & route_production["production_route"].eq(route_name)
            & route_production["route_production"].gt(0)
        ].copy()
        if rp.empty:
            continue
        for process_name in route_def.get("processes", []):
            process_def = processes.get(process_name)
            if not process_def:
                raise ValueError(f"New route '{route_name}' references undefined process '{process_name}'.")
            entries = _intensity_entries(process_def)
            if not entries:
                raise ValueError(
                    f"New-route process '{process_name}' must define intensities in MWh/t product."
                )
            for carrier, intensity, use_type in entries:
                rows = rp.copy()
                # production is expected in kt/a: kt * MWh/t = GWh; /1000 = TWh.
                units = rows["unit"].astype(str)
                bad = ~units.str.contains("kt", case=False, na=False)
                if bad.any():
                    raise ValueError(
                        f"New route {route_name} requires mass production in kt/a; got units "
                        f"{sorted(units[bad].unique())}."
                    )
                rows["sector"] = None
                rows["sector_name"] = None
                rows["activity"] = route_name
                rows["process"] = process_name
                rows["technology"] = process_name
                rows["technology_scenario"] = process_name
                rows["technology_share"] = 1.0
                rows["carrier"] = carrier
                rows["energy_layer"] = "FEC"
                rows["use_type"] = use_type
                rows["demand"] = rows["route_production"] * intensity / 1000.0
                rows["unit"] = "TWh/a"
                rows["source"] = "new_production_route"
                rows["source_note"] = f"{intensity} MWh/t product"
                rows["transformation_source"] = "new_production_route"
                frames.append(rows)

        # A new route can inherit selected historical use types (most notably
        # chemical feedstocks) from an incumbent route. This allows process
        # energy to change without silently deleting material/feedstock demand.
        inherit = route_def.get("inherit_use_types_from")
        if inherit:
            source_route = str(inherit["production_route"])
            use_types = inherit.get("use_types", ["feedstock"])
            if isinstance(use_types, str):
                use_types = [use_types]
            use_types = [str(u) for u in use_types]

            inherited = historical_intensity.loc[
                historical_intensity["commodity"].eq(commodity)
                & historical_intensity["production_route"].eq(source_route)
                & historical_intensity["use_type"].astype(str).isin(use_types)
            ].copy()

            if inherited.empty:
                print(
                    f"WARNING: new route {route_name} requested inherited use types "
                    f"{use_types} from {source_route}, but no matching historical "
                    "intensities were found."
                )
            else:
                inherited = rp.merge(
                    inherited,
                    on=["country", "commodity"],
                    how="inner",
                    suffixes=("", "_hist"),
                )
                if not inherited.empty:
                    inherited["production_route"] = route_name
                    inherited["activity"] = route_name
                    inherited["route_share"] = inherited["route_share"]
                    inherited["route_production"] = inherited["route_production"]
                    inherited["demand"] = (
                        inherited["route_production"]
                        * inherited["intensity_per_production_unit"]
                    )
                    if "unit_hist" in inherited.columns:
                        inherited["unit"] = inherited["unit_hist"]
                    inherited["technology_scenario"] = "INHERITED"
                    inherited["technology_share"] = 1.0
                    inherited["source"] = "new_production_route_inherited"
                    inherited["source_note"] = (
                        f"Inherited {','.join(use_types)} intensity from "
                        f"{source_route}."
                    )
                    inherited["transformation_source"] = "new_production_route"
                    if "year_hist" in inherited.columns:
                        inherited.drop(columns=["year_hist"], inplace=True)
                    frames.append(inherited)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def transform_demand(
    projected_production_path: str | Path,
    historical_production_path: str | Path,
    historical_energy_path: str | Path,
    config_path: str | Path,
    technologies_path: str | Path,
    scenario_path: str | Path,
    output_demand_path: str | Path,
    output_route_production_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = load_yaml(config_path)
    reference_year = int(config["historical_calibration"]["reference_year"])
    technologies = load_yaml(technologies_path)
    scenario = load_yaml(scenario_path)
    processes = technologies.get("processes", {}) or {}
    route_definitions = technologies.get("production_routes", {}) or {}
    transformations = scenario.get("process_transformations", []) or []
    route_shares = scenario.get("route_shares", {}) or {}

    projected = pd.read_csv(projected_production_path)
    hist_prod = pd.read_csv(historical_production_path)
    hist_energy = pd.read_csv(historical_energy_path)

    route_production = build_route_production(
        projected, hist_prod, reference_year, route_shares
    )
    hist_intensity = historical_route_intensities(hist_energy, hist_prod, reference_year)
    existing = build_existing_route_demand(route_production, hist_intensity)
    existing = apply_process_transformations(existing, transformations, processes, reference_year)
    new = build_new_route_demand(
        route_production, route_definitions, processes, hist_intensity
    )

    demand = pd.concat([existing, new], ignore_index=True, sort=False) if not new.empty else existing
    preferred = [
        "country", "year", "sector", "sector_name", "commodity", "production_route",
        "route_share", "route_production", "activity", "process", "technology",
        "technology_scenario", "technology_share", "carrier", "use_type", "energy_layer",
        "demand", "unit", "source", "source_note", "transformation_source",
    ]
    columns = [c for c in preferred if c in demand.columns] + [c for c in demand.columns if c not in preferred]
    demand = demand[columns]
    demand.sort_values(
        [c for c in ["country", "commodity", "year", "production_route", "process", "energy_layer", "carrier"] if c in demand.columns],
        inplace=True,
    )

    output_demand_path = Path(output_demand_path)
    output_route_production_path = Path(output_route_production_path)
    output_demand_path.parent.mkdir(parents=True, exist_ok=True)
    output_route_production_path.parent.mkdir(parents=True, exist_ok=True)
    demand.to_csv(output_demand_path, index=False, float_format="%.8f")
    route_production.to_csv(output_route_production_path, index=False, float_format="%.8f")
    return demand, route_production


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--projected-production", required=True)
    parser.add_argument("--historical-production", required=True)
    parser.add_argument("--historical-energy", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--technologies", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output-demand", required=True)
    parser.add_argument("--output-route-production", required=True)
    args = parser.parse_args()

    transform_demand(
        args.projected_production,
        args.historical_production,
        args.historical_energy,
        args.config,
        args.technologies,
        args.scenario,
        args.output_demand,
        args.output_route_production,
    )

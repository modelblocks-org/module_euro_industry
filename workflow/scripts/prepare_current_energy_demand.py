"""Prepare hierarchical historical industrial energy demand from JRC-IDEES.

The output deliberately stays close to the JRC-IDEES Industry workbooks:

* ``energy_layer`` distinguishes final-energy consumption (FEC) from useful-
  energy demand (UED).
* ``use_type`` distinguishes ordinary energy use from non-energy/feedstock use.
* JRC process, technology and carrier codes are preserved without fuel
  aggregation.
* Canonical activity/commodity/production-route labels are added only to make
  later route and process substitutions easier.

JRC anomaly: chemical feedstock/non-energy rows are available in the FEC data,
but corresponding coded rows can be absent from UED. For these rows only, the
FEC observation is copied into the UED layer. This is equivalent to UED=FEC for
feedstocks and avoids silently dropping feedstock from efficiency-ready data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import warnings

import country_converter as coco
import numpy as np
import pandas as pd
import yaml

from _industry_schema import (
    CHEMICAL_SCHEMA,
    COKE_CARRIERS,
    JRC_CODE_COLUMNS,
    JRC_INDUSTRY_SHEETS,
    JRC_NAMES,
    PROCESS_MAPPING,
    SECTOR_NAMES,
    schema_for_jrc_subsector,
)

KTOE_TO_TWH = 0.011630
ENERGY_LAYERS = ("FEC", "UED")


def _clean_code_part(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value if value and value.lower() != "nan" else None


def _year_column(df: pd.DataFrame, year: int, sheet: str, file_path: Path):
    if year in df.columns:
        return year
    candidates = {int(c): c for c in df.columns if isinstance(c, (int, float))}
    if year not in candidates:
        raise ValueError(f"Year {year} not found in sheet '{sheet}' of {file_path}.")
    return candidates[year]


def _normalize_process_fields(data: pd.DataFrame) -> pd.DataFrame:
    """Expose normalized process/technology while retaining raw JRC fields."""
    data = data.copy()

    # In the earlier JRC parser GENERIC rows use the process code as the
    # effective technology. Preserve that behaviour while keeping raw fields.
    technology = data["jrc_process"].copy()
    technology = technology.where(technology.notna(), data["jrc_energy_type"])
    data["technology"] = technology.fillna("GENERIC")
    data["process"] = data["technology"].map(PROCESS_MAPPING).fillna(data["technology"])

    # Non-energy feedstock is not an energy-conversion process. Giving it an
    # explicit process label prevents uncoded chemical feedstock rows from
    # disappearing when process-level data are grouped later.
    feedstock = data["use_type"].eq("feedstock")
    data.loc[feedstock, "technology"] = "FEEDSTOCK"
    data.loc[feedstock, "process"] = "FEEDSTOCK"
    return data


def read_jrc_energy_sheet(
    file_path: Path,
    sector: str,
    year: int,
    energy_layer: str,
) -> pd.DataFrame:
    """Read one JRC ``<sector>_fec`` or ``<sector>_ued`` sheet.

    Carrier and hierarchy codes are retained exactly as supplied by JRC.
    ``TOTAL`` carrier rows are removed to avoid double counting.
    """
    energy_layer = energy_layer.upper()
    if energy_layer not in ENERGY_LAYERS:
        raise ValueError(f"Unsupported energy layer: {energy_layer}")

    sheet = f"{sector}_{energy_layer.lower()}"
    df = pd.read_excel(file_path, sheet_name=sheet)
    if "Code" not in df.columns:
        raise ValueError(f"Sheet '{sheet}' in {file_path} has no 'Code' column.")

    year_col = _year_column(df, year, sheet, file_path)

    # Normal UED/FEC process rows are code-driven. Rows without Code cannot be
    # safely assigned to a process and are therefore not guessed here. The
    # chemical feedstock exception is handled explicitly from FEC below.
    coded = df.loc[df["Code"].notna(), [df.columns[0], "Code", year_col]].copy()
    coded.rename(
        columns={df.columns[0]: "source_description", year_col: "source_value"},
        inplace=True,
    )

    split = coded["Code"].astype(str).str.split(".", expand=True)
    split = split.iloc[:, : len(JRC_CODE_COLUMNS)]
    split.columns = JRC_CODE_COLUMNS[: split.shape[1]]
    data = pd.concat([coded.reset_index(drop=True), split.reset_index(drop=True)], axis=1)

    for column in JRC_CODE_COLUMNS:
        if column not in data.columns:
            data[column] = None
        data[column] = data[column].map(_clean_code_part)

    indicator = data["indicator"].fillna("").str.upper()

    if energy_layer == "FEC":
        # FEC sheets can contain NONENERGY rows for feedstocks.
        keep = indicator.isin({"FEC", "NONENERGY"})
        data = data.loc[keep].copy()
        data["use_type"] = np.where(
            data["indicator"].fillna("").str.upper().eq("NONENERGY"),
            "feedstock",
            "final_energy",
        )
    else:
        data = data.loc[indicator.eq("UED")].copy()
        data["use_type"] = "final_energy"

    data = data.loc[
        ~data["jrc_energy_carrier"].fillna("").str.upper().eq("TOTAL")
    ].copy()
    data["source_value"] = pd.to_numeric(data["source_value"], errors="coerce")
    data = data.loc[data["source_value"].notna()].copy()

    # Chemical NONENERGY codes in JRC are less complete than normal process
    # codes. They belong to basic chemicals in this historical representation.
    feedstock = data["use_type"].eq("feedstock")
    if sector == "CHI" and feedstock.any():
        data.loc[feedstock & data["sector"].isna(), "sector"] = "CHI"
        data.loc[feedstock & data["subsector"].isna(), "subsector"] = "BASIC_CHEM"

    data = _normalize_process_fields(data)

    meta = data.apply(
        lambda row: schema_for_jrc_subsector(
            str(row["sector"] or sector), row["subsector"]
        ),
        axis=1,
    )
    data["sector"] = data["sector"].fillna(sector)
    data["sector_name"] = meta.map(lambda x: x["sector_name"])
    data["activity"] = meta.map(lambda x: x["activity"])
    data["commodity"] = meta.map(lambda x: x["commodity"])
    data["production_route"] = meta.map(lambda x: x["production_route"])

    # JRC Industry energy sheets are expressed in ktoe. Keep source value/unit
    # and provide a common TWh/a value for downstream calculations.
    units = data["source_unit"].fillna("").str.upper()
    expected = {"KTOE", "KTOE/A", "KTOE/YR", ""}
    unknown_units = sorted(set(units[~units.isin(expected)]))
    if unknown_units:
        warnings.warn(
            f"Unexpected {energy_layer} units in {file_path.name}/{sheet}: "
            f"{unknown_units}. Values are converted with the JRC ktoe-to-TWh convention."
        )

    data["demand"] = data["source_value"] * KTOE_TO_TWH
    data["unit"] = "TWh/a"
    data["carrier"] = data["jrc_energy_carrier"]
    data["energy_layer"] = energy_layer
    data["year"] = int(year)
    data["source"] = "JRC-IDEES-2021"
    data["source_sheet"] = sheet
    data["source_note"] = None
    return data


def add_feedstock_to_ued(fec: pd.DataFrame, ued: pd.DataFrame) -> pd.DataFrame:
    """Add UED feedstock rows using FEC where JRC UED has no coded feedstock.

    Feedstocks are not converted into useful energy, so for this bookkeeping
    layer UED=FEC. This special case is explicit in ``source_note`` and does not
    alter ordinary UED process observations.
    """
    feedstock = fec.loc[fec["use_type"].eq("feedstock")].copy()
    if feedstock.empty:
        return ued

    # If a future JRC release supplies coded UED feedstock rows, do not duplicate
    # them. Match on the source-faithful structural fields.
    key_cols = [
        "sector",
        "subsector",
        "jrc_process",
        "jrc_energy_type",
        "jrc_energy_carrier",
        "process",
        "technology",
        "carrier",
    ]
    existing = ued.loc[ued["use_type"].eq("feedstock"), key_cols].drop_duplicates()
    if not existing.empty:
        missing = feedstock.merge(existing, on=key_cols, how="left", indicator=True)
        feedstock = missing.loc[missing["_merge"].eq("left_only"), fec.columns].copy()

    if feedstock.empty:
        return ued

    feedstock["energy_layer"] = "UED"
    feedstock["indicator"] = "UED"
    feedstock["source_note"] = (
        "UED feedstock copied from FEC because JRC UED does not provide coded "
        "feedstock rows; UED=FEC for feedstock bookkeeping."
    )
    # Keep the FEC sheet in source_sheet so provenance remains truthful.
    return pd.concat([ued, feedstock], ignore_index=True)


def read_jrc_country(country: str, year: int, jrc_dir: Path | str) -> pd.DataFrame:
    jrc_dir = Path(jrc_dir)
    jrc_country = JRC_NAMES.get(country, country)
    file_path = jrc_dir / jrc_country / f"JRC-IDEES-2021_Industry_{jrc_country}.xlsx"
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    frames = []
    for sector in JRC_INDUSTRY_SHEETS:
        try:
            fec = read_jrc_energy_sheet(file_path, sector, year, "FEC")
            ued = read_jrc_energy_sheet(file_path, sector, year, "UED")
            ued = add_feedstock_to_ued(fec, ued)
            frames.extend([fec, ued])
        except (ValueError, KeyError) as exc:
            # Some country workbooks may omit a sector/layer sheet. Preserve an
            # explicit warning rather than fabricating ordinary process rows.
            warnings.warn(str(exc))

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "country", country)
    return out


def _production_by_activity(production: pd.DataFrame) -> pd.DataFrame:
    return production.groupby(
        ["country", "sector", "activity"], as_index=False
    )["production"].sum()


def infer_non_eu_demand(
    eu_demand: pd.DataFrame,
    production: pd.DataFrame,
    countries: list[str],
    eu27: set[str],
) -> pd.DataFrame:
    """Infer non-EU process/carrier/layer structure from EU intensities."""
    non_eu = [c for c in countries if c not in eu27]
    if not non_eu or eu_demand.empty:
        return pd.DataFrame(columns=eu_demand.columns)

    prod = _production_by_activity(production)
    eu_prod = (
        prod.loc[prod["country"].isin(eu27)]
        .groupby(["sector", "activity"], as_index=False)["production"]
        .sum()
        .rename(columns={"production": "eu_production"})
    )

    structure_cols = [
        "sector",
        "sector_name",
        "activity",
        "commodity",
        "production_route",
        "process",
        "technology",
        "carrier",
        "energy_layer",
        "use_type",
        "jrc_process",
        "jrc_energy_type",
        "jrc_energy_carrier",
        "source_description",
        "source_unit",
        "source_sheet",
        "source_note",
    ]
    eu_energy = (
        eu_demand.groupby(structure_cols, dropna=False, as_index=False)["demand"]
        .sum()
        .merge(eu_prod, on=["sector", "activity"], how="left")
    )
    eu_energy["intensity"] = eu_energy["demand"] / eu_energy["eu_production"]
    eu_energy.replace([np.inf, -np.inf], np.nan, inplace=True)
    eu_energy = eu_energy.loc[eu_energy["intensity"].notna()].copy()

    frames = []
    for country in non_eu:
        p = prod.loc[
            prod["country"].eq(country), ["sector", "activity", "production"]
        ]
        if p.empty:
            continue
        inferred = eu_energy.merge(p, on=["sector", "activity"], how="inner")
        inferred["demand"] = inferred["intensity"] * inferred["production"]
        inferred["country"] = country
        inferred["year"] = int(eu_demand["year"].iloc[0])
        inferred["unit"] = "TWh/a"
        inferred["source"] = "inferred_from_EU"
        inferred["source_value"] = np.nan
        inferred["source_unit"] = None
        inferred["indicator"] = inferred["energy_layer"]
        inferred["region"] = country
        inferred["Code"] = None
        frames.append(inferred.reindex(columns=eu_demand.columns))

    return (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=eu_demand.columns)
    )


def _production_lookup(production: pd.DataFrame) -> pd.DataFrame:
    return production.pivot_table(
        index="country",
        columns="activity",
        values="production",
        aggfunc="sum",
        fill_value=0.0,
    )


def _derive_hvc_ued(
    original_basic: pd.DataFrame,
    calibrated_basic: pd.DataFrame,
) -> pd.DataFrame:
    """Rescale Basic-chemicals UED using original JRC process efficiencies.

    Only ordinary final-energy rows participate in the efficiency calculation.
    Feedstock UED rows are already exact FEC copies and are therefore simply
    retained/renamed with the calibrated HVC structure.
    """
    ued = original_basic.loc[
        original_basic["energy_layer"].eq("UED")
        & original_basic["use_type"].eq("final_energy")
    ].copy()
    fec_original = original_basic.loc[
        original_basic["energy_layer"].eq("FEC")
        & original_basic["use_type"].eq("final_energy")
    ].copy()
    fec_hvc = calibrated_basic.loc[
        calibrated_basic["energy_layer"].eq("FEC")
        & calibrated_basic["use_type"].eq("final_energy")
    ].copy()

    if ued.empty or fec_original.empty or fec_hvc.empty:
        return ued

    group_cols = ["country", "sector", "activity", "process", "year"]
    original_fec_tot = (
        fec_original.groupby(group_cols, as_index=False)["demand"]
        .sum()
        .rename(columns={"demand": "fec_original"})
    )
    original_ued_tot = (
        ued.groupby(group_cols, as_index=False)["demand"]
        .sum()
        .rename(columns={"demand": "ued_original"})
    )
    efficiency = original_fec_tot.merge(original_ued_tot, on=group_cols, how="outer")
    efficiency[["fec_original", "ued_original"]] = efficiency[
        ["fec_original", "ued_original"]
    ].fillna(0.0)
    efficiency["efficiency"] = np.where(
        efficiency["fec_original"] > 0,
        efficiency["ued_original"] / efficiency["fec_original"],
        0.0,
    )

    fec_hvc_for_join = fec_hvc.copy()
    fec_hvc_for_join["activity"] = "Basic chemicals"
    hvc_fec_tot = (
        fec_hvc_for_join.groupby(group_cols, as_index=False)["demand"]
        .sum()
        .rename(columns={"demand": "fec_hvc"})
    )
    hvc_tot = hvc_fec_tot.merge(
        efficiency[group_cols + ["efficiency"]], on=group_cols, how="left"
    )
    hvc_tot["efficiency"] = hvc_tot["efficiency"].fillna(0.0)
    hvc_tot["ued_hvc"] = hvc_tot["fec_hvc"] * hvc_tot["efficiency"]

    ued_tot = original_ued_tot
    out = ued.merge(ued_tot, on=group_cols, how="left", validate="many_to_one")
    out["ued_share"] = np.where(
        out["ued_original"] > 0, out["demand"] / out["ued_original"], 0.0
    )
    out = out.merge(
        hvc_tot[group_cols + ["ued_hvc"]], on=group_cols, how="left", validate="many_to_one"
    )
    out["ued_hvc"] = out["ued_hvc"].fillna(0.0)
    out["demand"] = out["ued_share"] * out["ued_hvc"]
    out.drop(columns=["ued_original", "ued_share", "ued_hvc"], inplace=True)
    return out


def calibrate_basic_chemicals(
    demand: pd.DataFrame,
    production: pd.DataFrame,
    calibration: dict,
) -> pd.DataFrame:
    """Split JRC Basic chemicals while preserving FEC/UED process structure."""
    if demand.empty:
        return demand

    production_m = _production_lookup(production)
    basic_mask = demand["sector"].eq("CHI") & demand["activity"].eq("Basic chemicals")
    original_basic = demand.loc[basic_mask].copy()
    other = demand.loc[~basic_mask].copy()
    if original_basic.empty:
        return demand

    basic = original_basic.copy()
    additions = []

    # Apply explicit historical chemical deductions to FEC only. UED is then
    # reconstructed using the original JRC process-level UED/FEC efficiency.
    fec_energy = basic["energy_layer"].eq("FEC") & basic["use_type"].eq("final_energy")

    for country in sorted(basic["country"].unique()):
        if country not in production_m.index:
            continue
        row = production_m.loc[country]
        chlorine = float(row.get("Chlorine", 0.0)) / 1e3
        methanol = float(row.get("Methanol", 0.0)) / 1e3
        ammonia = float(row.get("Ammonia", 0.0)) / 1e3

        deductions = {
            "ELEC": (
                chlorine * calibration["MWh_elec_per_tCl"]
                + methanol * calibration["MWh_elec_per_tMeOH"]
                + ammonia * calibration["MWh_elec_per_tNH3_electrolysis"]
            ),
            "NG_BIOGAS": methanol * calibration["MWh_CH4_per_tMeOH"],
            "HYDROGEN": (
                chlorine * calibration["MWh_H2_per_tCl"]
                + ammonia * calibration["MWh_H2_per_tNH3_electrolysis"]
            ),
        }

        for carrier, deduction in deductions.items():
            idx = (
                basic["country"].eq(country)
                & fec_energy
                & basic["carrier"].eq(carrier)
            )
            if not idx.any() or abs(deduction) < 1e-15:
                continue
            total = basic.loc[idx, "demand"].sum()
            if total == 0:
                continue
            if deduction > total + 1e-12:
                warnings.warn(
                    f"Chemical calibration deduction ({deduction:.4f} TWh) exceeds "
                    f"JRC Basic chemicals {carrier} FEC ({total:.4f} TWh) for {country}."
                )
            shares = basic.loc[idx, "demand"] / total
            basic.loc[idx, "demand"] = basic.loc[idx, "demand"] - shares * deduction

        def add(activity: str, carrier: str, value: float, use_type: str = "final_energy"):
            if abs(value) < 1e-15:
                return
            schema = CHEMICAL_SCHEMA[activity]
            additions.append(
                dict(
                    country=country,
                    sector="CHI",
                    sector_name=SECTOR_NAMES["CHI"],
                    activity=activity,
                    commodity=schema["commodity"],
                    production_route=schema["production_route"],
                    process="CALIBRATED",
                    technology="CALIBRATED",
                    carrier=carrier,
                    energy_layer="FEC",
                    use_type=use_type,
                    year=int(calibration["reference_year"]),
                    demand=value,
                    unit="TWh/a",
                    source="historical_calibration",
                    source_description="historical chemical calibration",
                    source_sheet=None,
                    source_note="No independent JRC UED is created for calibrated chemical subactivities.",
                    source_value=np.nan,
                    source_unit=None,
                    indicator="FEC",
                    region=country,
                    subsector=activity.upper(),
                    jrc_process=None,
                    jrc_energy_type=None,
                    jrc_energy_carrier=None,
                    Code=None,
                )
            )

        add("Chlorine", "ELEC", chlorine * calibration["MWh_elec_per_tCl"])
        add("Chlorine", "HYDROGEN", chlorine * calibration["MWh_H2_per_tCl"])
        add("Methanol", "ELEC", methanol * calibration["MWh_elec_per_tMeOH"])
        # Methanol natural-gas input is treated as feedstock/non-energy use.
        add("Methanol", "NG_BIOGAS", methanol * calibration["MWh_CH4_per_tMeOH"], "feedstock")
        if calibration.get("ammonia", True):
            add("Ammonia", "AMMONIA", ammonia * calibration["MWh_NH3_per_tNH3"], "feedstock")
        else:
            add("Ammonia", "ELEC", ammonia * calibration["MWh_elec_per_tNH3_electrolysis"])
            add("Ammonia", "HYDROGEN", ammonia * calibration["MWh_H2_per_tNH3_electrolysis"], "feedstock")

    # Reconstruct HVC UED using JRC process efficiencies after the FEC deduction.
    hvc_ued = _derive_hvc_ued(original_basic, basic)

    # Keep UED feedstock rows copied from FEC unchanged (UED=FEC), but rename
    # their activity to HVC together with the calibrated FEC residual.
    basic_no_ued_energy = basic.loc[
        ~(
            basic["energy_layer"].eq("UED")
            & basic["use_type"].eq("final_energy")
        )
    ].copy()
    basic = pd.concat([basic_no_ued_energy, hvc_ued], ignore_index=True)
    basic["activity"] = "HVC"
    basic["commodity"] = CHEMICAL_SCHEMA["HVC"]["commodity"]
    basic["production_route"] = "BASE_ROUTE"
    basic["subsector"] = "HVC"
    basic["source"] = basic["source"].astype(str) + "+historical_calibration"

    calibrated = pd.DataFrame(additions)
    if calibrated.empty:
        return pd.concat([other, basic], ignore_index=True)
    calibrated = calibrated.reindex(columns=demand.columns)
    return pd.concat([other, basic, calibrated], ignore_index=True)


def add_coke_ovens(
    demand: pd.DataFrame,
    coke_path: Path,
    year: int,
    factor: float,
) -> pd.DataFrame:
    """Append Eurostat coke-oven FEC as an explicit BF-BOF process."""
    if not coke_path.exists():
        return demand
    coke = pd.read_csv(coke_path, index_col=[0, 1])
    try:
        coke = coke.xs(year, level=1)
    except KeyError:
        return demand

    rows = []
    for country, series in coke.iterrows():
        for carrier in COKE_CARRIERS:
            if carrier not in series.index or pd.isna(series[carrier]):
                continue
            value = float(series[carrier]) * factor
            if abs(value) < 1e-15:
                continue
            rows.append(
                dict(
                    country=country,
                    sector="ISI",
                    sector_name=SECTOR_NAMES["ISI"],
                    activity="Integrated steelworks",
                    commodity="STEEL",
                    production_route="BF_BOF",
                    process="COKE_OVENS",
                    technology="COKE_OVENS",
                    carrier=carrier,
                    energy_layer="FEC",
                    use_type="final_energy",
                    year=year,
                    demand=value,
                    unit="TWh/a",
                    source="Eurostat coke-oven calibration",
                    source_description="Coke ovens - Other sources",
                    source_sheet=None,
                    source_note="FEC-only auxiliary calibration; no independent UED available.",
                    source_value=value,
                    source_unit="TWh/a",
                    indicator="FEC",
                    region=country,
                    subsector="BF_BOF",
                    jrc_process=None,
                    jrc_energy_type=None,
                    jrc_energy_carrier=None,
                    Code=None,
                )
            )
    if not rows:
        return demand
    extra = pd.DataFrame(rows).reindex(columns=demand.columns)
    return pd.concat([demand, extra], ignore_index=True)


def prepare(
    countries: list[str],
    calibration: dict,
    jrc_dir: str | Path,
    production_path: str | Path,
    coke_path: str | Path,
    output_path: str | Path,
) -> None:
    year = int(calibration["reference_year"])
    jrc_dir = Path(jrc_dir)
    production = pd.read_csv(production_path)
    eu27 = set(coco.CountryConverter().EU27as("ISO2").ISO2.tolist())

    frames = []
    for country in countries:
        if country not in eu27:
            continue
        try:
            frames.append(read_jrc_country(country, year, jrc_dir))
        except FileNotFoundError:
            warnings.warn(
                f"No JRC Industry workbook found for {country}; skipping direct extraction."
            )

    eu_demand = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if eu_demand.empty:
        raise RuntimeError("No EU JRC process-level FEC/UED data could be read.")

    inferred = infer_non_eu_demand(eu_demand, production, countries, eu27)
    demand = pd.concat([eu_demand, inferred], ignore_index=True)
    demand = calibrate_basic_chemicals(demand, production, calibration)
    demand = add_coke_ovens(
        demand,
        Path(coke_path),
        year,
        float(calibration.get("coke_oven_allocation", 0.75)),
    )

    output_columns = [
        "country",
        "year",
        "sector",
        "sector_name",
        "activity",
        "commodity",
        "production_route",
        "process",
        "technology",
        "carrier",
        "energy_layer",
        "use_type",
        "demand",
        "unit",
        "source",
        "source_description",
        "source_sheet",
        "source_note",
        "source_value",
        "source_unit",
        "indicator",
        "region",
        "subsector",
        "jrc_process",
        "jrc_energy_type",
        "jrc_energy_carrier",
        "Code",
    ]
    demand = demand.reindex(columns=output_columns)
    demand.sort_values(
        [
            "country",
            "sector",
            "activity",
            "production_route",
            "process",
            "energy_layer",
            "use_type",
            "carrier",
        ],
        inplace=True,
        na_position="last",
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    demand.to_csv(output_path, index=False, float_format="%.8f")


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--jrc-dir", required=True)
    parser.add_argument("--production", required=True)
    parser.add_argument("--coke", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    prepare(
        countries=config["countries"],
        calibration=config["historical_calibration"],
        jrc_dir=args.jrc_dir,
        production_path=args.production,
        coke_path=args.coke,
        output_path=args.output,
    )

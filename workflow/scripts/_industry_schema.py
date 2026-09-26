"""Shared historical-industry schema for JRC-IDEES.

The historical representation deliberately stays close to the JRC-IDEES
Industry workbooks. Raw JRC codes are preserved in the output; canonical
``activity``, ``commodity`` and ``production_route`` fields are only added to
make later route/process substitutions easier.
"""

from __future__ import annotations

SECTOR_NAMES = {
    "ISI": "Iron and steel",
    "CHI": "Chemical industry",
    "NMM": "Non-metallic mineral products",
    "PPA": "Pulp, paper and printing",
    "FBT": "Food, beverages and tobacco",
    "NFM": "Non Ferrous Metals",
    "TRE": "Transport equipment",
    "MAE": "Machinery equipment",
    "TEL": "Textiles and leather",
    "WWP": "Wood and wood products",
    "OIS": "Other industrial sectors",
}

JRC_INDUSTRY_SHEETS = {sector: sector for sector in SECTOR_NAMES}
JRC_NAMES = {"GR": "EL", "GB": "UK"}

# Columns encoded in the dot-separated JRC ``Code`` field. Some rows contain
# fewer levels; pandas will simply leave the deeper levels empty.
JRC_CODE_COLUMNS = [
    "indicator",
    "source_unit",
    "region",
    "sector",
    "subsector",
    "jrc_process",
    "jrc_energy_type",
    "jrc_energy_carrier",
]

# Physical-output rows used from the JRC Industry workbooks.
PRODUCTION_DEFINITIONS = {
    "ISI": [
        dict(activity="Integrated steelworks", source_field="Integrated steelworks", commodity="STEEL", production_route="BF_BOF", unit="kt/a"),
        dict(activity="Electric arc", source_field="Electric arc", commodity="STEEL", production_route="EAF", unit="kt/a"),
    ],
    "CHI": [
        dict(activity="Basic chemicals", source_field="Basic chemicals (kt ethylene eq.)", commodity="BASIC_CHEMICALS", production_route="BASE_ROUTE", unit="kt ethylene eq./a"),
        dict(activity="Other chemicals", source_field="Other chemicals (kt ethylene eq.)", commodity="OTHER_CHEMICALS", production_route="BASE_ROUTE", unit="kt ethylene eq./a"),
        dict(activity="Pharmaceutical products etc.", source_field="Pharmaceutical products etc. (kt ethylene eq.)", commodity="PHARMACEUTICALS", production_route="BASE_ROUTE", unit="kt ethylene eq./a"),
    ],
    "NMM": [
        dict(activity="Cement", source_field="Cement (kt)", commodity="CEMENT", production_route="BASE_ROUTE", unit="kt/a"),
        dict(activity="Ceramics & other NMM", source_field="Ceramics & other NMM (kt bricks eq.)", commodity="CERAMICS", production_route="BASE_ROUTE", unit="kt bricks eq./a"),
        dict(activity="Glass production", source_field="Glass production  (kt)", commodity="GLASS", production_route="BASE_ROUTE", unit="kt/a"),
    ],
    "PPA": [
        dict(activity="Pulp production", source_field="Pulp production (kt)", commodity="PULP", production_route="BASE_ROUTE", unit="kt/a"),
        dict(activity="Paper production", source_field="Paper production  (kt)", commodity="PAPER", production_route="BASE_ROUTE", unit="kt/a"),
        dict(activity="Printing and media reproduction", source_field="Printing and media reproduction (kt paper eq.)", commodity="PRINTING", production_route="BASE_ROUTE", unit="kt paper eq./a"),
    ],
    "FBT": [dict(activity="Food, beverages and tobacco", source_field="Physical output (index)", commodity="FBT", production_route="BASE_ROUTE", unit="index")],
    "NFM": [
        dict(activity="Alumina production", source_field="Alumina production (kt)", commodity="ALUMINA", production_route="BASE_ROUTE", unit="kt/a"),
        dict(activity="Aluminium - primary production", source_field="Aluminium - primary production", commodity="ALUMINIUM", production_route="PRIM_ALU", unit="kt/a"),
        dict(activity="Aluminium - secondary production", source_field="Aluminium - secondary production", commodity="ALUMINIUM", production_route="SEC_ALU", unit="kt/a"),
        dict(activity="Other non-ferrous metals", source_field="Other non-ferrous metals (kt lead eq.)", commodity="OTHER_NFM", production_route="BASE_ROUTE", unit="kt lead eq./a"),
    ],
    "TRE": [dict(activity="Transport equipment", source_field="Physical output (index)", commodity="TRE", production_route="BASE_ROUTE", unit="index")],
    "MAE": [dict(activity="Machinery equipment", source_field="Physical output (index)", commodity="MAE", production_route="BASE_ROUTE", unit="index")],
    "TEL": [dict(activity="Textiles and leather", source_field="Physical output (index)", commodity="TEL", production_route="BASE_ROUTE", unit="index")],
    "WWP": [dict(activity="Wood and wood products", source_field="Physical output (index)", commodity="WWP", production_route="BASE_ROUTE", unit="index")],
    "OIS": [dict(activity="Other industrial sectors", source_field="Physical output (index)", commodity="OIS", production_route="BASE_ROUTE", unit="index")],
}

# Known JRC subsector codes used in the Industry workbook. Unknown codes are
# preserved rather than discarded; see ``schema_for_jrc_subsector`` below.
JRC_SUBSECTOR_SCHEMA = {
    ("ISI", "BF_BOF"): dict(activity="Integrated steelworks", commodity="STEEL", production_route="BF_BOF"),
    ("ISI", "EAF"): dict(activity="Electric arc", commodity="STEEL", production_route="EAF"),
    ("CHI", "BASIC_CHEM"): dict(activity="Basic chemicals", commodity="BASIC_CHEMICALS", production_route="BASE_ROUTE"),
    ("CHI", "OTHER_CHEM"): dict(activity="Other chemicals", commodity="OTHER_CHEMICALS", production_route="BASE_ROUTE"),
    ("CHI", "PHARMA"): dict(activity="Pharmaceutical products etc.", commodity="PHARMACEUTICALS", production_route="BASE_ROUTE"),
    ("NMM", "CEM"): dict(activity="Cement", commodity="CEMENT", production_route="BASE_ROUTE"),
    ("NMM", "CER"): dict(activity="Ceramics & other NMM", commodity="CERAMICS", production_route="BASE_ROUTE"),
    ("NMM", "GLASS"): dict(activity="Glass production", commodity="GLASS", production_route="BASE_ROUTE"),
    ("PPA", "PULP"): dict(activity="Pulp production", commodity="PULP", production_route="BASE_ROUTE"),
    ("PPA", "PAPER"): dict(activity="Paper production", commodity="PAPER", production_route="BASE_ROUTE"),
    ("PPA", "PRINT"): dict(activity="Printing and media reproduction", commodity="PRINTING", production_route="BASE_ROUTE"),
    ("NFM", "ALUMINA"): dict(activity="Alumina production", commodity="ALUMINA", production_route="BASE_ROUTE"),
    ("NFM", "PRIM_ALU"): dict(activity="Aluminium - primary production", commodity="ALUMINIUM", production_route="PRIM_ALU"),
    ("NFM", "SEC_ALU"): dict(activity="Aluminium - secondary production", commodity="ALUMINIUM", production_route="SEC_ALU"),
    ("NFM", "OTHER_NFM"): dict(activity="Other non-ferrous metals", commodity="OTHER_NFM", production_route="BASE_ROUTE"),
}

# Process normalization developed in the earlier test model. The raw JRC
# process/energy-type codes remain available in separate columns.
PROCESS_MAPPING = {
    "LIGHT": "LIGHTING",
    "AIRCOMP": "AIR_COMPRESSION",
    "MOTOR": "MOTOR_DRIVES",
    "FANS": "FANS_PUMPS",
    "LOW_ENTH": "LOW_ENTHALPY_HEAT",
    "DRYING": "DRYING",
    "DRYING_STEAM": "DRYING",
    "DRYING_ELEC": "DRYING",
    "DRYING_MICROW": "DRYING",
    "DRYING_FREEZE": "DRYING",
    "KILN": "KILN",
    "KILN_THERM": "KILN",
    "KILN_ELEC": "KILN",
    "MELTING": "MELTING",
    "MELTING_ELEC": "MELTING",
    "ANNEALING": "ANNEALING",
    "ANNEALING_ELEC": "ANNEALING",
    "FINISHING": "FINISHING",
    "FINISHING_ELEC": "FINISHING",
    "FINISHING_STEAM": "FINISHING",
    "PROCESSING": "PROCESSING",
    "PROCESSING_STEAM": "PROCESSING",
    "PROC_HEAT": "PROCESS_HEAT",
    "PROC_HEAT_ELEC": "PROCESS_HEAT",
    "PROC_HEAT_MICROW": "PROCESS_HEAT",
    "PROC_COOL": "PROCESS_COOLING",
    "PROC_COOL_ELEC": "PROCESS_COOLING",
    "PROC_COOL_STEAM": "PROCESS_COOLING",
    "PROC_COOL_THERM": "PROCESS_COOLING",
    "OVEN": "OVEN",
    "OVEN_MICROW": "OVEN",
    "CONNECTION_THERM": "CONNECTION",
    "CONNECTION_ELEC": "CONNECTION",
    "PREPARATION": "PREPARATION",
    "PREPARATION_ELEC": "PREPARATION",
    "PAPER_MACHINE": "PAPER_MACHINE",
    "PAPER_MACHINE_ELEC": "PAPER_MACHINE",
}

CHEMICAL_SCHEMA = {
    "Ammonia": dict(sector="CHI", sector_name=SECTOR_NAMES["CHI"], commodity="AMMONIA", production_route="BASE_ROUTE", unit="kt/a"),
    "HVC": dict(sector="CHI", sector_name=SECTOR_NAMES["CHI"], commodity="HVC", production_route="BASE_ROUTE", unit="kt/a"),
    "Chlorine": dict(sector="CHI", sector_name=SECTOR_NAMES["CHI"], commodity="CHLORINE", production_route="BASE_ROUTE", unit="kt/a"),
    "Methanol": dict(sector="CHI", sector_name=SECTOR_NAMES["CHI"], commodity="METHANOL", production_route="BASE_ROUTE", unit="kt/a"),
}

# Raw Eurostat product categories retained for the coke-oven add-on. They are
# not collapsed into model fuel groups.
COKE_CARRIERS = [
    "Solid fossil fuels",
    "Peat and peat products",
    "Oil shale and oil sands",
    "Oil and petroleum products",
    "Manufactured gases",
    "Natural gas",
    "Nuclear heat",
    "Heat",
    "Renewables and biofuels",
    "Non-renewable waste",
    "Electricity",
]


def schema_for_jrc_subsector(sector: str, subsector: str | None) -> dict:
    """Return canonical metadata while preserving unknown JRC subsectors."""
    subsector = "" if subsector is None else str(subsector)
    known = JRC_SUBSECTOR_SCHEMA.get((sector, subsector))
    if known is not None:
        return {"sector_name": SECTOR_NAMES.get(sector, sector), **known}

    definitions = PRODUCTION_DEFINITIONS.get(sector, [])
    if len(definitions) == 1:
        d = definitions[0]
        return {
            "sector_name": SECTOR_NAMES.get(sector, sector),
            "activity": d["activity"],
            "commodity": d["commodity"],
            "production_route": d["production_route"],
        }

    fallback = subsector or sector
    return {
        "sector_name": SECTOR_NAMES.get(sector, sector),
        "activity": fallback,
        "commodity": fallback,
        "production_route": "BASE_ROUTE",
    }

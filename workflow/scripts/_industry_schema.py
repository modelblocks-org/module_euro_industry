"""Shared historical-industry schema for JRC-IDEES.

The historical representation deliberately stays close to the JRC-IDEES Industry workbooks.
Raw JRC codes are preserved in the output.
The canonical ``activity``, ``commodity`` and ``production_route`` fields are only added to
make later route/process substitutions easier.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ActivityMetadata(BaseModel):
    """Canonical activity labels shared by production and energy demand schemas."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    activity: str
    commodity: str
    production_route: str = "BASE_ROUTE"


class ProductionDefinition(ActivityMetadata):
    """Physical-output field and optional energy-sheet subsector in JRC."""

    source_field: str
    unit: str
    jrc_subsector: str | None = None


class ChemicalDefinition(ActivityMetadata):
    """Metadata for a calibrated chemical activity."""

    sector: str = "CHI"
    unit: str = "kt/a"

    @property
    def sector_name(self) -> str:
        """Look up the sector name without repeating it in each definition."""
        return SECTOR_NAMES[self.sector]


class SubsectorMetadata(ActivityMetadata):
    """Canonical labels resolved from a raw JRC sector and subsector."""

    sector_name: str


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
PRODUCTION_DEFINITIONS: dict[str, list[ProductionDefinition]] = {
    "ISI": [
        ProductionDefinition(
            activity="Integrated steelworks",
            source_field="Integrated steelworks",
            commodity="STEEL",
            production_route="BF_BOF",
            unit="kt/a",
            jrc_subsector="BF_BOF",
        ),
        ProductionDefinition(
            activity="Electric arc",
            source_field="Electric arc",
            commodity="STEEL",
            production_route="EAF",
            unit="kt/a",
            jrc_subsector="EAF",
        ),
    ],
    "CHI": [
        ProductionDefinition(
            activity="Basic chemicals",
            source_field="Basic chemicals (kt ethylene eq.)",
            commodity="BASIC_CHEMICALS",
            unit="kt ethylene eq./a",
            jrc_subsector="BASIC_CHEM",
        ),
        ProductionDefinition(
            activity="Other chemicals",
            source_field="Other chemicals (kt ethylene eq.)",
            commodity="OTHER_CHEMICALS",
            unit="kt ethylene eq./a",
            jrc_subsector="OTHER_CHEM",
        ),
        ProductionDefinition(
            activity="Pharmaceutical products etc.",
            source_field="Pharmaceutical products etc. (kt ethylene eq.)",
            commodity="PHARMACEUTICALS",
            unit="kt ethylene eq./a",
            jrc_subsector="PHARMA",
        ),
    ],
    "NMM": [
        ProductionDefinition(
            activity="Cement",
            source_field="Cement (kt)",
            commodity="CEMENT",
            unit="kt/a",
            jrc_subsector="CEM",
        ),
        ProductionDefinition(
            activity="Ceramics & other NMM",
            source_field="Ceramics & other NMM (kt bricks eq.)",
            commodity="CERAMICS",
            unit="kt bricks eq./a",
            jrc_subsector="CER",
        ),
        ProductionDefinition(
            activity="Glass production",
            source_field="Glass production  (kt)",
            commodity="GLASS",
            unit="kt/a",
            jrc_subsector="GLASS",
        ),
    ],
    "PPA": [
        ProductionDefinition(
            activity="Pulp production",
            source_field="Pulp production (kt)",
            commodity="PULP",
            unit="kt/a",
            jrc_subsector="PULP",
        ),
        ProductionDefinition(
            activity="Paper production",
            source_field="Paper production  (kt)",
            commodity="PAPER",
            unit="kt/a",
            jrc_subsector="PAPER",
        ),
        ProductionDefinition(
            activity="Printing and media reproduction",
            source_field="Printing and media reproduction (kt paper eq.)",
            commodity="PRINTING",
            unit="kt paper eq./a",
            jrc_subsector="PRINT",
        ),
    ],
    "FBT": [
        ProductionDefinition(
            activity="Food, beverages and tobacco",
            source_field="Physical output (index)",
            commodity="FBT",
            unit="index",
        )
    ],
    "NFM": [
        ProductionDefinition(
            activity="Alumina production",
            source_field="Alumina production (kt)",
            commodity="ALUMINA",
            unit="kt/a",
            jrc_subsector="ALUMINA",
        ),
        ProductionDefinition(
            activity="Aluminium - primary production",
            source_field="Aluminium - primary production",
            commodity="ALUMINIUM",
            production_route="PRIM_ALU",
            unit="kt/a",
            jrc_subsector="PRIM_ALU",
        ),
        ProductionDefinition(
            activity="Aluminium - secondary production",
            source_field="Aluminium - secondary production",
            commodity="ALUMINIUM",
            production_route="SEC_ALU",
            unit="kt/a",
            jrc_subsector="SEC_ALU",
        ),
        ProductionDefinition(
            activity="Other non-ferrous metals",
            source_field="Other non-ferrous metals (kt lead eq.)",
            commodity="OTHER_NFM",
            unit="kt lead eq./a",
            jrc_subsector="OTHER_NFM",
        ),
    ],
    "TRE": [
        ProductionDefinition(
            activity="Transport equipment",
            source_field="Physical output (index)",
            commodity="TRE",
            unit="index",
        )
    ],
    "MAE": [
        ProductionDefinition(
            activity="Machinery equipment",
            source_field="Physical output (index)",
            commodity="MAE",
            unit="index",
        )
    ],
    "TEL": [
        ProductionDefinition(
            activity="Textiles and leather",
            source_field="Physical output (index)",
            commodity="TEL",
            unit="index",
        )
    ],
    "WWP": [
        ProductionDefinition(
            activity="Wood and wood products",
            source_field="Physical output (index)",
            commodity="WWP",
            unit="index",
        )
    ],
    "OIS": [
        ProductionDefinition(
            activity="Other industrial sectors",
            source_field="Physical output (index)",
            commodity="OIS",
            unit="index",
        )
    ],
}

# Known JRC subsector codes used in the Industry workbook. Unknown codes are
# preserved rather than discarded; see ``schema_for_jrc_subsector`` below.
JRC_SUBSECTOR_LOOKUP: dict[tuple[str, str], ProductionDefinition] = {
    (sector, definition.jrc_subsector): definition
    for sector, definitions in PRODUCTION_DEFINITIONS.items()
    for definition in definitions
    if definition.jrc_subsector is not None
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

CHEMICAL_DEFINITIONS: dict[str, ChemicalDefinition] = {
    definition.activity: definition
    for definition in (
        ChemicalDefinition(activity="Ammonia", commodity="AMMONIA"),
        ChemicalDefinition(activity="HVC", commodity="HVC"),
        ChemicalDefinition(activity="Chlorine", commodity="CHLORINE"),
        ChemicalDefinition(activity="Methanol", commodity="METHANOL"),
    )
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


def schema_for_jrc_subsector(sector: str, subsector: str | None) -> SubsectorMetadata:
    """Return canonical metadata while preserving unknown JRC subsectors."""
    subsector = "" if subsector is None else str(subsector)
    definition = JRC_SUBSECTOR_LOOKUP.get((sector, subsector))
    if definition is None:
        definitions = PRODUCTION_DEFINITIONS.get(sector, [])
        if len(definitions) == 1:
            definition = definitions[0]

    if definition is not None:
        return SubsectorMetadata(
            sector_name=SECTOR_NAMES.get(sector, sector),
            activity=definition.activity,
            commodity=definition.commodity,
            production_route=definition.production_route,
        )

    fallback = subsector or sector
    return SubsectorMetadata(
        sector_name=SECTOR_NAMES.get(sector, sector),
        activity=fallback,
        commodity=fallback,
    )

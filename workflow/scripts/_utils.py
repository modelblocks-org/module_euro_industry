"""Shared helper functions for workflow scripts."""

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


def spatial_category(sector: str, commodity: str) -> str:
    """Map model sector/commodity to the Hotmaps industrial subsector taxonomy."""
    if sector == "NMM":
        if commodity in {"CEM", "CEMENT"}:
            return "Cement"
        if commodity == "GLASS":
            return "Glass"
        return "Non-metallic mineral products"
    return HOTMAPS_CATEGORY_BY_SECTOR.get(sector, "Other non-classified")

"""Validation of user-provided geographic shapes."""

from copy import deepcopy

from pandera import pandas as pa
from pandera.typing.geopandas import GeoSeries
from pandera.typing.pandas import Series
from shapely.geometry import MultiPolygon, Polygon


class ShapesSchema(pa.DataFrameModel):
    """Regions with unique names, valid boundaries and at least one land region."""

    shape_id: Series[str] = pa.Field(unique=True, str_length={"min_value": 1})
    country_id: Series[str] = pa.Field(str_matches=r"^[A-Za-z]{2,3}$")
    shape_class: Series[str] = pa.Field(str_length={"min_value": 1})
    geometry: GeoSeries

    @classmethod
    def validate_for_year(cls, table, reference_year: int):
        """Check shapes and the Swiss data coverage for the selected year."""
        schema = deepcopy(cls.to_schema())
        if reference_year < 2014:
            schema.checks.append(
                pa.Check(
                    lambda frame: (
                        not (
                            frame["shape_class"].eq("land")
                            & frame["country_id"].str.upper().isin(["CH", "CHE"])
                        ).any()
                    ),
                    error="Switzerland requires a historical reference year of 2014 or later.",
                )
            )
        return schema.validate(table, lazy=True)

    @pa.dataframe_check
    def has_land_regions(cls, table):
        """Require at least one land region, rejecting empty inputs too."""
        return "shape_class" in table.columns and table["shape_class"].eq("land").any()

    @pa.check("geometry", element_wise=True)
    def valid_boundaries(cls, geometry):
        """Require nonempty, valid polygons."""
        return (
            isinstance(geometry, (Polygon, MultiPolygon))
            and not geometry.is_empty
            and geometry.is_valid
        )

    @pa.dataframe_check
    def has_crs(cls, table):
        """Require a coordinate system so regions can be mapped correctly."""
        return table.crs is not None

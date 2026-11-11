"""Validation of user-provided geographic shapes."""

from copy import deepcopy

import pandas as pd
from pandera import pandas as pa
from pandera.typing.geopandas import GeoSeries
from pandera.typing.pandas import Series
from shapely.geometry import MultiPolygon, Polygon


class ShapesSchema(pa.DataFrameModel):
    """Regions with unique names, valid boundaries and at least one land region."""

    shape_id: Series[str] = pa.Field(unique=True, str_length={"min_value": 1})
    country_id: Series[str] = pa.Field(str_matches=r"^[A-Z]{3}$")
    shape_class: Series[str] = pa.Field(str_length={"min_value": 1})
    geometry: GeoSeries

    class Config:
        """Coerce declared column types and allow additional columns."""

        coerce = True
        strict = False

    @classmethod
    def validate_for_year(
        cls, table: pd.DataFrame, reference_year: int
    ) -> pd.DataFrame:
        """Check shapes and the Swiss data coverage for the selected year."""
        schema = deepcopy(cls.to_schema())
        if reference_year < 2014:
            schema.checks.append(
                pa.Check(
                    lambda frame: (
                        not (
                            frame["shape_class"].eq("land")
                            & frame["country_id"].eq("CHE")
                        ).any()
                    ),
                    error="Switzerland requires a historical reference year of 2014 or later.",
                )
            )
        return schema.validate(table, lazy=True)

    @pa.check("shape_class")
    def has_land_regions(cls, s: Series[str]):
        """Require at least one land region, rejecting empty inputs too."""
        return (s == "land").any()

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

"""Read target countries and expand the reference scope for calibration."""

import country_converter as coco
import pandas as pd


def _country_scope_w_proxies(
    country_ids: list[str],
    proxies: dict[str, list[str]],
    covered_country_ids: list[str],
) -> list[str]:
    expanded_country_ids = set(country_ids)
    for country_id in expanded_country_ids - set(covered_country_ids):
        expanded_country_ids.update(proxies[country_id])
    return sorted(expanded_country_ids)


def read_country_ids(path: str) -> list[str]:
    """Read target countries directly from the prepared shapes' country column."""
    return sorted(pd.read_parquet(path, columns=["country"])["country"].unique())


def read_country_scope(path: str, supported_countries):
    """Derive target and reference countries without a separate scope file."""
    return country_scope(
        read_country_ids(path),
        supported_countries,
        coco.CountryConverter().EU27as("ISO2").ISO2.tolist(),
    )


def country_scope(country_ids, supported_countries, eu_countries):
    """Add the fixed EU reference only when non-EU inference is needed."""
    country_ids = sorted(set(country_ids))
    if not country_ids:
        raise ValueError("The supplied shapes contain no land countries.")
    unsupported = set(country_ids) - set(supported_countries)
    if unsupported:
        raise ValueError(
            "No supported industrial calibration source for countries: "
            f"{', '.join(sorted(unsupported))}. "
            "Supply shapes restricted to supported countries, or add a verified "
            "industrial data source before including these countries."
        )
    reference = sorted(set(supported_countries) & set(eu_countries))
    proxies = {c: reference for c in set(country_ids) - set(eu_countries)}
    return country_ids, _country_scope_w_proxies(country_ids, proxies, reference)

"""Input helpers included in the Snakemake workflow namespace."""


def population_input(wildcards):
    """Require the population key only when enabled in the module config."""
    if config["spatial_disaggregation"]["population"]["enabled"]:
        return "<population>"
    return []


def user_key_input(wildcards):
    """Require the user-provided key only when enabled in the module config."""
    if config["spatial_disaggregation"]["user_key"]["enabled"]:
        return "<user_key>"
    return []

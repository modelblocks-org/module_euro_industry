"""Rules for disaggregating statistics at national level to user-provided shapes."""


rule disaggregate_production_rates:
    input:
        shapes=rules.prepare_shapes.output.shapes,
        hotmaps=rules.download_hotmaps.output.file,
        gem_gspt=rules.download_GEM_SPT.output.file,
        ammonia=rules.download_ammonia_plants.output.file,
        cement_supplement=rules.download_cement_non_eu.output.file,
        refineries_supplement=rules.download_refineries_non_eu.output.file,
    output:
        production_rates="resources/automatic/shapes/{shape}/production_rates.csv",
    log:
        "logs/{shape}/disaggregate_production_rates.log",
    conda:
        "../envs/industry.yaml"
    params:
        hotmaps_locate_missing=config["industry"]["hotmaps_locate_missing"],
        geographic_crs=internal["crs"]["geographic"],
    message:
        "{wildcards.shape}: estimating production rates per shape using proxies."
    script:
        "../scripts/disaggregate_production_rates.py"


rule disaggregate_current_energy_demand:
    input:
        shapes=rules.prepare_shapes.output.shapes,
        production_rates=rules.disaggregate_production_rates.output.production_rates,
        current_europe_energy_demand=rules.prepare_current_europe_energy_demand.output.energy_demand,
    output:
        energy_demand="results/{shape}/current_industrial_energy_demand.csv",
    log:
        "logs/{shape}/disaggregate_current_energy_demand.log",
    conda:
        "../envs/industry.yaml"
    message:
        "{wildcards.shape}: disaggregating current energy demand."
    script:
        "../scripts/disaggregate_current_energy_demand.py"


rule disaggregate_future_production:
    input:
        shapes=rules.prepare_shapes.output.shapes,
        production_rates=rules.disaggregate_production_rates.output.production_rates,
        future_europe_production=rules.prepare_future_europe_production.output.production,
    output:
        production="results/{shape}/{year}/production.csv",
    log:
        "logs/{shape}/{year}/disaggregate_future_production.log",
    conda:
        "../envs/industry.yaml"
    message:
        "{wildcards.shape}/{wildcards.year}: disaggregating future production."
    script:
        "../scripts/disaggregate_future_production.py"


rule disaggregate_future_energy_demand:
    input:
        shapes=rules.prepare_shapes.output.shapes,
        sector_rates=rules.prepare_future_europe_sector_rates.output.sector_rates,
        future_production=rules.disaggregate_future_production.output.production,
        current_energy_demand=rules.disaggregate_current_energy_demand.output.energy_demand,
    output:
        energy_demand="results/{shape}/{year}/energy_demand.csv",
    log:
        "logs/{shape}/{year}/disaggregate_future_energy_demand.log",
    conda:
        "../envs/industry.yaml"
    message:
        "{wildcards.shape}/{wildcards.year}: disaggregating energy demand."
    script:
        "../scripts/disaggregate_future_energy_demand.py"

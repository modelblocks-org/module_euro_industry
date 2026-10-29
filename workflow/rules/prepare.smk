"""Prepare the historical/current industrial calibration data."""


rule prepare_all:
    input:
        "results/historical/production.parquet",
        "results/historical/production_aggregated.parquet",
        "results/historical/energy_demand.parquet",
    output:
        touch("results/historical/.prepare_complete"),
    conda:
        "../envs/module.yaml"


rule prepare_ammonia_production:
    input:
        usgs="resources/automatic/ammonia/usgs.xlsx",
    output:
        "resources/automatic/prepare/ammonia_production.parquet",
    log:
        "logs/prepare/prepare_ammonia_production.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare historical ammonia production from USGS."
    script:
        "../scripts/prepare_ammonia_production.py"


rule prepare_coke_transformation:
    input:
        eurostat_dir="resources/automatic/eurostat",
    output:
        "resources/automatic/prepare/coke_transformation.parquet",
    log:
        "logs/prepare/prepare_coke_transformation.log",
    conda:
        "../envs/module.yaml"
    params:
        countries=config["countries"],
    message:
        "Prepare historical coke-oven transformation output from Eurostat."
    script:
        "../scripts/prepare_coke_transformation.py"


rule prepare_current_production:
    input:
        jrc_dir="resources/automatic/jrc_idees",
        eurostat_dir="resources/automatic/eurostat",
        ch_industrial_production="resources/automatic/CHE_industry.csv",
        ammonia_production=rules.prepare_ammonia_production.output[0],
    output:
        production="results/historical/production.parquet",
        aggregated="results/historical/production_aggregated.parquet",
    log:
        "logs/prepare/prepare_current_production.log",
    conda:
        "../envs/module.yaml"
    params:
        config_path="config/config.yaml",
    message:
        "Prepare route-preserving historical industrial production."
    script:
        "../scripts/prepare_current_production.py"


rule prepare_current_energy_demand:
    input:
        jrc_dir="resources/automatic/jrc_idees",
        production=rules.prepare_current_production.output.production,
        coke=rules.prepare_coke_transformation.output[0],
    output:
        "results/historical/energy_demand.parquet",
    log:
        "logs/prepare/prepare_current_energy_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        config_path="config/config.yaml",
    message:
        "Prepare route/activity-preserving historical industrial energy demand."
    script:
        "../scripts/prepare_current_energy_demand.py"

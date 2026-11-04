"""Prepare shape-specific historical industrial calibration data."""


rule prepare_shapes:
    input:
        shapes="<shapes>",
    output:
        shapes="<resources>/automatic/shapes/{shapes}/land_shapes.parquet",
        country_ids="<resources>/automatic/shapes/{shapes}/country_ids.txt",
        source_country_ids="<resources>/automatic/shapes/{shapes}/source_country_ids.txt",
    log:
        "<logs>/{shapes}/prepare_shapes.log",
    conda:
        "../envs/module.yaml"
    params:
        supported_countries=internal["calibration_countries"],
    script:
        "../scripts/prepare_shapes.py"


rule prepare_all:
    input:
        "<historical_production>",
        "<historical_production_aggregated>",
        "<historical_energy_demand>",
    output:
        touch("<results>/{shapes}/historical/.prepare_complete"),
    conda:
        "../envs/module.yaml"


rule prepare_ammonia_production:
    input:
        usgs="<resources>/automatic/ammonia/usgs.xlsx",
    output:
        production="<resources>/automatic/prepare/ammonia_production.parquet",
    log:
        "<logs>/prepare/prepare_ammonia_production.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare historical ammonia production from USGS."
    script:
        "../scripts/prepare_ammonia_production.py"


rule prepare_coke_transformation:
    input:
        country_ids=rules.prepare_shapes.output.country_ids,
        eurostat_dir="<resources>/automatic/eurostat",
    output:
        transformation="<resources>/automatic/shapes/{shapes}/coke_transformation.parquet",
    log:
        "<logs>/{shapes}/prepare/prepare_coke_transformation.log",
    conda:
        "../envs/module.yaml"
    message:
        "Prepare historical coke-oven transformation output from Eurostat."
    script:
        "../scripts/prepare_coke_transformation.py"


rule prepare_current_production:
    input:
        country_ids=rules.prepare_shapes.output.country_ids,
        source_country_ids=rules.prepare_shapes.output.source_country_ids,
        jrc_dir="<resources>/automatic/jrc_idees",
        eurostat_dir="<resources>/automatic/eurostat",
        ch_industrial_production="<resources>/automatic/CHE_industry.csv",
        ammonia_production=rules.prepare_ammonia_production.output.production,
    output:
        source_production="<resources>/automatic/shapes/{shapes}/source_production.parquet",
        production="<historical_production>",
        aggregated="<historical_production_aggregated>",
    log:
        "<logs>/{shapes}/prepare/prepare_current_production.log",
    conda:
        "../envs/module.yaml"
    params:
        reference_year=config["historical_calibration"]["reference_year"],
        basic_chemicals_without_NH3_production_today=config["historical_calibration"][
            "basic_chemicals_without_NH3_production_today"
        ],
        HVC_production_today=config["historical_calibration"]["HVC_production_today"],
        chlorine_production_today=config["historical_calibration"][
            "chlorine_production_today"
        ],
        methanol_production_today=config["historical_calibration"][
            "methanol_production_today"
        ],
    message:
        "Prepare route-preserving historical industrial production."
    script:
        "../scripts/prepare_current_production.py"


rule prepare_current_energy_demand:
    input:
        country_ids=rules.prepare_shapes.output.country_ids,
        source_country_ids=rules.prepare_shapes.output.source_country_ids,
        jrc_dir="<resources>/automatic/jrc_idees",
        production=rules.prepare_current_production.output.source_production,
        coke=rules.prepare_coke_transformation.output.transformation,
    output:
        energy_demand="<historical_energy_demand>",
    log:
        "<logs>/{shapes}/prepare/prepare_current_energy_demand.log",
    conda:
        "../envs/module.yaml"
    params:
        reference_year=config["historical_calibration"]["reference_year"],
        MWh_NH3_per_tNH3=config["historical_calibration"]["MWh_NH3_per_tNH3"],
        MWh_H2_per_tNH3_electrolysis=config["historical_calibration"][
            "MWh_H2_per_tNH3_electrolysis"
        ],
        MWh_elec_per_tNH3_electrolysis=config["historical_calibration"][
            "MWh_elec_per_tNH3_electrolysis"
        ],
        MWh_elec_per_tCl=config["historical_calibration"]["MWh_elec_per_tCl"],
        MWh_H2_per_tCl=config["historical_calibration"]["MWh_H2_per_tCl"],
        MWh_elec_per_tMeOH=config["historical_calibration"]["MWh_elec_per_tMeOH"],
        MWh_CH4_per_tMeOH=config["historical_calibration"]["MWh_CH4_per_tMeOH"],
        ammonia=config["historical_calibration"]["ammonia"],
        coke_oven_allocation=config["historical_calibration"]["coke_oven_allocation"],
    message:
        "Prepare route/activity-preserving historical industrial energy demand."
    script:
        "../scripts/prepare_current_energy_demand.py"
